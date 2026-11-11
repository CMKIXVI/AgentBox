"""SQLite-backed immutable agent version registry."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class VersionConflictError(Exception):
    """An immutable agent version already exists with different content."""


class AgentNotFoundError(Exception):
    """An agent version does not exist."""


@dataclass(frozen=True)
class AgentVersionRecord:
    agent_id: str
    version: str
    content_hash: str
    manifest: dict[str, Any]
    parent_artifact_id: str | None
    created_at: str
    tenant_id: str


def canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def content_hash(manifest: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(manifest).encode("utf-8")).hexdigest()


LEGACY_TENANT_ID = "__legacy_unassigned__"


class AgentRegistry:
    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)
        self._use_uri = self.database_path == ":memory:"
        self._dsn = (
            f"file:agentbox-{id(self)}?mode=memory&cache=shared"
            if self._use_uri else self.database_path
        )
        self._keeper = (
            sqlite3.connect(self._dsn, uri=True, timeout=10)
            if self._use_uri else None
        )
        if not self._use_uri:
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._dsn, uri=self._use_uri, timeout=10)
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
            if self.database_path != ":memory:":
                connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_versions (
                    agent_id TEXT NOT NULL,
                    version TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    manifest_json TEXT NOT NULL,
                    parent_artifact_id TEXT,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (agent_id, version)
                )
                """
            )
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(agent_versions)")}
            if "tenant_id" not in columns:
                connection.execute(
                    "ALTER TABLE agent_versions ADD COLUMN tenant_id TEXT NOT NULL "
                    "DEFAULT '__legacy_unassigned__'"
                )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_agent_versions_tenant_agent "
                "ON agent_versions(tenant_id, agent_id, created_at)"
            )

    @staticmethod
    def _to_record(row: sqlite3.Row) -> AgentVersionRecord:
        return AgentVersionRecord(
            agent_id=row["agent_id"],
            version=row["version"],
            content_hash=row["content_hash"],
            manifest=json.loads(row["manifest_json"]),
            parent_artifact_id=row["parent_artifact_id"],
            created_at=row["created_at"],
            tenant_id=row["tenant_id"],
        )

    def create(
        self, manifest: dict[str, Any], parent_artifact_id: str | None = None,
        tenant_id: str = LEGACY_TENANT_ID,
    ) -> tuple[AgentVersionRecord, bool]:
        agent_id = manifest["agent_id"]
        version = manifest["version"]
        serialized = canonical_json(manifest)
        digest = content_hash(manifest)
        created_at = manifest["provenance"]["created_at"]

        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM agent_versions WHERE tenant_id = ? AND agent_id = ? AND version = ?",
                (tenant_id, agent_id, version),
            ).fetchone()
            if existing:
                record = self._to_record(existing)
                if record.content_hash != digest or record.parent_artifact_id != parent_artifact_id:
                    raise VersionConflictError(f"{agent_id}@{version} is immutable and already exists")
                return record, False

            connection.execute(
                """
                INSERT INTO agent_versions
                    (agent_id, version, content_hash, manifest_json, parent_artifact_id, created_at, tenant_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (agent_id, version, digest, serialized, parent_artifact_id, created_at, tenant_id),
            )
            row = connection.execute(
                "SELECT * FROM agent_versions WHERE tenant_id = ? AND agent_id = ? AND version = ?",
                (tenant_id, agent_id, version),
            ).fetchone()
        return self._to_record(row), True

    def get(
        self, agent_id: str, version: str, tenant_id: str = LEGACY_TENANT_ID
    ) -> AgentVersionRecord:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM agent_versions WHERE agent_id = ? AND version = ?",
                (agent_id, version),
            ).fetchone()
        if row is None:
            raise AgentNotFoundError(f"{agent_id}@{version} was not found")
        return self._to_record(row)

    def list(
        self, agent_id: str, limit: int = 50, offset: int = 0,
        tenant_id: str = LEGACY_TENANT_ID,
    ) -> list[AgentVersionRecord]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM agent_versions WHERE tenant_id = ? AND agent_id = ?
                ORDER BY created_at DESC, version DESC LIMIT ? OFFSET ?
                """,
                (tenant_id, agent_id, limit, offset),
            ).fetchall()
        return [self._to_record(row) for row in rows]
