"""Tenant-scoped cognitive run state and append-only lifecycle event journal.

This service records lifecycle state only. It does not perform reasoning, invoke
capabilities, execute agents, attest evidence, or consolidate memory.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .cognitive_contract import validate_cognitive_event, validate_stage_transition

MAX_EVENT_BYTES = 64 * 1024
FORBIDDEN_PAYLOAD_KEYS = {
    "access_token", "refresh_token", "authorization", "credential", "credentials",
    "password", "secret", "private_key", "tenant_id", "principal", "permissions",
    "execute", "executable", "code", "script", "command", "shell", "tool_arguments",
    "raw_prompt", "prompt", "raw_input", "raw_output",
}
TERMINAL_MEMORY_EVENTS = {"memory.accepted", "memory.rejected"}


class CognitiveRunError(Exception):
    """Base cognitive run failure."""


class CognitiveRunNotFoundError(CognitiveRunError):
    """Run does not exist in the requested tenant."""


class CognitiveRunConflictError(CognitiveRunError):
    """Idempotency key or run state conflicts with the request."""


class CognitiveRunValidationError(CognitiveRunError):
    """Lifecycle event violates its contract or state transition."""


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _canonical(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


class CognitiveRunService:
    """Persist tenant-scoped cognitive runs and immutable ordered lifecycle events."""

    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)
        self._memory = self.database_path == ":memory:"
        self._dsn = (
            f"file:agentbox-cognition-{id(self)}?mode=memory&cache=shared"
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

    def _connect(self) -> sqlite3.Connection:
        if self._closed:
            raise RuntimeError("cognitive run service is closed")
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
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS cognitive_runs (
                    tenant_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    trace_id TEXT NOT NULL,
                    goal_ref TEXT NOT NULL,
                    agent_ref TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    agent_version TEXT NOT NULL,
                    agent_content_hash TEXT NOT NULL,
                    current_stage TEXT NOT NULL CHECK(current_stage IN (
                        'intent','context','cognition','capability','responsibility',
                        'execution','observation','verification','memory'
                    )),
                    next_sequence INTEGER NOT NULL CHECK(next_sequence >= 2),
                    status TEXT NOT NULL CHECK(status IN ('active','completed')),
                    create_idempotency_key_hash TEXT NOT NULL,
                    create_request_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, run_id),
                    UNIQUE (tenant_id, create_idempotency_key_hash),
                    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id)
                );
                CREATE INDEX IF NOT EXISTS idx_cognitive_runs_tenant_created
                    ON cognitive_runs(tenant_id, created_at DESC);
                CREATE TABLE IF NOT EXISTS cognitive_events (
                    tenant_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL CHECK(sequence >= 1),
                    event_id TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    idempotency_key_hash TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    event_json TEXT NOT NULL,
                    event_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, run_id, sequence),
                    UNIQUE (tenant_id, event_id),
                    UNIQUE (tenant_id, run_id, idempotency_key_hash),
                    FOREIGN KEY (tenant_id, run_id)
                        REFERENCES cognitive_runs(tenant_id, run_id)
                );
                CREATE INDEX IF NOT EXISTS idx_cognitive_events_trace
                    ON cognitive_events(tenant_id, run_id, sequence);
                CREATE TRIGGER IF NOT EXISTS cognitive_events_no_update
                BEFORE UPDATE ON cognitive_events
                BEGIN
                    SELECT RAISE(ABORT, 'cognitive events are append-only');
                END;
                CREATE TRIGGER IF NOT EXISTS cognitive_events_no_delete
                BEFORE DELETE ON cognitive_events
                BEGIN
                    SELECT RAISE(ABORT, 'cognitive events are append-only');
                END;
            """)

    @staticmethod
    def _run_record(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "tenant_id": row["tenant_id"],
            "run_id": row["run_id"],
            "trace_id": row["trace_id"],
            "goal_ref": row["goal_ref"],
            "agent_ref": row["agent_ref"],
            "agent_id": row["agent_id"],
            "agent_version": row["agent_version"],
            "agent_content_hash": row["agent_content_hash"],
            "current_stage": row["current_stage"],
            "next_sequence": row["next_sequence"],
            "status": row["status"],
            "created_at": row["created_at"],
            "created_by": row["created_by"],
            "updated_at": row["updated_at"],
        }

    @staticmethod
    def _event_record(row: sqlite3.Row) -> dict[str, Any]:
        return json.loads(row["event_json"])

    def create_run(
        self,
        goal_ref: str,
        agent_ref: str,
        agent_id: str,
        agent_version: str,
        agent_content_hash: str,
        tenant_id: str,
        actor_id: str,
        idempotency_key: str,
    ) -> tuple[dict[str, Any], dict[str, Any], bool]:
        values = (goal_ref, agent_ref, agent_id, agent_version, agent_content_hash,
                  tenant_id, actor_id, idempotency_key)
        if any(not isinstance(value, str) or not value.strip() for value in values):
            raise CognitiveRunValidationError("Run identity and references must be non-empty strings")
        if len(goal_ref) > 1024 or len(agent_ref) > 512 or len(idempotency_key) > 256:
            raise CognitiveRunValidationError("Run reference or idempotency key exceeds its limit")
        if len(agent_content_hash) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in agent_content_hash):
            raise CognitiveRunValidationError("Agent content hash must be SHA-256 hex")
        request = {
            "goal_ref": goal_ref, "agent_ref": agent_ref,
            "agent_content_hash": agent_content_hash, "actor_id": actor_id,
        }
        request_hash = _digest(request)
        idempotency_key_hash = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
        now = _now()
        run_id = str(uuid.uuid4())
        trace_id = str(uuid.uuid4())
        event = {
            "schema_version": "1.0.0",
            "event_id": str(uuid.uuid4()),
            "run_id": run_id,
            "trace_id": trace_id,
            "tenant_id": tenant_id,
            "agent_ref": agent_ref,
            "agent_content_hash": agent_content_hash,
            "sequence": 1,
            "stage": "intent",
            "event_type": "intent.accepted",
            "actor": {"kind": "user", "id": actor_id},
            "occurred_at": now,
            "evidence_status": "not_applicable",
            "input_refs": [goal_ref],
            "payload": {"goal_ref": goal_ref},
        }
        errors = validate_cognitive_event(event)
        if errors:
            raise CognitiveRunValidationError(_canonical(errors))
        event_json = _canonical(event)
        event_hash = hashlib.sha256(event_json.encode("utf-8")).hexdigest()

        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM cognitive_runs WHERE tenant_id=? AND create_idempotency_key_hash=?",
                (tenant_id, idempotency_key_hash),
            ).fetchone()
            if existing is not None:
                if existing["create_request_hash"] != request_hash:
                    raise CognitiveRunConflictError("Run idempotency key was reused with different content")
                event_row = connection.execute(
                    "SELECT * FROM cognitive_events WHERE tenant_id=? AND run_id=? AND sequence=1",
                    (tenant_id, existing["run_id"]),
                ).fetchone()
                return self._run_record(existing), self._event_record(event_row), False

            connection.execute(
                """INSERT INTO cognitive_runs (
                    tenant_id,run_id,trace_id,goal_ref,agent_ref,agent_id,agent_version,
                    agent_content_hash,current_stage,next_sequence,status,create_idempotency_key_hash,
                    create_request_hash,created_at,created_by,updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (tenant_id,run_id,trace_id,goal_ref,agent_ref,agent_id,agent_version,
                 agent_content_hash,"intent",2,"active",idempotency_key_hash,request_hash,
                 now,actor_id,now),
            )
            connection.execute(
                """INSERT INTO cognitive_events (
                    tenant_id,run_id,sequence,event_id,stage,event_type,idempotency_key_hash,
                    request_hash,event_json,event_hash,created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (tenant_id,run_id,1,event["event_id"],"intent","intent.accepted",
                 idempotency_key_hash,request_hash,event_json,event_hash,now),
            )
            row = connection.execute(
                "SELECT * FROM cognitive_runs WHERE tenant_id=? AND run_id=?",
                (tenant_id,run_id),
            ).fetchone()
        return self._run_record(row), event, True

    def append_event(
        self,
        run_id: str,
        event_input: dict[str, Any],
        tenant_id: str,
        actor_id: str,
        idempotency_key: str,
    ) -> tuple[dict[str, Any], bool]:
        if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 256:
            raise CognitiveRunValidationError("Idempotency-Key must contain 1 to 256 characters")
        allowed = {
            "stage", "event_type", "evidence_status", "input_refs", "output_refs",
            "evidence_refs", "payload", "error_code", "causation_event_id", "correlation_id",
        }
        if not isinstance(event_input, dict) or set(event_input) - allowed:
            raise CognitiveRunValidationError("Cognitive event request contains unsupported fields")
        try:
            request_json = _canonical(event_input)
        except (TypeError, ValueError) as exc:
            raise CognitiveRunValidationError("Cognitive event must contain finite JSON values") from exc
        if len(request_json.encode("utf-8")) > MAX_EVENT_BYTES:
            raise CognitiveRunValidationError("Cognitive event request exceeds the 64 KiB limit")
        request_hash = hashlib.sha256(
            _canonical({"event": event_input, "actor_id": actor_id}).encode("utf-8")
        ).hexdigest()
        idempotency_key_hash = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
        payload = event_input.get("payload", {})
        if self._contains_forbidden_payload_key(payload):
            raise CognitiveRunValidationError(
                "Cognitive event payload contains a forbidden authority or executable field"
            )
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """SELECT * FROM cognitive_events
                   WHERE tenant_id=? AND run_id=? AND idempotency_key_hash=?""",
                (tenant_id,run_id,idempotency_key_hash),
            ).fetchone()
            if existing is not None:
                if existing["request_hash"] != request_hash:
                    raise CognitiveRunConflictError("Event idempotency key was reused with different content")
                return self._event_record(existing), False

            run = connection.execute(
                "SELECT * FROM cognitive_runs WHERE tenant_id=? AND run_id=?",
                (tenant_id,run_id),
            ).fetchone()
            if run is None:
                raise CognitiveRunNotFoundError("Cognitive run was not found")
            if run["status"] != "active":
                raise CognitiveRunConflictError("Cognitive run is already completed")
            stage = event_input.get("stage")
            errors = validate_stage_transition(run["current_stage"], stage)
            if errors:
                raise CognitiveRunValidationError(_canonical(errors))

            now = _now()
            event = {
                "schema_version": "1.0.0",
                "event_id": str(uuid.uuid4()),
                "run_id": run_id,
                "trace_id": run["trace_id"],
                "tenant_id": tenant_id,
                "agent_ref": run["agent_ref"],
                "agent_content_hash": run["agent_content_hash"],
                "sequence": run["next_sequence"],
                "stage": stage,
                "event_type": event_input.get("event_type"),
                "actor": {"kind": "user", "id": actor_id},
                "occurred_at": now,
                "evidence_status": event_input.get("evidence_status", "unverified"),
                "payload": event_input.get("payload", {}),
            }
            for field in (
                "input_refs","output_refs","evidence_refs","error_code",
                "causation_event_id","correlation_id",
            ):
                if field in event_input:
                    event[field] = event_input[field]
            errors = validate_cognitive_event(event)
            if errors:
                raise CognitiveRunValidationError(_canonical(errors))
            event_json = _canonical(event)
            if len(event_json.encode("utf-8")) > MAX_EVENT_BYTES:
                raise CognitiveRunValidationError("Cognitive event exceeds the 64 KiB limit")
            event_hash = hashlib.sha256(event_json.encode("utf-8")).hexdigest()
            sequence = run["next_sequence"]
            connection.execute(
                """INSERT INTO cognitive_events (
                    tenant_id,run_id,sequence,event_id,stage,event_type,idempotency_key_hash,
                    request_hash,event_json,event_hash,created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (tenant_id,run_id,sequence,event["event_id"],stage,event["event_type"],
                 idempotency_key_hash,request_hash,event_json,event_hash,now),
            )
            status = (
                "completed"
                if stage == "memory" and event["event_type"] in TERMINAL_MEMORY_EVENTS
                else "active"
            )
            connection.execute(
                """UPDATE cognitive_runs SET current_stage=?,next_sequence=?,
                   status=?,updated_at=? WHERE tenant_id=? AND run_id=?""",
                (stage,sequence+1,status,now,tenant_id,run_id),
            )
        return event, True

    @classmethod
    def _contains_forbidden_payload_key(cls, value: Any) -> bool:
        if isinstance(value, dict):
            for key, nested in value.items():
                if isinstance(key, str) and key.lower() in FORBIDDEN_PAYLOAD_KEYS:
                    return True
                if cls._contains_forbidden_payload_key(nested):
                    return True
        elif isinstance(value, list):
            return any(cls._contains_forbidden_payload_key(item) for item in value)
        return False

    def get_run(self, run_id: str, tenant_id: str) -> dict[str, Any]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM cognitive_runs WHERE tenant_id=? AND run_id=?",
                (tenant_id,run_id),
            ).fetchone()
        if row is None:
            raise CognitiveRunNotFoundError("Cognitive run was not found")
        return self._run_record(row)

    def list_events(
        self, run_id: str, tenant_id: str, after_sequence: int = 0, limit: int = 100
    ) -> list[dict[str, Any]]:
        if type(after_sequence) is not int or after_sequence < 0 or type(limit) is not int or not 1 <= limit <= 200:
            raise CognitiveRunValidationError("Invalid event pagination")
        with self._connection() as connection:
            run = connection.execute(
                "SELECT 1 FROM cognitive_runs WHERE tenant_id=? AND run_id=?",
                (tenant_id,run_id),
            ).fetchone()
            if run is None:
                raise CognitiveRunNotFoundError("Cognitive run was not found")
            rows = connection.execute(
                """SELECT * FROM cognitive_events
                   WHERE tenant_id=? AND run_id=? AND sequence>?
                   ORDER BY sequence LIMIT ?""",
                (tenant_id,run_id,after_sequence,limit),
            ).fetchall()
        return [self._event_record(row) for row in rows]
