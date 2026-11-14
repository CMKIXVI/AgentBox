"""Tenant-scoped PostgreSQL connector and signing-key lifecycle registry.

Public keys and lifecycle events are append-only. Revocation is represented by a
new event, never by mutating the original key material.
"""
from __future__ import annotations

import base64
import binascii
import json
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .enterprise_context import ContextConflictError, ContextNotFoundError, ContextValidationError

IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{1,127}$")


def _now() -> str:
    return datetime.now(UTC).isoformat()


class PostgreSQLConnectorRegistry:
    """Persistent connector identities, immutable Ed25519 keys and audit events."""

    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)
        self._memory = self.database_path == ":memory:"
        self._dsn = (
            f"file:agentbox-pg-connectors-{id(self)}?mode=memory&cache=shared"
            if self._memory else self.database_path
        )
        self._keeper = sqlite3.connect(self._dsn, uri=True, timeout=10) if self._memory else None
        if not self._memory:
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self._closed = False
        self._initialize()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._keeper is not None:
            self._keeper.close()
            self._keeper = None

    def _connect(self):
        if self._closed:
            raise RuntimeError("PostgreSQL connector registry is closed")
        connection = sqlite3.connect(self._dsn, uri=self._memory, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    @contextmanager
    def _connection(self):
        connection = self._connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as db:
            if not self._memory:
                db.execute("PRAGMA journal_mode = WAL")
            db.execute("""
                CREATE TABLE IF NOT EXISTS pg_connectors (
                    tenant_id TEXT NOT NULL,
                    connector_id TEXT NOT NULL,
                    source_ref TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('active','revoked')),
                    created_at TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, connector_id),
                    UNIQUE (tenant_id, source_ref)
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS pg_connector_keys (
                    tenant_id TEXT NOT NULL,
                    connector_id TEXT NOT NULL,
                    key_id TEXT NOT NULL,
                    public_key_b64 TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('active','revoked')),
                    created_at TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, connector_id, key_id),
                    FOREIGN KEY (tenant_id, connector_id)
                        REFERENCES pg_connectors(tenant_id, connector_id)
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS pg_connector_events (
                    event_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    connector_id TEXT NOT NULL,
                    event_type TEXT NOT NULL CHECK(event_type IN (
                        'connector.registered','connector.key_added','connector.key_revoked',
                        'connector.revoked'
                    )),
                    key_id TEXT,
                    actor_id TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    FOREIGN KEY (tenant_id, connector_id)
                        REFERENCES pg_connectors(tenant_id, connector_id)
                )
            """)
            for table in ("pg_connector_keys", "pg_connector_events"):
                for operation in ("UPDATE", "DELETE"):
                    db.execute(f"""
                        CREATE TRIGGER IF NOT EXISTS {table}_no_{operation.lower()}
                        BEFORE {operation} ON {table} BEGIN
                            SELECT RAISE(ABORT, 'Connector key and event records are append-only');
                        END
                    """)
            db.execute("""
                CREATE TRIGGER IF NOT EXISTS pg_connector_events_no_update
                BEFORE UPDATE ON pg_connector_events BEGIN
                    SELECT RAISE(ABORT, 'Connector events are append-only');
                END
            """)
            db.execute("""
                CREATE TRIGGER IF NOT EXISTS pg_connector_events_no_delete
                BEFORE DELETE ON pg_connector_events BEGIN
                    SELECT RAISE(ABORT, 'Connector events are append-only');
                END
            """)

    @staticmethod
    def _validate_identity(connector_id: str, key_id: str | None = None) -> None:
        if not isinstance(connector_id, str) or not IDENTIFIER.fullmatch(connector_id):
            raise ContextValidationError("connector_id must be a 2-128 character safe identifier")
        if key_id is not None and (
            not isinstance(key_id, str) or not IDENTIFIER.fullmatch(key_id)
        ):
            raise ContextValidationError("key_id must be a 2-128 character safe identifier")

    @staticmethod
    def _validate_public_key(public_key: str) -> tuple[str, bytes]:
        if not isinstance(public_key, str) or not 40 <= len(public_key) <= 64:
            raise ContextValidationError("public_key must be base64 encoded raw Ed25519 key material")
        try:
            raw = base64.b64decode(public_key, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ContextValidationError("public_key is not valid base64") from exc
        if len(raw) != 32:
            raise ContextValidationError("Ed25519 public keys must contain exactly 32 bytes")
        return base64.b64encode(raw).decode("ascii"), raw

    @staticmethod
    def _event(db, tenant_id: str, connector_id: str, event_type: str,
               actor_id: str, key_id: str | None, payload: dict[str, Any]) -> None:
        db.execute(
            """INSERT INTO pg_connector_events
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (str(uuid.uuid4()), tenant_id, connector_id, event_type, key_id,
             actor_id, _now(), json.dumps(payload, sort_keys=True, separators=(",", ":"))),
        )

    def register(
        self, tenant_id: str, connector_id: str, source_ref: str,
        key_id: str, public_key: str, actor_id: str,
    ) -> dict[str, Any]:
        self._validate_identity(connector_id, key_id)
        encoded, _ = self._validate_public_key(public_key)
        if not isinstance(source_ref, str) or not source_ref.startswith("postgresql-catalog://") or len(source_ref) > 1024:
            raise ContextValidationError("source_ref must be a credential-free postgresql-catalog URI")
        if not isinstance(actor_id, str) or not actor_id.strip() or len(actor_id) > 256:
            raise ContextValidationError("actor_id is invalid")
        now = _now()
        try:
            with self._connection() as db:
                db.execute("BEGIN IMMEDIATE")
                db.execute(
                    "INSERT INTO pg_connectors VALUES (?, ?, ?, 'active', ?, ?)",
                    (tenant_id, connector_id, source_ref, now, actor_id),
                )
                db.execute(
                    "INSERT INTO pg_connector_keys VALUES (?, ?, ?, ?, 'active', ?, ?)",
                    (tenant_id, connector_id, key_id, encoded, now, actor_id),
                )
                self._event(db, tenant_id, connector_id, "connector.registered",
                            actor_id, None, {"source_ref": source_ref})
                self._event(db, tenant_id, connector_id, "connector.key_added",
                            actor_id, key_id, {"public_key_sha256": __import__("hashlib").sha256(encoded.encode()).hexdigest()})
        except sqlite3.IntegrityError as exc:
            raise ContextConflictError("Connector identity or source_ref already exists for this tenant") from exc
        return {"connector_id": connector_id, "source_ref": source_ref,
                "key_id": key_id, "status": "active", "created_at": now}

    def add_key(
        self, tenant_id: str, connector_id: str, key_id: str,
        public_key: str, actor_id: str,
    ) -> dict[str, Any]:
        self._validate_identity(connector_id, key_id)
        encoded, _ = self._validate_public_key(public_key)
        now = _now()
        try:
            with self._connection() as db:
                db.execute("BEGIN IMMEDIATE")
                connector = db.execute(
                    "SELECT status FROM pg_connectors WHERE tenant_id=? AND connector_id=?",
                    (tenant_id, connector_id),
                ).fetchone()
                if connector is None:
                    raise ContextNotFoundError("PostgreSQL connector not found")
                if connector["status"] != "active":
                    raise ContextConflictError("Cannot rotate keys on a revoked connector")
                db.execute(
                    "INSERT INTO pg_connector_keys VALUES (?, ?, ?, ?, 'active', ?, ?)",
                    (tenant_id, connector_id, key_id, encoded, now, actor_id),
                )
                self._event(db, tenant_id, connector_id, "connector.key_added",
                            actor_id, key_id, {"public_key_sha256": __import__("hashlib").sha256(encoded.encode()).hexdigest()})
        except sqlite3.IntegrityError as exc:
            raise ContextConflictError("Connector key ID already exists") from exc
        return {"connector_id": connector_id, "key_id": key_id, "status": "active", "created_at": now}

    def revoke_key(self, tenant_id: str, connector_id: str, key_id: str,
                   actor_id: str) -> dict[str, Any]:
        self._validate_identity(connector_id, key_id)
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                """SELECT status FROM pg_connector_keys
                WHERE tenant_id=? AND connector_id=? AND key_id=?""",
                (tenant_id, connector_id, key_id),
            ).fetchone()
            if row is None:
                raise ContextNotFoundError("PostgreSQL connector key not found")
            if row["status"] == "revoked":
                raise ContextConflictError("Connector key is already revoked")
            db.execute(
                "INSERT INTO pg_connector_events VALUES (?, ?, ?, 'connector.key_revoked', ?, ?, ?, ?)",
                (str(uuid.uuid4()), tenant_id, connector_id, key_id, actor_id, _now(),
                 json.dumps({"reason": "operator_revocation"}, separators=(",", ":"))),
            )
            db.execute(
                """INSERT INTO pg_connector_keys
                (tenant_id, connector_id, key_id, public_key_b64, status, created_at, created_by)
                SELECT tenant_id, connector_id, key_id, public_key_b64, 'revoked', ?, ?
                FROM pg_connector_keys WHERE tenant_id=? AND connector_id=? AND key_id=?""",
                (_now(), actor_id, tenant_id, connector_id, key_id),
            )
        return {"connector_id": connector_id, "key_id": key_id, "status": "revoked"}

    def get_active_key(self, tenant_id: str, connector_id: str,
                       key_id: str, source_ref: str) -> bytes:
        self._validate_identity(connector_id, key_id)
        with self._connection() as db:
            connector = db.execute(
                """SELECT source_ref, status FROM pg_connectors
                WHERE tenant_id=? AND connector_id=?""",
                (tenant_id, connector_id),
            ).fetchone()
            if connector is None:
                raise ContextNotFoundError("PostgreSQL connector not found")
            if connector["status"] != "active" or connector["source_ref"] != source_ref:
                raise ContextValidationError("Connector is revoked or source_ref does not match registration")
            row = db.execute(
                """SELECT public_key_b64 FROM pg_connector_keys
                WHERE tenant_id=? AND connector_id=? AND key_id=? AND status='active'
                ORDER BY created_at DESC LIMIT 1""",
                (tenant_id, connector_id, key_id),
            ).fetchone()
        if row is None:
            raise ContextValidationError("Connector signing key is unknown or revoked")
        return base64.b64decode(row["public_key_b64"], validate=True)

    def list_connectors(self, tenant_id: str) -> list[dict[str, Any]]:
        with self._connection() as db:
            rows = db.execute(
                """SELECT c.connector_id, c.source_ref, c.status, c.created_at, c.created_by,
                k.key_id, k.status AS key_status, k.created_at AS key_created_at
                FROM pg_connectors c LEFT JOIN pg_connector_keys k
                ON c.tenant_id=k.tenant_id AND c.connector_id=k.connector_id
                WHERE c.tenant_id=? ORDER BY c.connector_id, k.created_at""",
                (tenant_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def events(self, tenant_id: str, connector_id: str) -> list[dict[str, Any]]:
        with self._connection() as db:
            rows = db.execute(
                """SELECT event_id, connector_id, event_type, key_id, actor_id,
                occurred_at, payload_json FROM pg_connector_events
                WHERE tenant_id=? AND connector_id=? ORDER BY occurred_at, event_id""",
                (tenant_id, connector_id),
            ).fetchall()
        return [{**dict(row), "payload": json.loads(row["payload_json"])} for row in rows]
