"""Immutable, tenant-scoped parent/candidate experiment comparisons.

Evaluation runs currently contain caller-submitted outputs. Comparisons therefore
record asserted workload identity and remain unverified/advisory; they cannot gate
or authorize promotion.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_HASH = re.compile(r"^[a-fA-F0-9]{64}$")


class ExperimentComparisonError(Exception):
    """Base comparison error."""


class ExperimentComparisonNotFoundError(ExperimentComparisonError):
    """A tenant-scoped comparison or dependency was not found."""


class ExperimentComparisonConflictError(ExperimentComparisonError):
    """An immutable comparison identity conflicts with existing content."""


class ExperimentComparisonValidationError(ExperimentComparisonError):
    """Comparison inputs or linked records are incompatible."""


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ExperimentComparisonValidationError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ExperimentComparisonValidationError(f"{name} must be finite and non-negative")
    return result


class ExperimentComparisonService:
    """Compare immutable parent/candidate evaluation records under one asserted workload."""

    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)
        self._closed = False
        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self._memory = self.database_path == ":memory:"
        self._dsn = (
            f"file:agentbox-experiment-comparison-{id(self)}?mode=memory&cache=shared"
            if self._memory else self.database_path
        )
        self._keeper = sqlite3.connect(self._dsn, uri=True, timeout=10) if self._memory else None
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
            raise RuntimeError("Experiment comparison store is closed")
        connection = sqlite3.connect(self._dsn, uri=self._memory, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            if not self._memory:
                connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("""
                CREATE TABLE IF NOT EXISTS agent_experiment_comparisons (
                    tenant_id TEXT NOT NULL,
                    comparison_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    parent_version TEXT NOT NULL,
                    candidate_version TEXT NOT NULL,
                    parent_content_hash TEXT NOT NULL,
                    candidate_content_hash TEXT NOT NULL,
                    parent_evaluation_run_id TEXT NOT NULL,
                    candidate_evaluation_run_id TEXT NOT NULL,
                    profile_id TEXT NOT NULL,
                    profile_version TEXT NOT NULL,
                    workload_ref TEXT NOT NULL,
                    workload_hash TEXT NOT NULL,
                    comparison_result_json TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    evidence_status TEXT NOT NULL CHECK(evidence_status = 'unverified'),
                    created_at TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, comparison_id),
                    UNIQUE (tenant_id, parent_evaluation_run_id, candidate_evaluation_run_id),
                    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id)
                )
            """)
            connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_agent_experiment_comparisons_agent
                ON agent_experiment_comparisons(tenant_id, agent_id, created_at)
            """)
            connection.execute("""
                CREATE TRIGGER IF NOT EXISTS agent_experiment_comparisons_no_update
                BEFORE UPDATE ON agent_experiment_comparisons
                BEGIN
                    SELECT RAISE(ABORT, 'experiment comparison records are append-only');
                END
            """)
            connection.execute("""
                CREATE TRIGGER IF NOT EXISTS agent_experiment_comparisons_no_delete
                BEFORE DELETE ON agent_experiment_comparisons
                BEGIN
                    SELECT RAISE(ABORT, 'experiment comparison records are append-only');
                END
            """)

    @staticmethod
    def _record(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "comparison_id": row["comparison_id"],
            "agent_id": row["agent_id"],
            "parent_version": row["parent_version"],
            "candidate_version": row["candidate_version"],
            "parent_content_hash": row["parent_content_hash"],
            "candidate_content_hash": row["candidate_content_hash"],
            "parent_evaluation_run_id": row["parent_evaluation_run_id"],
            "candidate_evaluation_run_id": row["candidate_evaluation_run_id"],
            "profile_id": row["profile_id"],
            "profile_version": row["profile_version"],
            "workload_ref": row["workload_ref"],
            "workload_hash": row["workload_hash"],
            "evidence_status": row["evidence_status"],
            "comparison": json.loads(row["comparison_result_json"]),
            "request_hash": row["request_hash"],
            "created_at": row["created_at"],
            "created_by": row["created_by"],
            "promotion_eligible": False,
            "decision_authority": "advisory_only",
        }

    def compare(
        self,
        *,
        agent_id: str,
        parent_version: str,
        candidate_version: str,
        parent_evaluation_run_id: str,
        candidate_evaluation_run_id: str,
        workload_ref: str,
        workload_hash: str,
        tenant_id: str,
        actor_id: str,
    ) -> tuple[dict[str, Any], bool]:
        values = {
            "agent_id": agent_id, "parent_version": parent_version,
            "candidate_version": candidate_version,
            "parent_evaluation_run_id": parent_evaluation_run_id,
            "candidate_evaluation_run_id": candidate_evaluation_run_id,
            "workload_ref": workload_ref, "workload_hash": workload_hash.lower()
            if isinstance(workload_hash, str) else workload_hash,
        }
        for name in ("agent_id", "parent_version", "candidate_version",
                     "parent_evaluation_run_id", "candidate_evaluation_run_id", "workload_ref"):
            value = values[name]
            if not isinstance(value, str) or not value.strip() or len(value) > 512:
                raise ExperimentComparisonValidationError(f"{name} must contain 1 to 512 characters")
        if parent_version == candidate_version:
            raise ExperimentComparisonValidationError("Parent and candidate versions must differ")
        if parent_evaluation_run_id == candidate_evaluation_run_id:
            raise ExperimentComparisonValidationError("Parent and candidate evaluation run IDs must differ")
        if not isinstance(workload_hash, str) or not _HASH.fullmatch(workload_hash):
            raise ExperimentComparisonValidationError("workload_hash must be a SHA-256 hex digest")
        if not isinstance(tenant_id, str) or not tenant_id.strip() or not isinstance(actor_id, str) or not actor_id.strip():
            raise ExperimentComparisonValidationError("Tenant and actor identity are required")

        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            parent = connection.execute(
                "SELECT * FROM agent_versions WHERE tenant_id = ? AND agent_id = ? AND version = ?",
                (tenant_id, agent_id, parent_version),
            ).fetchone()
            candidate = connection.execute(
                "SELECT * FROM agent_versions WHERE tenant_id = ? AND agent_id = ? AND version = ?",
                (tenant_id, agent_id, candidate_version),
            ).fetchone()
            if parent is None or candidate is None:
                raise ExperimentComparisonNotFoundError("Parent or candidate agent version was not found")
            expected_parent_ref = f"{agent_id}@{parent_version}"
            if candidate["parent_artifact_id"] != expected_parent_ref:
                raise ExperimentComparisonValidationError(
                    "Candidate immutable lineage does not reference the supplied parent version"
                )

            run_rows = {}
            for role, run_id, version in (
                ("parent", parent_evaluation_run_id, parent_version),
                ("candidate", candidate_evaluation_run_id, candidate_version),
            ):
                row = connection.execute(
                    "SELECT * FROM evaluation_runs WHERE tenant_id = ? AND run_id = ?",
                    (tenant_id, run_id),
                ).fetchone()
                if row is None:
                    raise ExperimentComparisonNotFoundError(f"{role.title()} evaluation run was not found")
                if row["status"] != "completed" or row["agent_id"] != agent_id or row["agent_version"] != version:
                    raise ExperimentComparisonValidationError(
                        f"{role.title()} evaluation run must be completed and reference the requested agent version"
                    )
                run_rows[role] = json.loads(row["result_json"])

            parent_run, candidate_run = run_rows["parent"], run_rows["candidate"]
            profile_identity = (parent_run.get("profile_id"), parent_run.get("profile_version"))
            if profile_identity != (candidate_run.get("profile_id"), candidate_run.get("profile_version")):
                raise ExperimentComparisonValidationError(
                    "Parent and candidate evaluations must use the exact same profile ID and version"
                )
            profile = connection.execute(
                "SELECT content_hash FROM evaluation_profiles WHERE tenant_id = ? AND profile_id = ? AND version = ?",
                (tenant_id, profile_identity[0], profile_identity[1]),
            ).fetchone()
            if profile is None:
                raise ExperimentComparisonNotFoundError("Pinned evaluation profile version was not found")

            parent_score = _number(parent_run.get("score"), "parent score")
            candidate_score = _number(candidate_run.get("score"), "candidate score")
            parent_latency = _number(parent_run.get("avg_latency_ms"), "parent average latency")
            candidate_latency = _number(candidate_run.get("avg_latency_ms"), "candidate average latency")
            parent_cost = _number(parent_run.get("total_cost_usd"), "parent total cost")
            candidate_cost = _number(candidate_run.get("total_cost_usd"), "candidate total cost")
            if parent_score > 1 or candidate_score > 1:
                raise ExperimentComparisonValidationError("Evaluation scores must be between 0 and 1")

            score_delta = round(candidate_score - parent_score, 6)
            comparison = {
                "score": {"parent": parent_score, "candidate": candidate_score, "delta": score_delta},
                "passed": {
                    "parent": bool(parent_run.get("passed")),
                    "candidate": bool(candidate_run.get("passed")),
                },
                "avg_latency_ms": {
                    "parent": parent_latency, "candidate": candidate_latency,
                    "delta": round(candidate_latency - parent_latency, 3),
                },
                "total_cost_usd": {
                    "parent": parent_cost, "candidate": candidate_cost,
                    "delta": round(candidate_cost - parent_cost, 8),
                },
                "profile_content_hash": profile["content_hash"],
                "asserted_same_workload": True,
                "workload_provenance": "caller_asserted",
                "outcome": "candidate_score_higher" if score_delta > 0 else (
                    "candidate_score_lower" if score_delta < 0 else "score_equal"
                ),
                "note": "Advisory comparison only; evaluation outputs and workload identity are not independently attested.",
            }
            request_identity = {
                **values, "tenant_id": tenant_id,
                "parent_content_hash": parent["content_hash"],
                "candidate_content_hash": candidate["content_hash"],
                "profile_content_hash": profile["content_hash"],
                "parent_run": parent_run, "candidate_run": candidate_run,
            }
            request_hash = _digest(request_identity)
            existing = connection.execute(
                """SELECT * FROM agent_experiment_comparisons
                WHERE tenant_id = ? AND parent_evaluation_run_id = ? AND candidate_evaluation_run_id = ?""",
                (tenant_id, parent_evaluation_run_id, candidate_evaluation_run_id),
            ).fetchone()
            if existing is not None:
                if existing["request_hash"] != request_hash:
                    raise ExperimentComparisonConflictError(
                        "This immutable evaluation pair already has a different comparison record"
                    )
                return self._record(existing), False

            comparison_id = str(uuid.uuid4())
            created_at = datetime.now(UTC).isoformat()
            connection.execute(
                """INSERT INTO agent_experiment_comparisons (
                    tenant_id, comparison_id, agent_id, parent_version, candidate_version,
                    parent_content_hash, candidate_content_hash, parent_evaluation_run_id,
                    candidate_evaluation_run_id, profile_id, profile_version, workload_ref,
                    workload_hash, comparison_result_json, request_hash, evidence_status,
                    created_at, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'unverified', ?, ?)""",
                (
                    tenant_id, comparison_id, agent_id, parent_version, candidate_version,
                    parent["content_hash"], candidate["content_hash"], parent_evaluation_run_id,
                    candidate_evaluation_run_id, profile_identity[0], profile_identity[1],
                    workload_ref, workload_hash.lower(), _canonical(comparison), request_hash,
                    created_at, actor_id,
                ),
            )
            row = connection.execute(
                "SELECT * FROM agent_experiment_comparisons WHERE tenant_id = ? AND comparison_id = ?",
                (tenant_id, comparison_id),
            ).fetchone()
        return self._record(row), True

    def get(self, comparison_id: str, tenant_id: str) -> dict[str, Any]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM agent_experiment_comparisons WHERE tenant_id = ? AND comparison_id = ?",
                (tenant_id, comparison_id),
            ).fetchone()
        if row is None:
            raise ExperimentComparisonNotFoundError(comparison_id)
        return self._record(row)
