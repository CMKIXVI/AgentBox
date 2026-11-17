"""Tenant-scoped, evidence-backed Enterprise Context Engine v1.

This module is a logical context store over the existing AgentBox SQLite database.
It stores metadata and source references, never source credentials or raw source payloads.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker

from .tenant import validate_tenant_id

ASSERTION_CLASSES = {"observed_fact", "inferred", "ai_hypothesis", "human_validated"}
HASH_PATTERN = re.compile(r"^[a-fA-F0-9]{64}$")
MAX_JSON_BYTES = 65536


class ContextError(Exception):
    """Base Enterprise Context Engine error."""


class ContextNotFoundError(ContextError):
    """A tenant-scoped context record does not exist."""


class ContextConflictError(ContextError):
    """An immutable context identity conflicts with existing content."""


class ContextValidationError(ContextError):
    """A context payload violates its versioned contract."""


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _canonical(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _validate_actor(actor_id: str) -> None:
    if not isinstance(actor_id, str) or not actor_id.strip() or len(actor_id) > 256:
        raise ContextValidationError("actor_id must contain 1 to 256 characters")


def _validate_period(payload: dict[str, Any]) -> None:
    start = payload.get("valid_from")
    end = payload.get("valid_to")
    if start and end:
        start_at = datetime.fromisoformat(start)
        end_at = datetime.fromisoformat(end)
        if start_at > end_at:
            raise ContextValidationError("valid_from must not be later than valid_to")


def _schema_validator(name: str) -> Draft202012Validator:
    path = Path(__file__).resolve().parents[2] / "schemas" / name
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


class EnterpriseContextService:
    """Immutable, tenant-scoped enterprise entities, edges, evidence and events."""

    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)
        self._memory = self.database_path == ":memory:"
        self._dsn = (
            f"file:agentbox-context-{id(self)}?mode=memory&cache=shared"
            if self._memory else self.database_path
        )
        self._keeper = (
            sqlite3.connect(self._dsn, uri=True, timeout=10) if self._memory else None
        )
        if not self._memory:
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self._entity_validator = _schema_validator("enterprise-context-entity-v1.schema.json")
        self._relationship_validator = _schema_validator(
            "enterprise-context-relationship-v1.schema.json"
        )
        self._evidence_validator = _schema_validator(
            "enterprise-context-evidence-v1.schema.json"
        )
        self._event_validator = _schema_validator("enterprise-context-event-v1.schema.json")
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._dsn, uri=self._memory, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            if not self._memory:
                connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("""
                CREATE TABLE IF NOT EXISTS context_entities (
                    tenant_id TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    version INTEGER NOT NULL CHECK(version >= 1),
                    entity_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    attributes_json TEXT NOT NULL,
                    assertion_class TEXT NOT NULL CHECK(assertion_class IN (
                        'observed_fact','inferred','ai_hypothesis','human_validated'
                    )),
                    confidence REAL NOT NULL CHECK(confidence >= 0 AND confidence <= 1),
                    valid_from TEXT,
                    valid_to TEXT,
                    content_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, entity_id, version),
                    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id)
                )
            """)
            connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_context_entities_tenant_type
                ON context_entities(tenant_id, entity_type, entity_id, version)
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS context_relationships (
                    tenant_id TEXT NOT NULL,
                    relationship_id TEXT NOT NULL,
                    version INTEGER NOT NULL CHECK(version >= 1),
                    relationship_type TEXT NOT NULL,
                    source_entity_id TEXT NOT NULL,
                    source_version INTEGER NOT NULL,
                    target_entity_id TEXT NOT NULL,
                    target_version INTEGER NOT NULL,
                    attributes_json TEXT NOT NULL,
                    assertion_class TEXT NOT NULL CHECK(assertion_class IN (
                        'observed_fact','inferred','ai_hypothesis','human_validated'
                    )),
                    confidence REAL NOT NULL CHECK(confidence >= 0 AND confidence <= 1),
                    valid_from TEXT,
                    valid_to TEXT,
                    content_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, relationship_id, version),
                    FOREIGN KEY (tenant_id, source_entity_id, source_version)
                        REFERENCES context_entities(tenant_id, entity_id, version),
                    FOREIGN KEY (tenant_id, target_entity_id, target_version)
                        REFERENCES context_entities(tenant_id, entity_id, version)
                )
            """)
            connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_context_relationships_source
                ON context_relationships(tenant_id, source_entity_id, relationship_type)
            """)
            connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_context_relationships_target
                ON context_relationships(tenant_id, target_entity_id, relationship_type)
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS context_evidence (
                    tenant_id TEXT NOT NULL,
                    evidence_id TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    entity_version INTEGER NOT NULL,
                    relationship_id TEXT,
                    relationship_version INTEGER,
                    source_kind TEXT NOT NULL,
                    source_ref TEXT NOT NULL,
                    source_hash TEXT,
                    observed_at TEXT NOT NULL,
                    confidence REAL NOT NULL CHECK(confidence >= 0 AND confidence <= 1),
                    validation_status TEXT NOT NULL CHECK(validation_status IN (
                        'unverified','validated','rejected'
                    )),
                    metadata_json TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    recorded_by TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, evidence_id),
                    FOREIGN KEY (tenant_id, entity_id, entity_version)
                        REFERENCES context_entities(tenant_id, entity_id, version),
                    FOREIGN KEY (tenant_id, relationship_id, relationship_version)
                        REFERENCES context_relationships(tenant_id, relationship_id, version)
                )
            """)
            connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_context_evidence_entity
                ON context_evidence(tenant_id, entity_id, entity_version, observed_at)
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS context_events (
                    tenant_id TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    object_type TEXT NOT NULL,
                    object_id TEXT NOT NULL,
                    object_version INTEGER,
                    source_ref TEXT,
                    observed_at TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    recorded_by TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, event_id),
                    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id)
                )
            """)
            connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_context_events_tenant_time
                ON context_events(tenant_id, recorded_at, event_id)
            """)
            for operation in ("UPDATE", "DELETE"):
                connection.execute(f"""
                    CREATE TRIGGER IF NOT EXISTS context_events_no_{operation.lower()}
                    BEFORE {operation} ON context_events BEGIN
                        SELECT RAISE(ABORT, 'AgentBox context events are append-only');
                    END
                """)

    @staticmethod
    def _validate(
        validator: Draft202012Validator, payload: dict[str, Any], label: str
    ) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ContextValidationError(f"{label} must be an object")
        errors = sorted(validator.iter_errors(payload), key=lambda item: str(item.path))
        if errors:
            details = "; ".join(
                f"{'/'.join(str(part) for part in error.absolute_path)}: {error.message}"
                for error in errors[:10]
            )
            raise ContextValidationError(f"Invalid {label}: {details}")
        try:
            serialized = _canonical(payload)
        except (TypeError, ValueError) as exc:
            raise ContextValidationError(f"{label} contains non-JSON or non-finite values") from exc
        if len(serialized.encode("utf-8")) > MAX_JSON_BYTES:
            raise ContextValidationError(f"{label} exceeds the 64 KiB metadata limit")
        return json.loads(serialized)

    @staticmethod
    def _record_entity(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row)
        result["attributes"] = json.loads(result.pop("attributes_json"))
        return result

    @staticmethod
    def _record_relationship(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row)
        result["attributes"] = json.loads(result.pop("attributes_json"))
        return result

    @staticmethod
    def _record_evidence(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row)
        result["metadata"] = json.loads(result.pop("metadata_json"))
        return result

    def _append_event(
        self,
        connection: sqlite3.Connection,
        tenant_id: str,
        event_type: str,
        object_type: str,
        object_id: str,
        object_version: int | None,
        actor_id: str,
        payload: dict[str, Any],
        source_ref: str | None = None,
        observed_at: str | None = None,
    ) -> None:
        event = {
            "event_id": uuid.uuid4().hex,
            "event_type": event_type,
            "object_type": object_type,
            "object_id": object_id,
            "object_version": object_version,
            "source_ref": source_ref,
            "observed_at": observed_at or _now(),
            "payload": payload,
        }
        self._validate(self._event_validator, event, "context event")
        recorded_at = _now()
        connection.execute(
            """INSERT INTO context_events
            (tenant_id,event_id,event_type,object_type,object_id,object_version,
             source_ref,observed_at,recorded_at,recorded_by,payload_json,content_hash)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                tenant_id, event["event_id"], event_type, object_type, object_id,
                object_version, source_ref, event["observed_at"], recorded_at, actor_id,
                _canonical(payload), _digest(event),
            ),
        )

    def create_entity(
        self, payload: dict[str, Any], tenant_id: str, actor_id: str
    ) -> dict[str, Any]:
        validate_tenant_id(tenant_id)
        _validate_actor(actor_id)
        item = self._validate(self._entity_validator, payload, "enterprise context entity")
        _validate_period(item)
        now = _now()
        digest = _digest(item)
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute(
                    """INSERT INTO context_entities
                    (tenant_id,entity_id,version,entity_type,name,description,attributes_json,
                     assertion_class,confidence,valid_from,valid_to,content_hash,created_at,created_by)
                    VALUES (?,?,1,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        tenant_id, item["entity_id"], item["entity_type"], item["name"],
                        item.get("description", ""), _canonical(item.get("attributes", {})),
                        item["assertion_class"], item["confidence"], item.get("valid_from"),
                        item.get("valid_to"), digest, now, actor_id,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ContextConflictError(
                    f"Enterprise context entity already exists: {item['entity_id']}"
                ) from exc
            self._append_event(
                connection, tenant_id, "context.entity.created", "entity",
                item["entity_id"], 1, actor_id, {"content_hash": digest},
                observed_at=now,
            )
            row = connection.execute(
                "SELECT * FROM context_entities WHERE tenant_id=? AND entity_id=? AND version=1",
                (tenant_id, item["entity_id"]),
            ).fetchone()
        return self._record_entity(row)

    def version_entity(
        self,
        payload: dict[str, Any],
        tenant_id: str,
        actor_id: str,
        expected_version: int,
    ) -> dict[str, Any]:
        validate_tenant_id(tenant_id)
        _validate_actor(actor_id)
        item = self._validate(self._entity_validator, payload, "enterprise context entity")
        _validate_period(item)
        if expected_version < 1:
            raise ContextValidationError("expected_version must be at least 1")
        now = _now()
        digest = _digest(item)
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            latest = connection.execute(
                "SELECT MAX(version) AS version FROM context_entities WHERE tenant_id=? AND entity_id=?",
                (tenant_id, item["entity_id"]),
            ).fetchone()["version"]
            if latest is None:
                raise ContextNotFoundError(item["entity_id"])
            if latest != expected_version:
                raise ContextConflictError(
                    f"Entity version changed; expected {expected_version}, current {latest}"
                )
            new_version = latest + 1
            connection.execute(
                """INSERT INTO context_entities
                (tenant_id,entity_id,version,entity_type,name,description,attributes_json,
                 assertion_class,confidence,valid_from,valid_to,content_hash,created_at,created_by)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    tenant_id, item["entity_id"], new_version, item["entity_type"], item["name"],
                    item.get("description", ""), _canonical(item.get("attributes", {})),
                    item["assertion_class"], item["confidence"], item.get("valid_from"),
                    item.get("valid_to"), digest, now, actor_id,
                ),
            )
            self._append_event(
                connection, tenant_id, "context.entity.versioned", "entity",
                item["entity_id"], new_version, actor_id,
                {"previous_version": latest, "content_hash": digest}, observed_at=now,
            )
            row = connection.execute(
                "SELECT * FROM context_entities WHERE tenant_id=? AND entity_id=? AND version=?",
                (tenant_id, item["entity_id"], new_version),
            ).fetchone()
        return self._record_entity(row)

    def get_entity(
        self, entity_id: str, tenant_id: str, version: int | None = None
    ) -> dict[str, Any]:
        validate_tenant_id(tenant_id)
        with self._connection() as connection:
            if version is None:
                row = connection.execute(
                    """SELECT * FROM context_entities WHERE tenant_id=? AND entity_id=?
                    ORDER BY version DESC LIMIT 1""", (tenant_id, entity_id)
                ).fetchone()
            else:
                row = connection.execute(
                    "SELECT * FROM context_entities WHERE tenant_id=? AND entity_id=? AND version=?",
                    (tenant_id, entity_id, version),
                ).fetchone()
        if row is None:
            raise ContextNotFoundError(entity_id)
        return self._record_entity(row)

    def query_entities(
        self,
        tenant_id: str,
        entity_type: str | None = None,
        assertion_class: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        validate_tenant_id(tenant_id)
        if not 1 <= limit <= 100 or offset < 0:
            raise ContextValidationError("limit must be 1-100 and offset must be non-negative")
        if search is not None and (not search.strip() or len(search) > 128):
            raise ContextValidationError("search must contain 1-128 non-whitespace characters")
        if assertion_class is not None and assertion_class not in ASSERTION_CLASSES:
            raise ContextValidationError("Unsupported assertion_class")
        clauses = ["e.tenant_id = ?", "e.version = (SELECT MAX(v.version) FROM context_entities v WHERE v.tenant_id=e.tenant_id AND v.entity_id=e.entity_id)"]
        values: list[Any] = [tenant_id]
        if entity_type:
            clauses.append("e.entity_type = ?")
            values.append(entity_type)
        if assertion_class:
            clauses.append("e.assertion_class = ?")
            values.append(assertion_class)
        if search:
            clauses.append("instr(lower(e.name), lower(?)) > 0")
            values.append(search)
        values.extend([limit, offset])
        with self._connection() as connection:
            rows = connection.execute(
                f"SELECT e.* FROM context_entities e WHERE {' AND '.join(clauses)} "
                "ORDER BY e.entity_type,e.name,e.entity_id LIMIT ? OFFSET ?",
                values,
            ).fetchall()
        return [self._record_entity(row) for row in rows]

    def create_relationship(
        self, payload: dict[str, Any], tenant_id: str, actor_id: str
    ) -> dict[str, Any]:
        validate_tenant_id(tenant_id)
        _validate_actor(actor_id)
        item = self._validate(
            self._relationship_validator, payload, "enterprise context relationship"
        )
        _validate_period(item)
        if item["source_entity_id"] == item["target_entity_id"] and (
            item["source_version"] == item["target_version"]
        ):
            raise ContextValidationError("A relationship cannot point from an entity version to itself")
        now = _now()
        digest = _digest(item)
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            for entity_id, version in (
                (item["source_entity_id"], item["source_version"]),
                (item["target_entity_id"], item["target_version"]),
            ):
                exists = connection.execute(
                    """SELECT 1 FROM context_entities
                    WHERE tenant_id=? AND entity_id=? AND version=?""",
                    (tenant_id, entity_id, version),
                ).fetchone()
                if exists is None:
                    raise ContextNotFoundError(
                        f"Relationship endpoint does not exist in this tenant: {entity_id}@{version}"
                    )
            try:
                connection.execute(
                    """INSERT INTO context_relationships
                    (tenant_id,relationship_id,version,relationship_type,source_entity_id,
                     source_version,target_entity_id,target_version,attributes_json,assertion_class,
                     confidence,valid_from,valid_to,content_hash,created_at,created_by)
                    VALUES (?,?,1,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        tenant_id, item["relationship_id"], item["relationship_type"],
                        item["source_entity_id"], item["source_version"], item["target_entity_id"],
                        item["target_version"], _canonical(item.get("attributes", {})),
                        item["assertion_class"], item["confidence"], item.get("valid_from"),
                        item.get("valid_to"), digest, now, actor_id,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ContextConflictError(
                    f"Enterprise context relationship already exists: {item['relationship_id']}"
                ) from exc
            self._append_event(
                connection, tenant_id, "context.relationship.created", "relationship",
                item["relationship_id"], 1, actor_id, {"content_hash": digest},
                observed_at=now,
            )
            row = connection.execute(
                """SELECT * FROM context_relationships
                WHERE tenant_id=? AND relationship_id=? AND version=1""",
                (tenant_id, item["relationship_id"]),
            ).fetchone()
        return self._record_relationship(row)

    def query_relationships(
        self,
        tenant_id: str,
        entity_id: str | None = None,
        relationship_type: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        validate_tenant_id(tenant_id)
        if not 1 <= limit <= 200:
            raise ContextValidationError("limit must be 1-200")
        clauses = ["r.tenant_id = ?"]
        values: list[Any] = [tenant_id]
        if entity_id:
            clauses.append("(r.source_entity_id = ? OR r.target_entity_id = ?)")
            values.extend([entity_id, entity_id])
        if relationship_type:
            clauses.append("r.relationship_type = ?")
            values.append(relationship_type)
        with self._connection() as connection:
            rows = connection.execute(
                f"SELECT r.* FROM context_relationships r WHERE {' AND '.join(clauses)} "
                "ORDER BY r.relationship_id,r.version LIMIT ?",
                [*values, limit],
            ).fetchall()
        return [self._record_relationship(row) for row in rows]

    def create_evidence(
        self, payload: dict[str, Any], tenant_id: str, actor_id: str
    ) -> dict[str, Any]:
        validate_tenant_id(tenant_id)
        _validate_actor(actor_id)
        item = self._validate(self._evidence_validator, payload, "enterprise context evidence")
        if item.get("validation_status", "unverified") != "unverified":
            raise ContextValidationError(
                "Evidence must remain unverified until a separately authorized review"
            )
        source_locator = urlsplit(item["source_ref"])
        if source_locator.username or source_locator.password or source_locator.query or source_locator.fragment:
            raise ContextValidationError(
                "source_ref must not contain credentials, query parameters, or fragments"
            )
        if item.get("source_hash") and not HASH_PATTERN.fullmatch(item["source_hash"]):
            raise ContextValidationError("source_hash must be a SHA-256 hex digest")
        now = _now()
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            entity = connection.execute(
                """SELECT 1 FROM context_entities WHERE tenant_id=? AND entity_id=? AND version=?""",
                (tenant_id, item["entity_id"], item["entity_version"]),
            ).fetchone()
            if entity is None:
                raise ContextNotFoundError("Evidence entity/version does not exist in this tenant")
            relationship_id = item.get("relationship_id")
            relationship_version = item.get("relationship_version")
            if relationship_id is not None:
                relation = connection.execute(
                    """SELECT 1 FROM context_relationships
                    WHERE tenant_id=? AND relationship_id=? AND version=?""",
                    (tenant_id, relationship_id, relationship_version),
                ).fetchone()
                if relation is None:
                    raise ContextNotFoundError("Evidence relationship/version does not exist in this tenant")
            try:
                connection.execute(
                    """INSERT INTO context_evidence
                    (tenant_id,evidence_id,entity_id,entity_version,relationship_id,
                     relationship_version,source_kind,source_ref,source_hash,observed_at,
                     confidence,validation_status,metadata_json,recorded_at,recorded_by)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        tenant_id, item["evidence_id"], item["entity_id"], item["entity_version"],
                        relationship_id, relationship_version, item["source_kind"],
                        item["source_ref"], item.get("source_hash"), item["observed_at"],
                        item["confidence"], item.get("validation_status", "unverified"),
                        _canonical(item.get("metadata", {})), now, actor_id,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ContextConflictError(
                    f"Enterprise context evidence already exists: {item['evidence_id']}"
                ) from exc
            self._append_event(
                connection, tenant_id, "context.evidence.recorded", "evidence",
                item["evidence_id"], None, actor_id,
                {"entity_id": item["entity_id"], "entity_version": item["entity_version"]},
                source_ref=item["source_ref"], observed_at=item["observed_at"],
            )
            row = connection.execute(
                "SELECT * FROM context_evidence WHERE tenant_id=? AND evidence_id=?",
                (tenant_id, item["evidence_id"]),
            ).fetchone()
        return self._record_evidence(row)

    def query_evidence(
        self, entity_id: str, tenant_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        validate_tenant_id(tenant_id)
        if not 1 <= limit <= 200:
            raise ContextValidationError("limit must be 1-200")
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT * FROM context_evidence WHERE tenant_id=? AND entity_id=?
                ORDER BY observed_at DESC,evidence_id LIMIT ?""",
                (tenant_id, entity_id, limit),
            ).fetchall()
        return [self._record_evidence(row) for row in rows]

    def query_events(
        self, tenant_id: str, since: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        validate_tenant_id(tenant_id)
        if not 1 <= limit <= 200:
            raise ContextValidationError("limit must be 1-200")
        with self._connection() as connection:
            if since:
                rows = connection.execute(
                    """SELECT * FROM context_events WHERE tenant_id=? AND recorded_at>?
                    ORDER BY recorded_at,event_id LIMIT ?""",
                    (tenant_id, since, limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    """SELECT * FROM context_events WHERE tenant_id=?
                    ORDER BY recorded_at,event_id LIMIT ?""", (tenant_id, limit)
                ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item.pop("payload_json"))
            result.append(item)
        return result
