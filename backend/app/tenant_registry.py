"""Server-owned SQLite tenant registry with explicit lifecycle transitions."""
from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .tenant import TenantRecord, TenantStatus, utc_now, validate_tenant_id, validate_transition


class TenantNotFoundError(Exception):
    """The requested AgentBox tenant does not exist."""


class TenantConflictError(Exception):
    """The requested tenant identity already exists."""


class TenantRegistry:
    """Persistent tenant authority. Callers must authorize administrators separately."""

    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)
        self._memory = self.database_path == ":memory:"
        self._dsn = f"file:agentbox-tenants-{id(self)}?mode=memory&cache=shared" if self._memory else self.database_path
        self._keeper = sqlite3.connect(self._dsn, uri=True, timeout=10) if self._memory else None
        if not self._memory:
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self._closed = False
        self._initialize()

    def close(self) -> None:
        """Release the shared in-memory database keeper and close this store."""
        if self._closed:
            return
        self._closed = True
        if self._keeper is not None:
            self._keeper.close()
            self._keeper = None

    def _connect(self) -> sqlite3.Connection:
        if self._closed:
            raise RuntimeError("SQLite store is closed")
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
                CREATE TABLE IF NOT EXISTS tenants (
                    tenant_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL CHECK(length(display_name) BETWEEN 1 AND 200),
                    status TEXT NOT NULL CHECK(status IN ('pending','active','suspended','decommissioned')),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS tenant_audit (
                    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    action TEXT NOT NULL CHECK(action IN ('tenant.created','tenant.status_changed')),
                    previous_status TEXT,
                    new_status TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id)
                )
            """)
            connection.execute("""
                CREATE TRIGGER IF NOT EXISTS tenant_audit_no_update
                BEFORE UPDATE ON tenant_audit BEGIN
                    SELECT RAISE(ABORT, 'AgentBox tenant audit is append-only');
                END
            """)
            connection.execute("""
                CREATE TRIGGER IF NOT EXISTS tenant_audit_no_delete
                BEFORE DELETE ON tenant_audit BEGIN
                    SELECT RAISE(ABORT, 'AgentBox tenant audit is append-only');
                END
            """)

    @staticmethod
    def _record(row: sqlite3.Row) -> TenantRecord:
        return TenantRecord(
            tenant_id=row["tenant_id"],
            display_name=row["display_name"],
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            metadata=json.loads(row["metadata_json"]),
        )

    def create(
        self,
        tenant_id: str,
        display_name: str,
        actor_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> TenantRecord:
        validate_tenant_id(tenant_id)
        if not isinstance(display_name, str) or not display_name.strip() or len(display_name) > 200:
            raise ValueError("display_name must contain 1 to 200 characters")
        if not isinstance(actor_id, str) or not actor_id.strip() or len(actor_id) > 256:
            raise ValueError("actor_id must contain 1 to 256 characters")
        metadata = metadata or {}
        if not isinstance(metadata, dict) or len(metadata) > 32:
            raise ValueError("metadata must be an object with at most 32 entries")
        if any(not isinstance(k, str) or not isinstance(v, (str, int, float, bool, type(None))) for k, v in metadata.items()):
            raise ValueError("metadata values must be scalar JSON values")
        serialized = json.dumps(metadata, sort_keys=True, separators=(",", ":"), allow_nan=False)
        now = utc_now()
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if connection.execute("SELECT 1 FROM tenants WHERE tenant_id = ?", (tenant_id,)).fetchone():
                raise TenantConflictError(f"AgentBox tenant already exists: {tenant_id}")
            connection.execute(
                "INSERT INTO tenants VALUES (?, ?, 'pending', ?, ?, ?)",
                (tenant_id, display_name.strip(), now, now, serialized),
            )
            connection.execute(
                """INSERT INTO tenant_audit
                (tenant_id, action, previous_status, new_status, actor_id, occurred_at)
                VALUES (?, 'tenant.created', NULL, 'pending', ?, ?)""",
                (tenant_id, actor_id, now),
            )
            row = connection.execute("SELECT * FROM tenants WHERE tenant_id = ?", (tenant_id,)).fetchone()
        return self._record(row)

    def get(self, tenant_id: str) -> TenantRecord:
        validate_tenant_id(tenant_id)
        with self._connection() as connection:
            row = connection.execute("SELECT * FROM tenants WHERE tenant_id = ?", (tenant_id,)).fetchone()
        if row is None:
            raise TenantNotFoundError(tenant_id)
        return self._record(row)

    def list(self, limit: int = 100, offset: int = 0) -> list[TenantRecord]:
        if not 1 <= limit <= 500 or offset < 0:
            raise ValueError("limit must be 1-500 and offset must be non-negative")
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM tenants ORDER BY created_at, tenant_id LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [self._record(row) for row in rows]

    def transition(self, tenant_id: str, target: TenantStatus, actor_id: str) -> TenantRecord:
        validate_tenant_id(tenant_id)
        if not isinstance(actor_id, str) or not actor_id.strip() or len(actor_id) > 256:
            raise ValueError("actor_id must contain 1 to 256 characters")
        now = utc_now()
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT * FROM tenants WHERE tenant_id = ?", (tenant_id,)).fetchone()
            if row is None:
                raise TenantNotFoundError(tenant_id)
            current = row["status"]
            validate_transition(current, target)
            connection.execute(
                "UPDATE tenants SET status = ?, updated_at = ? WHERE tenant_id = ?",
                (target, now, tenant_id),
            )
            connection.execute(
                """INSERT INTO tenant_audit
                (tenant_id, action, previous_status, new_status, actor_id, occurred_at)
                VALUES (?, 'tenant.status_changed', ?, ?, ?, ?)""",
                (tenant_id, current, target, actor_id, now),
            )
            updated = connection.execute("SELECT * FROM tenants WHERE tenant_id = ?", (tenant_id,)).fetchone()
        return self._record(updated)

    def audit_events(self, tenant_id: str) -> list[dict[str, Any]]:
        validate_tenant_id(tenant_id)
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM tenant_audit WHERE tenant_id = ? ORDER BY audit_id",
                (tenant_id,),
            ).fetchall()
        return [dict(row) for row in rows]
