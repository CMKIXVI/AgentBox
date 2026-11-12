"""Read-only PostgreSQL catalog discovery for AgentBox.

The adapter reads PostgreSQL system catalogs only. It never selects application rows,
stores connection material, or performs source-system writes. A caller supplies an
already-authenticated DB-API connection factory so credential handling stays outside
the discovery domain.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Iterable, Mapping
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]{0,62}$")
DEFAULT_EXCLUDED_SCHEMAS = ("information_schema",)
MAX_SCHEMAS = 100
MAX_RELATIONS = 2000
MAX_COLUMNS = 20000
MAX_INDEXES = 10000
MAX_CONSTRAINTS = 10000
MAX_STATEMENT_TIMEOUT_MS = 30000


class PostgreSQLDiscoveryError(Exception):
    """Base error for bounded PostgreSQL catalog discovery."""


class PostgreSQLDiscoveryLimitError(PostgreSQLDiscoveryError):
    """The source catalog exceeds an explicit discovery bound."""


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _rows(cursor: Any) -> list[dict[str, Any]]:
    records = cursor.fetchall()
    if not records:
        return []
    if isinstance(records[0], Mapping):
        return [dict(row) for row in records]
    names = [column[0] for column in cursor.description]
    return [dict(zip(names, row, strict=True)) for row in records]


def _bounded(items: list[dict[str, Any]], limit: int, label: str) -> list[dict[str, Any]]:
    if len(items) > limit:
        raise PostgreSQLDiscoveryLimitError(f"{label} exceeds the configured limit of {limit}")
    return items


class PostgreSQLCatalogDiscovery:
    """Discover a bounded PostgreSQL catalog through an injected DB-API connection."""

    def __init__(
        self,
        connection_factory: Callable[[], Any],
        *,
        statement_timeout_ms: int = 10000,
    ) -> None:
        if not callable(connection_factory):
            raise ValueError("connection_factory must be callable")
        if not 100 <= statement_timeout_ms <= MAX_STATEMENT_TIMEOUT_MS:
            raise ValueError("statement_timeout_ms must be between 100 and 30000")
        self._connection_factory = connection_factory
        self._statement_timeout_ms = statement_timeout_ms

    @contextmanager
    def _read_only_connection(self):
        connection = self._connection_factory()
        cursor = connection.cursor()
        try:
            cursor.execute("BEGIN TRANSACTION READ ONLY")
            cursor.execute(f"SET LOCAL statement_timeout = '{self._statement_timeout_ms}ms'")
            yield cursor
            connection.rollback()
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def _validate_schemas(schemas: Iterable[str] | None) -> list[str] | None:
        if schemas is None:
            return None
        result = list(dict.fromkeys(schemas))
        if not result or len(result) > MAX_SCHEMAS:
            raise ValueError(f"schemas must contain between 1 and {MAX_SCHEMAS} names")
        if any(not isinstance(name, str) or not IDENTIFIER.fullmatch(name) for name in result):
            raise ValueError("schema names must be simple PostgreSQL identifiers")
        return result

    def discover(self, schemas: Iterable[str] | None = None) -> dict[str, Any]:
        """Return metadata-only snapshot; optional schemas are an exact allowlist."""
        selected = self._validate_schemas(schemas)
        with self._read_only_connection() as cursor:
            cursor.execute(
                """
                /* agentbox:schemas */
                SELECT nspname AS schema_name
                FROM pg_catalog.pg_namespace
                WHERE nspname <> 'information_schema'
                  AND nspname NOT LIKE 'pg_%'
                ORDER BY nspname
                """
            )
            discovered_schemas = [row["schema_name"] for row in _rows(cursor)]
            if selected is not None:
                available = set(discovered_schemas)
                missing = sorted(set(selected) - available)
                if missing:
                    raise PostgreSQLDiscoveryError(f"Requested schemas do not exist: {missing}")
                discovered_schemas = [name for name in discovered_schemas if name in selected]
            _bounded([{"name": name} for name in discovered_schemas], MAX_SCHEMAS, "Schemas")
            if not discovered_schemas:
                return self._snapshot([], [], [], [], [])

            cursor.execute(
                """
                /* agentbox:relations */
                SELECT n.nspname AS schema_name, c.relname AS relation_name,
                       CASE c.relkind WHEN 'r' THEN 'table'
                         WHEN 'p' THEN 'partitioned_table'
                         WHEN 'v' THEN 'view' WHEN 'm' THEN 'materialized_view'
                         WHEN 'f' THEN 'foreign_table' END AS relation_kind,
                       obj_description(c.oid, 'pg_class') AS comment
                FROM pg_catalog.pg_class c
                JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = ANY(%s)
                  AND c.relkind IN ('r','p','v','m','f')
                ORDER BY n.nspname, c.relname
                """,
                (discovered_schemas,),
            )
            relations = _bounded(_rows(cursor), MAX_RELATIONS, "Relations")

            cursor.execute(
                """
                /* agentbox:columns */
                SELECT n.nspname AS schema_name, c.relname AS relation_name,
                       a.attnum AS ordinal_position, a.attname AS column_name,
                       pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
                       NOT a.attnotnull AS is_nullable,
                       col_description(c.oid, a.attnum) AS comment
                FROM pg_catalog.pg_attribute a
                JOIN pg_catalog.pg_class c ON c.oid = a.attrelid
                JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = ANY(%s) AND a.attnum > 0 AND NOT a.attisdropped
                  AND c.relkind IN ('r','p','v','m','f')
                ORDER BY n.nspname, c.relname, a.attnum
                """,
                (discovered_schemas,),
            )
            columns = _bounded(_rows(cursor), MAX_COLUMNS, "Columns")

            cursor.execute(
                """
                /* agentbox:indexes */
                SELECT n.nspname AS schema_name, t.relname AS relation_name,
                       i.relname AS index_name, ix.indisprimary AS is_primary,
                       ix.indisunique AS is_unique,
                       pg_get_indexdef(i.oid) AS definition
                FROM pg_catalog.pg_index ix
                JOIN pg_catalog.pg_class t ON t.oid = ix.indrelid
                JOIN pg_catalog.pg_class i ON i.oid = ix.indexrelid
                JOIN pg_catalog.pg_namespace n ON n.oid = t.relnamespace
                WHERE n.nspname = ANY(%s)
                ORDER BY n.nspname, t.relname, i.relname
                """,
                (discovered_schemas,),
            )
            indexes = _bounded(_rows(cursor), MAX_INDEXES, "Indexes")

            cursor.execute(
                """
                /* agentbox:constraints */
                SELECT n.nspname AS schema_name, t.relname AS relation_name,
                       con.conname AS constraint_name,
                       CASE con.contype WHEN 'p' THEN 'primary_key'
                         WHEN 'f' THEN 'foreign_key' WHEN 'u' THEN 'unique'
                         WHEN 'c' THEN 'check' WHEN 'x' THEN 'exclusion' END AS constraint_kind,
                       pg_get_constraintdef(con.oid, true) AS definition,
                       rn.nspname AS referenced_schema,
                       rt.relname AS referenced_relation
                FROM pg_catalog.pg_constraint con
                JOIN pg_catalog.pg_class t ON t.oid = con.conrelid
                JOIN pg_catalog.pg_namespace n ON n.oid = t.relnamespace
                LEFT JOIN pg_catalog.pg_class rt ON rt.oid = con.confrelid
                LEFT JOIN pg_catalog.pg_namespace rn ON rn.oid = rt.relnamespace
                WHERE n.nspname = ANY(%s)
                ORDER BY n.nspname, t.relname, con.conname
                """,
                (discovered_schemas,),
            )
            constraints = _bounded(_rows(cursor), MAX_CONSTRAINTS, "Constraints")

        return self._snapshot(discovered_schemas, relations, columns, indexes, constraints)

    @staticmethod
    def _snapshot(
        schemas: list[str],
        relations: list[dict[str, Any]],
        columns: list[dict[str, Any]],
        indexes: list[dict[str, Any]],
        constraints: list[dict[str, Any]],
    ) -> dict[str, Any]:
        payload = {
            "contract_version": "1.0.0",
            "source_kind": "postgresql_catalog",
            "discovered_at": datetime.now(UTC).isoformat(),
            "schemas": schemas,
            "relations": relations,
            "columns": columns,
            "indexes": indexes,
            "constraints": constraints,
            "data_rows_read": 0,
            "writes_performed": 0,
        }
        payload["snapshot_hash"] = _hash(payload)
        return payload
