"""SQLite-backed, tenant-scoped durable execution-job lifecycle.

This service owns job admission and state, not workload execution. SQLite mode is
single-instance only; workers must treat delivery as at-least-once.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .registry import canonical_json

JOB_STATES = frozenset({
    "queued", "leased", "running", "cancel_requested", "succeeded",
    "failed", "cancelled", "timed_out",
})
TERMINAL_STATES = frozenset({"succeeded", "failed", "cancelled", "timed_out"})
WORKLOAD_KINDS = frozenset({"provider_invocation", "sandbox_workload"})
MAX_RESULT_BYTES = 64 * 1024
MAX_PAYLOAD_BYTES = 256 * 1024


def _now() -> datetime:
    return datetime.now(UTC)


def _timestamp(value: datetime | None = None) -> str:
    instant = value or _now()
    if instant.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return instant.astimezone(UTC).isoformat()


class JobError(Exception):
    """Base durable-job error."""


class JobNotFoundError(JobError):
    """Job does not exist in the requested tenant."""


class JobConflictError(JobError):
    """Idempotency or state conflict."""


class JobLeaseError(JobError):
    """Worker lease is absent, expired, or owned by another worker."""


class DurableExecutionJobService:
    """Transactional SQLite queue for one AgentBox API/worker instance."""

    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)
        if self.database_path == ":memory:":
            self._dsn = f"file:agentbox-jobs-{id(self)}?mode=memory&cache=shared"
            self._uri = True
            self._keeper = sqlite3.connect(self._dsn, uri=True, timeout=10)
        else:
            self._dsn = self.database_path
            self._uri = False
            self._keeper = None
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._dsn, uri=self._uri, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 10000")
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS execution_jobs (
                    job_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    subject_id TEXT NOT NULL,
                    principal_type TEXT NOT NULL,
                    workload_kind TEXT NOT NULL,
                    handler_id TEXT NOT NULL,
                    handler_version TEXT NOT NULL,
                    workload_ref TEXT NOT NULL,
                    workload_hash TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    idempotency_key_hash TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    state TEXT NOT NULL,
                    attempt INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL,
                    priority INTEGER NOT NULL DEFAULT 0,
                    available_at TEXT NOT NULL,
                    worker_id TEXT,
                    lease_token TEXT,
                    lease_expires_at TEXT,
                    heartbeat_at TEXT,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    updated_at TEXT NOT NULL,
                    result_json TEXT,
                    error_code TEXT,
                    cancel_requested_at TEXT,
                    correlation_id TEXT NOT NULL,
                    UNIQUE (tenant_id, idempotency_key_hash),
                    CHECK (state IN ('queued','leased','running','cancel_requested',
                        'succeeded','failed','cancelled','timed_out')),
                    CHECK (attempt >= 0 AND max_attempts BETWEEN 1 AND 20)
                );
                CREATE INDEX IF NOT EXISTS idx_execution_jobs_claim
                    ON execution_jobs(state, available_at, priority DESC, created_at);
                CREATE INDEX IF NOT EXISTS idx_execution_jobs_tenant
                    ON execution_jobs(tenant_id, created_at DESC);
                CREATE TABLE IF NOT EXISTS execution_job_events (
                    event_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL REFERENCES execution_jobs(job_id),
                    tenant_id TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    from_state TEXT,
                    to_state TEXT NOT NULL,
                    reason_code TEXT NOT NULL,
                    attempt INTEGER NOT NULL,
                    lease_token_fingerprint TEXT,
                    correlation_id TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_execution_job_events_tenant
                    ON execution_job_events(tenant_id, job_id, created_at);
                CREATE TRIGGER IF NOT EXISTS execution_job_events_no_update
                    BEFORE UPDATE ON execution_job_events
                    BEGIN SELECT RAISE(ABORT, 'execution job events are append-only'); END;
                CREATE TRIGGER IF NOT EXISTS execution_job_events_no_delete
                    BEFORE DELETE ON execution_job_events
                    BEGIN SELECT RAISE(ABORT, 'execution job events are append-only'); END;
            """)

    @staticmethod
    def _fingerprint(token: str | None) -> str | None:
        return hashlib.sha256(token.encode()).hexdigest() if token else None

    @staticmethod
    def _record(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "job_id": row["job_id"],
            "tenant_id": row["tenant_id"],
            "subject_id": row["subject_id"],
            "principal_type": row["principal_type"],
            "workload_kind": row["workload_kind"],
            "handler_id": row["handler_id"],
            "handler_version": row["handler_version"],
            "workload_ref": row["workload_ref"],
            "workload_hash": row["workload_hash"],
            "state": row["state"],
            "attempt": row["attempt"],
            "max_attempts": row["max_attempts"],
            "priority": row["priority"],
            "created_at": row["created_at"],
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
            "updated_at": row["updated_at"],
            "result": json.loads(row["result_json"]) if row["result_json"] else None,
            "error_code": row["error_code"],
            "cancel_requested_at": row["cancel_requested_at"],
            "correlation_id": row["correlation_id"],
        }

    @staticmethod
    def _event(
        connection: sqlite3.Connection, row: sqlite3.Row, actor_id: str,
        previous: str | None, target: str, reason: str, token: str | None = None,
    ) -> None:
        connection.execute(
            """INSERT INTO execution_job_events
            (event_id, job_id, tenant_id, actor_id, from_state, to_state, reason_code,
             attempt, lease_token_fingerprint, correlation_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (str(uuid.uuid4()), row["job_id"], row["tenant_id"], actor_id, previous,
             target, reason, row["attempt"], DurableExecutionJobService._fingerprint(token),
             row["correlation_id"], _timestamp()),
        )

    def create(
        self, *, tenant_id: str, subject_id: str, principal_type: str,
        workload_kind: str, handler_id: str, handler_version: str,
        workload_ref: str, workload_hash: str, payload: dict[str, Any],
        idempotency_key: str, max_attempts: int = 1, priority: int = 0,
        correlation_id: str | None = None,
    ) -> tuple[dict[str, Any], bool]:
        required = (tenant_id, subject_id, principal_type, handler_id, handler_version,
                    workload_ref, idempotency_key)
        if not all(isinstance(item, str) and item.strip() for item in required):
            raise ValueError("tenant, principal, handler, workload and idempotency fields are required")
        if workload_kind not in WORKLOAD_KINDS:
            raise ValueError("unsupported workload_kind")
        if len(idempotency_key) > 128:
            raise ValueError("idempotency_key must be at most 128 characters")
        if len(workload_hash) != 64 or any(c not in "0123456789abcdefABCDEF" for c in workload_hash):
            raise ValueError("workload_hash must be a SHA-256 hex digest")
        if not 1 <= max_attempts <= 20:
            raise ValueError("max_attempts must be between 1 and 20")
        if not -100 <= priority <= 100:
            raise ValueError("priority must be between -100 and 100")
        if not isinstance(payload, dict):
            raise ValueError("payload must be an object")
        payload_json = canonical_json(payload)
        if len(payload_json.encode()) > MAX_PAYLOAD_BYTES:
            raise ValueError("payload exceeds the configured size limit")
        request_hash = hashlib.sha256(canonical_json({
            "workload_kind": workload_kind, "handler_id": handler_id,
            "handler_version": handler_version, "workload_ref": workload_ref,
            "workload_hash": workload_hash, "payload": payload,
            "max_attempts": max_attempts, "priority": priority,
        }).encode()).hexdigest()
        key_hash = hashlib.sha256(idempotency_key.encode()).hexdigest()
        now = _timestamp()
        correlation = correlation_id or str(uuid.uuid4())
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM execution_jobs WHERE tenant_id=? AND idempotency_key_hash=?",
                (tenant_id, key_hash),
            ).fetchone()
            if existing:
                if existing["request_hash"] != request_hash:
                    raise JobConflictError("idempotency key was already used for a different job request")
                return self._record(existing), False
            job_id = str(uuid.uuid4())
            connection.execute(
                """INSERT INTO execution_jobs
                (job_id, tenant_id, subject_id, principal_type, workload_kind, handler_id,
                 handler_version, workload_ref, workload_hash, request_hash,
                 idempotency_key_hash, payload_json, state, max_attempts, priority,
                 available_at, created_at, updated_at, correlation_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'queued', ?, ?, ?, ?, ?, ?)""",
                (job_id, tenant_id, subject_id, principal_type, workload_kind, handler_id,
                 handler_version, workload_ref, workload_hash.lower(), request_hash,
                 key_hash, payload_json, max_attempts, priority, now, now, now, correlation),
            )
            row = connection.execute("SELECT * FROM execution_jobs WHERE job_id=?", (job_id,)).fetchone()
            self._event(connection, row, subject_id, None, "queued", "job_admitted")
            return self._record(row), True

    def get(self, job_id: str, tenant_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM execution_jobs WHERE job_id=? AND tenant_id=?",
                (job_id, tenant_id),
            ).fetchone()
        if row is None:
            raise JobNotFoundError(job_id)
        return self._record(row)

    def list_events(self, job_id: str, tenant_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT * FROM execution_job_events
                WHERE job_id=? AND tenant_id=? ORDER BY created_at, event_id""",
                (job_id, tenant_id),
            ).fetchall()
        if not rows:
            self.get(job_id, tenant_id)
        return [{
            "event_id": row["event_id"], "job_id": row["job_id"],
            "tenant_id": row["tenant_id"], "actor_id": row["actor_id"],
            "from_state": row["from_state"], "to_state": row["to_state"],
            "reason_code": row["reason_code"], "attempt": row["attempt"],
            "lease_token_fingerprint": row["lease_token_fingerprint"],
            "correlation_id": row["correlation_id"], "created_at": row["created_at"],
        } for row in rows]

    def claim(self, worker_id: str, lease_seconds: int = 30) -> dict[str, Any] | None:
        if not worker_id or len(worker_id) > 128:
            raise ValueError("worker_id is required and must be at most 128 characters")
        if not 1 <= lease_seconds <= 3600:
            raise ValueError("lease_seconds must be between 1 and 3600")
        now = _now()
        now_text = _timestamp(now)
        expiry = _timestamp(now + timedelta(seconds=lease_seconds))
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """SELECT * FROM execution_jobs WHERE state='queued' AND available_at<=?
                AND attempt < max_attempts ORDER BY priority DESC, created_at, job_id LIMIT 1""",
                (now_text,),
            ).fetchone()
            if row is None:
                return None
            token = str(uuid.uuid4())
            connection.execute(
                """UPDATE execution_jobs SET state='leased', attempt=attempt+1,
                worker_id=?, lease_token=?, lease_expires_at=?, heartbeat_at=?,
                updated_at=? WHERE job_id=? AND state='queued'""",
                (worker_id, token, expiry, now_text, now_text, row["job_id"]),
            )
            updated = connection.execute(
                "SELECT * FROM execution_jobs WHERE job_id=?", (row["job_id"],)
            ).fetchone()
            self._event(connection, updated, worker_id, "queued", "leased", "worker_claimed", token)
            record = self._record(updated)
            record["lease_token"] = token
            record["lease_expires_at"] = expiry
            record["payload"] = json.loads(updated["payload_json"])
            return record

    def _leased_row(
        self, connection: sqlite3.Connection, job_id: str, tenant_id: str,
        worker_id: str, lease_token: str, states: tuple[str, ...],
    ) -> sqlite3.Row:
        row = connection.execute(
            "SELECT * FROM execution_jobs WHERE job_id=? AND tenant_id=?",
            (job_id, tenant_id),
        ).fetchone()
        if row is None:
            raise JobNotFoundError(job_id)
        if (row["worker_id"] != worker_id or row["lease_token"] != lease_token
                or row["state"] not in states or not row["lease_expires_at"]
                or row["lease_expires_at"] <= _timestamp()):
            raise JobLeaseError("worker lease is invalid or expired")
        return row

    def start(self, job_id: str, tenant_id: str, worker_id: str, lease_token: str) -> dict[str, Any]:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = self._leased_row(connection, job_id, tenant_id, worker_id, lease_token, ("leased",))
            now = _timestamp()
            connection.execute(
                """UPDATE execution_jobs SET state='running', started_at=COALESCE(started_at, ?),
                heartbeat_at=?, updated_at=? WHERE job_id=?""",
                (now, now, now, job_id),
            )
            updated = connection.execute("SELECT * FROM execution_jobs WHERE job_id=?", (job_id,)).fetchone()
            self._event(connection, updated, worker_id, row["state"], "running", "worker_started", lease_token)
            return self._record(updated)

    def heartbeat(
        self, job_id: str, tenant_id: str, worker_id: str, lease_token: str,
        lease_seconds: int = 30,
    ) -> str:
        if not 1 <= lease_seconds <= 3600:
            raise ValueError("lease_seconds must be between 1 and 3600")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = self._leased_row(
                connection, job_id, tenant_id, worker_id, lease_token, ("leased", "running", "cancel_requested")
            )
            now = _now()
            expiry = _timestamp(now + timedelta(seconds=lease_seconds))
            connection.execute(
                "UPDATE execution_jobs SET heartbeat_at=?, lease_expires_at=?, updated_at=? WHERE job_id=?",
                (_timestamp(now), expiry, _timestamp(now), job_id),
            )
            return expiry

    def complete(
        self, job_id: str, tenant_id: str, worker_id: str, lease_token: str,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        result_json = canonical_json(result)
        if len(result_json.encode()) > MAX_RESULT_BYTES:
            raise ValueError("result exceeds the configured size limit")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = self._leased_row(connection, job_id, tenant_id, worker_id, lease_token, ("running", "cancel_requested"))
            now = _timestamp()
            connection.execute(
                """UPDATE execution_jobs SET state='succeeded', result_json=?, completed_at=?,
                updated_at=?, lease_token=NULL, lease_expires_at=NULL WHERE job_id=?""",
                (result_json, now, now, job_id),
            )
            updated = connection.execute("SELECT * FROM execution_jobs WHERE job_id=?", (job_id,)).fetchone()
            self._event(connection, updated, worker_id, row["state"], "succeeded", "worker_completed", lease_token)
            return self._record(updated)

    def fail(
        self, job_id: str, tenant_id: str, worker_id: str, lease_token: str,
        error_code: str,
    ) -> dict[str, Any]:
        if not error_code or len(error_code) > 128:
            raise ValueError("error_code is required and must be at most 128 characters")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = self._leased_row(connection, job_id, tenant_id, worker_id, lease_token, ("running", "cancel_requested", "leased"))
            now = _timestamp()
            connection.execute(
                """UPDATE execution_jobs SET state='failed', error_code=?, completed_at=?,
                updated_at=?, lease_token=NULL, lease_expires_at=NULL WHERE job_id=?""",
                (error_code, now, now, job_id),
            )
            updated = connection.execute("SELECT * FROM execution_jobs WHERE job_id=?", (job_id,)).fetchone()
            self._event(connection, updated, worker_id, row["state"], "failed", error_code, lease_token)
            return self._record(updated)

    def request_cancel(self, job_id: str, tenant_id: str, actor_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM execution_jobs WHERE job_id=? AND tenant_id=?", (job_id, tenant_id)
            ).fetchone()
            if row is None:
                raise JobNotFoundError(job_id)
            if row["state"] in TERMINAL_STATES:
                return self._record(row)
            if row["state"] == "cancel_requested":
                return self._record(row)
            now = _timestamp()
            connection.execute(
                "UPDATE execution_jobs SET state='cancel_requested', cancel_requested_at=?, updated_at=? WHERE job_id=?",
                (now, now, job_id),
            )
            updated = connection.execute("SELECT * FROM execution_jobs WHERE job_id=?", (job_id,)).fetchone()
            self._event(connection, updated, actor_id, row["state"], "cancel_requested", "cancellation_requested")
            return self._record(updated)

    def confirm_cancel(
        self, job_id: str, tenant_id: str, actor_id: str,
        worker_id: str | None = None, lease_token: str | None = None,
    ) -> dict[str, Any]:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM execution_jobs WHERE job_id=? AND tenant_id=?", (job_id, tenant_id)
            ).fetchone()
            if row is None:
                raise JobNotFoundError(job_id)
            if row["state"] != "cancel_requested":
                raise JobConflictError("job has no pending cancellation request")
            if row["lease_token"] is not None and (
                worker_id != row["worker_id"] or lease_token != row["lease_token"]
            ):
                raise JobLeaseError("only the lease owner or trusted supervisor may confirm termination")
            now = _timestamp()
            connection.execute(
                """UPDATE execution_jobs SET state='cancelled', completed_at=?, updated_at=?,
                worker_id=NULL, lease_token=NULL, lease_expires_at=NULL WHERE job_id=?""",
                (now, now, job_id),
            )
            updated = connection.execute("SELECT * FROM execution_jobs WHERE job_id=?", (job_id,)).fetchone()
            self._event(connection, updated, actor_id, row["state"], "cancelled", "termination_confirmed", lease_token)
            return self._record(updated)

    def recover_expired_leases(self, supervisor_id: str = "recovery") -> dict[str, int]:
        now = _timestamp()
        counts = {"requeued_leased": 0, "failed_ambiguous_running": 0}
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            expired = connection.execute(
                """SELECT * FROM execution_jobs WHERE lease_expires_at<=?
                AND state IN ('leased','running') ORDER BY created_at""", (now,)
            ).fetchall()
            for row in expired:
                if row["state"] == "leased":
                    target = "queued"
                    reason = "expired_lease_before_start"
                    connection.execute(
                        """UPDATE execution_jobs SET state='queued', worker_id=NULL,
                        lease_token=NULL, lease_expires_at=NULL, heartbeat_at=NULL, updated_at=?
                        WHERE job_id=?""", (now, row["job_id"])
                    )
                    counts["requeued_leased"] += 1
                else:
                    target = "failed"
                    reason = "worker_lost_ambiguous_outcome"
                    connection.execute(
                        """UPDATE execution_jobs SET state='failed', error_code=?, completed_at=?,
                        updated_at=?, worker_id=NULL, lease_token=NULL, lease_expires_at=NULL
                        WHERE job_id=?""", (reason, now, now, row["job_id"])
                    )
                    counts["failed_ambiguous_running"] += 1
                updated = connection.execute(
                    "SELECT * FROM execution_jobs WHERE job_id=?", (row["job_id"],)
                ).fetchone()
                self._event(connection, updated, supervisor_id, row["state"], target, reason, row["lease_token"])
        return counts
