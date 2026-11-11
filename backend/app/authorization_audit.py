"""Append-only authorization decision audit store."""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class AuthorizationAuditStore:
    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)
        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self._dsn = (
            f"file:agentbox-auth-audit-{id(self)}?mode=memory&cache=shared"
            if self.database_path == ":memory:" else self.database_path
        )
        self._uri = self.database_path == ":memory:"
        self._keeper = sqlite3.connect(self._dsn, uri=True) if self._uri else None
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS authorization_decisions (
                    event_id TEXT PRIMARY KEY,
                    subject_id TEXT,
                    tenant_id TEXT,
                    capability_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    allowed INTEGER NOT NULL CHECK (allowed IN (0, 1)),
                    reason TEXT NOT NULL,
                    matched_policy_ids_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            connection.execute("""
                CREATE TRIGGER IF NOT EXISTS authorization_decisions_no_update
                BEFORE UPDATE ON authorization_decisions
                BEGIN SELECT RAISE(ABORT, 'authorization audit is append-only'); END
            """)
            connection.execute("""
                CREATE TRIGGER IF NOT EXISTS authorization_decisions_no_delete
                BEFORE DELETE ON authorization_decisions
                BEGIN SELECT RAISE(ABORT, 'authorization audit is append-only'); END
            """)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._dsn, uri=self._uri, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def append(
        self, principal: Any, capability_id: str, action: str, resource_id: str,
        decision: dict[str, Any], created_at: datetime | None = None,
    ) -> dict[str, Any]:
        timestamp = created_at or datetime.now(UTC)
        if timestamp.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        event = {
            "event_id": str(uuid.uuid4()),
            "subject_id": principal.subject_id if principal else None,
            "tenant_id": principal.tenant_id if principal else None,
            "capability_id": capability_id,
            "action": action,
            "resource_id": resource_id,
            "allowed": bool(decision.get("allowed", False)),
            "reason": str(decision.get("reason", "unspecified")),
            "matched_policy_ids": sorted(decision.get("matched_policy_ids", [])),
            "created_at": timestamp.isoformat(),
        }
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO authorization_decisions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (event["event_id"], event["subject_id"], event["tenant_id"], capability_id,
                 action, resource_id, int(event["allowed"]), event["reason"],
                 json.dumps(event["matched_policy_ids"], separators=(",", ":")), event["created_at"]),
            )
        return event

    def list_events(self, limit: int = 100) -> list[dict[str, Any]]:
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM authorization_decisions ORDER BY created_at DESC, event_id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [{
            "event_id": row["event_id"], "subject_id": row["subject_id"],
            "tenant_id": row["tenant_id"], "capability_id": row["capability_id"],
            "action": row["action"], "resource_id": row["resource_id"],
            "allowed": bool(row["allowed"]), "reason": row["reason"],
            "matched_policy_ids": json.loads(row["matched_policy_ids_json"]),
            "created_at": row["created_at"],
        } for row in rows]
