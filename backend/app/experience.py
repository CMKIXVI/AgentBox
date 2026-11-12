"""Tenant-scoped execution experience, proposed lessons and evidence-aware fitness selection.

Experience links are caller-asserted until a trusted runner can attest workload execution
and evaluation provenance. Raw prompts, inputs and outputs are never copied into this store.
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

HASH_PATTERN = re.compile(r"^[a-fA-F0-9]{64}$")
LESSON_SOURCES = {"deterministic_rule", "human_review", "model_proposal"}


class ExperienceError(Exception):
    """Base execution experience error."""


class ExperienceNotFoundError(ExperienceError):
    """A tenant-scoped execution experience does not exist."""


class ExperienceConflictError(ExperienceError):
    """An immutable experience or lesson identity conflicts with existing content."""


class ExperienceValidationError(ExperienceError):
    """An experience or lesson violates its contract."""


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _finite_number(value: Any, label: str, minimum: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ExperienceValidationError(f"{label} must be a number")
    number = float(value)
    if not math.isfinite(number) or number < minimum:
        raise ExperienceValidationError(f"{label} must be finite and at least {minimum}")
    return number


class ExecutionExperienceService:
    """Persist minimized, tenant-scoped links between execution and evaluation evidence."""

    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)
        self._memory = self.database_path == ":memory:"
        self._dsn = (
            f"file:agentbox-experience-{id(self)}?mode=memory&cache=shared"
            if self._memory else self.database_path
        )
        self._keeper = sqlite3.connect(self._dsn, uri=True, timeout=10) if self._memory else None
        if not self._memory:
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
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
                CREATE TABLE IF NOT EXISTS agent_experiences (
                    tenant_id TEXT NOT NULL,
                    experience_id TEXT NOT NULL,
                    execution_id TEXT NOT NULL,
                    evaluation_run_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    agent_version TEXT NOT NULL,
                    agent_content_hash TEXT NOT NULL,
                    profile_id TEXT NOT NULL,
                    profile_version TEXT NOT NULL,
                    profile_content_hash TEXT NOT NULL,
                    workload_ref TEXT NOT NULL,
                    workload_hash TEXT NOT NULL,
                    execution_status TEXT NOT NULL CHECK(execution_status = 'completed'),
                    evaluation_score REAL NOT NULL CHECK(evaluation_score >= 0 AND evaluation_score <= 1),
                    evaluation_passed INTEGER NOT NULL CHECK(evaluation_passed IN (0, 1)),
                    case_pass_rate REAL NOT NULL CHECK(case_pass_rate >= 0 AND case_pass_rate <= 1),
                    avg_latency_ms REAL NOT NULL CHECK(avg_latency_ms >= 0),
                    total_cost_usd REAL NOT NULL CHECK(total_cost_usd >= 0),
                    input_tokens INTEGER NOT NULL CHECK(input_tokens >= 0),
                    output_tokens INTEGER NOT NULL CHECK(output_tokens >= 0),
                    linkage_status TEXT NOT NULL CHECK(linkage_status = 'caller_asserted'),
                    evidence_status TEXT NOT NULL CHECK(evidence_status = 'unverified'),
                    record_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, experience_id),
                    UNIQUE (tenant_id, evaluation_run_id),
                    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id)
                )
            """)
            connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_agent_experiences_fitness
                ON agent_experiences(
                    tenant_id, profile_id, profile_version, agent_id, agent_version, created_at
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS learning_lessons (
                    tenant_id TEXT NOT NULL,
                    lesson_id TEXT NOT NULL,
                    experience_id TEXT NOT NULL,
                    lesson_type TEXT NOT NULL,
                    statement TEXT NOT NULL,
                    evidence_refs_json TEXT NOT NULL,
                    source_kind TEXT NOT NULL CHECK(source_kind IN (
                        'deterministic_rule', 'human_review', 'model_proposal'
                    )),
                    extractor_version TEXT NOT NULL,
                    confidence REAL NOT NULL CHECK(confidence >= 0 AND confidence <= 1),
                    status TEXT NOT NULL CHECK(status = 'proposed'),
                    statement_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, lesson_id),
                    UNIQUE (tenant_id, experience_id, statement_hash),
                    FOREIGN KEY (tenant_id, experience_id)
                        REFERENCES agent_experiences(tenant_id, experience_id)
                )
            """)
            connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_learning_lessons_experience
                ON learning_lessons(tenant_id, experience_id, created_at)
            """)

    @staticmethod
    def _experience_record(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "experience_id": row["experience_id"],
            "execution_id": row["execution_id"],
            "evaluation_run_id": row["evaluation_run_id"],
            "agent_id": row["agent_id"],
            "agent_version": row["agent_version"],
            "agent_content_hash": row["agent_content_hash"],
            "profile_id": row["profile_id"],
            "profile_version": row["profile_version"],
            "profile_content_hash": row["profile_content_hash"],
            "workload_ref": row["workload_ref"],
            "workload_hash": row["workload_hash"],
            "execution_status": row["execution_status"],
            "evaluation": {
                "score": row["evaluation_score"],
                "passed": bool(row["evaluation_passed"]),
                "case_pass_rate": row["case_pass_rate"],
                "avg_latency_ms": row["avg_latency_ms"],
                "total_cost_usd": row["total_cost_usd"],
            },
            "usage": {
                "input_tokens": row["input_tokens"],
                "output_tokens": row["output_tokens"],
            },
            "linkage_status": row["linkage_status"],
            "evidence_status": row["evidence_status"],
            "record_hash": row["record_hash"],
            "created_at": row["created_at"],
            "created_by": row["created_by"],
        }

    def record(
        self,
        execution_id: str,
        evaluation_run_id: str,
        workload_ref: str,
        workload_hash: str,
        tenant_id: str,
        actor_id: str,
    ) -> tuple[dict[str, Any], bool]:
        if not isinstance(execution_id, str) or not execution_id.strip() or len(execution_id) > 128:
            raise ExperienceValidationError("execution_id must contain 1 to 128 characters")
        if not isinstance(evaluation_run_id, str) or not evaluation_run_id.strip() or len(evaluation_run_id) > 128:
            raise ExperienceValidationError("evaluation_run_id must contain 1 to 128 characters")
        if not isinstance(workload_ref, str) or not workload_ref.strip() or len(workload_ref) > 512:
            raise ExperienceValidationError("workload_ref must contain 1 to 512 characters")
        if not isinstance(workload_hash, str) or not HASH_PATTERN.fullmatch(workload_hash):
            raise ExperienceValidationError("workload_hash must be a SHA-256 hex digest")
        if not isinstance(actor_id, str) or not actor_id.strip() or len(actor_id) > 256:
            raise ExperienceValidationError("actor_id must contain 1 to 256 characters")

        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            execution = connection.execute(
                "SELECT * FROM executions WHERE tenant_id = ? AND execution_id = ?",
                (tenant_id, execution_id),
            ).fetchone()
            evaluation = connection.execute(
                "SELECT * FROM evaluation_runs WHERE tenant_id = ? AND run_id = ?",
                (tenant_id, evaluation_run_id),
            ).fetchone()
            if execution is None or evaluation is None:
                raise ExperienceNotFoundError("Execution or evaluation run was not found for this tenant")
            if execution["status"] != "completed":
                raise ExperienceValidationError("Only completed executions can produce fitness experience")
            if evaluation["status"] != "completed":
                raise ExperienceValidationError("Only completed evaluation runs can produce fitness experience")
            if (
                execution["agent_id"] != evaluation["agent_id"]
                or execution["agent_version"] != evaluation["agent_version"]
            ):
                raise ExperienceValidationError("Execution and evaluation must reference the same agent version")

            agent = connection.execute(
                """SELECT content_hash FROM agent_versions
                WHERE tenant_id = ? AND agent_id = ? AND version = ?""",
                (tenant_id, execution["agent_id"], execution["agent_version"]),
            ).fetchone()
            profile = connection.execute(
                """SELECT content_hash FROM evaluation_profiles
                WHERE tenant_id = ? AND profile_id = ? AND version = ?""",
                (tenant_id, evaluation["profile_id"], evaluation["profile_version"]),
            ).fetchone()
            if agent is None or profile is None:
                raise ExperienceValidationError("Referenced agent or evaluation profile version is missing")

            result = json.loads(evaluation["result_json"])
            usage = json.loads(execution["result_json"] or "{}").get("usage", {})
            score = _finite_number(result.get("score"), "evaluation score")
            pass_rate = _finite_number(result.get("case_pass_rate"), "case pass rate")
            latency = _finite_number(result.get("avg_latency_ms"), "average latency")
            cost = _finite_number(result.get("total_cost_usd"), "total cost")
            input_tokens = int(usage.get("input_tokens", 0))
            output_tokens = int(usage.get("output_tokens", 0))
            if score > 1 or pass_rate > 1 or input_tokens < 0 or output_tokens < 0:
                raise ExperienceValidationError("Evaluation or usage metrics are outside supported bounds")

            existing = connection.execute(
                """SELECT * FROM agent_experiences
                WHERE tenant_id = ? AND evaluation_run_id = ?""",
                (tenant_id, evaluation_run_id),
            ).fetchone()
            candidate = {
                "tenant_id": tenant_id,
                "execution_id": execution_id,
                "evaluation_run_id": evaluation_run_id,
                "agent_id": execution["agent_id"],
                "agent_version": execution["agent_version"],
                "agent_content_hash": agent["content_hash"],
                "profile_id": evaluation["profile_id"],
                "profile_version": evaluation["profile_version"],
                "profile_content_hash": profile["content_hash"],
                "workload_ref": workload_ref,
                "workload_hash": workload_hash.lower(),
                "execution_status": "completed",
                "evaluation_score": score,
                "evaluation_passed": int(bool(evaluation["passed"])),
                "case_pass_rate": pass_rate,
                "avg_latency_ms": latency,
                "total_cost_usd": cost,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "linkage_status": "caller_asserted",
                "evidence_status": "unverified",
            }
            digest = _hash(candidate)
            if existing is not None:
                if existing["record_hash"] != digest:
                    raise ExperienceConflictError("Evaluation run already has a different immutable experience record")
                return self._experience_record(existing), False

            experience_id = str(uuid.uuid4())
            created_at = _now()
            connection.execute(
                """INSERT INTO agent_experiences (
                    tenant_id, experience_id, execution_id, evaluation_run_id, agent_id,
                    agent_version, agent_content_hash, profile_id, profile_version,
                    profile_content_hash, workload_ref, workload_hash, execution_status,
                    evaluation_score, evaluation_passed, case_pass_rate, avg_latency_ms,
                    total_cost_usd, input_tokens, output_tokens, linkage_status, evidence_status,
                    record_hash, created_at, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    tenant_id, experience_id, execution_id, evaluation_run_id,
                    candidate["agent_id"], candidate["agent_version"], candidate["agent_content_hash"],
                    candidate["profile_id"], candidate["profile_version"], candidate["profile_content_hash"],
                    candidate["workload_ref"], candidate["workload_hash"], candidate["execution_status"],
                    candidate["evaluation_score"], candidate["evaluation_passed"], candidate["case_pass_rate"],
                    candidate["avg_latency_ms"], candidate["total_cost_usd"], candidate["input_tokens"],
                    candidate["output_tokens"], candidate["linkage_status"], candidate["evidence_status"],
                    digest, created_at, actor_id,
                ),
            )
            row = connection.execute(
                "SELECT * FROM agent_experiences WHERE tenant_id = ? AND experience_id = ?",
                (tenant_id, experience_id),
            ).fetchone()
        return self._experience_record(row), True

    def get(self, experience_id: str, tenant_id: str) -> dict[str, Any]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM agent_experiences WHERE tenant_id = ? AND experience_id = ?",
                (tenant_id, experience_id),
            ).fetchone()
        if row is None:
            raise ExperienceNotFoundError(experience_id)
        return self._experience_record(row)

    def list_for_agent(
        self, agent_id: str, tenant_id: str, profile_id: str | None = None,
        profile_version: str | None = None, limit: int = 50, offset: int = 0,
    ) -> list[dict[str, Any]]:
        if (profile_id is None) != (profile_version is None):
            raise ExperienceValidationError("profile_id and profile_version must be supplied together")
        if not 1 <= limit <= 100 or offset < 0:
            raise ExperienceValidationError("Invalid experience pagination")
        query = "SELECT * FROM agent_experiences WHERE tenant_id = ? AND agent_id = ?"
        values: list[Any] = [tenant_id, agent_id]
        if profile_id is not None:
            query += " AND profile_id = ? AND profile_version = ?"
            values.extend([profile_id, profile_version])
        query += " ORDER BY created_at DESC, experience_id LIMIT ? OFFSET ?"
        values.extend([limit, offset])
        with self._connection() as connection:
            rows = connection.execute(query, values).fetchall()
        return [self._experience_record(row) for row in rows]

    def create_lesson(
        self, experience_id: str, lesson_type: str, statement: str,
        evidence_refs: list[str], source_kind: str, extractor_version: str,
        confidence: float, tenant_id: str, actor_id: str,
    ) -> tuple[dict[str, Any], bool]:
        if not isinstance(lesson_type, str) or not re.fullmatch(r"[a-z][a-z0-9._-]{1,63}", lesson_type):
            raise ExperienceValidationError("lesson_type must be a normalized identifier")
        if not isinstance(statement, str) or not statement.strip() or len(statement) > 2000:
            raise ExperienceValidationError("statement must contain 1 to 2000 characters")
        if not isinstance(evidence_refs, list) or not 1 <= len(evidence_refs) <= 20:
            raise ExperienceValidationError("evidence_refs must contain 1 to 20 references")
        if any(not isinstance(item, str) or not item.strip() or len(item) > 512 for item in evidence_refs):
            raise ExperienceValidationError("evidence_refs contain an invalid reference")
        if source_kind not in LESSON_SOURCES:
            raise ExperienceValidationError("Unsupported lesson source_kind")
        if not isinstance(extractor_version, str) or not extractor_version.strip() or len(extractor_version) > 128:
            raise ExperienceValidationError("extractor_version must contain 1 to 128 characters")
        confidence = _finite_number(confidence, "confidence")
        if confidence > 1:
            raise ExperienceValidationError("confidence must not exceed 1")
        if not isinstance(actor_id, str) or not actor_id.strip() or len(actor_id) > 256:
            raise ExperienceValidationError("actor_id must contain 1 to 256 characters")

        normalized_statement = statement.strip()
        statement_hash = _hash({
            "lesson_type": lesson_type,
            "statement": normalized_statement,
            "evidence_refs": sorted(set(evidence_refs)),
            "source_kind": source_kind,
            "extractor_version": extractor_version,
            "confidence": confidence,
        })
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            experience = connection.execute(
                "SELECT experience_id FROM agent_experiences WHERE tenant_id = ? AND experience_id = ?",
                (tenant_id, experience_id),
            ).fetchone()
            if experience is None:
                raise ExperienceNotFoundError(experience_id)
            existing = connection.execute(
                """SELECT * FROM learning_lessons
                WHERE tenant_id = ? AND experience_id = ? AND statement_hash = ?""",
                (tenant_id, experience_id, statement_hash),
            ).fetchone()
            if existing is not None:
                return self._lesson_record(existing), False
            lesson_id = str(uuid.uuid4())
            created_at = _now()
            connection.execute(
                """INSERT INTO learning_lessons (
                    tenant_id, lesson_id, experience_id, lesson_type, statement,
                    evidence_refs_json, source_kind, extractor_version, confidence,
                    status, statement_hash, created_at, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'proposed', ?, ?, ?)""",
                (
                    tenant_id, lesson_id, experience_id, lesson_type, normalized_statement,
                    _canonical(sorted(set(evidence_refs))), source_kind, extractor_version,
                    confidence, statement_hash, created_at, actor_id,
                ),
            )
            row = connection.execute(
                "SELECT * FROM learning_lessons WHERE tenant_id = ? AND lesson_id = ?",
                (tenant_id, lesson_id),
            ).fetchone()
        return self._lesson_record(row), True

    @staticmethod
    def _lesson_record(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "lesson_id": row["lesson_id"],
            "experience_id": row["experience_id"],
            "lesson_type": row["lesson_type"],
            "statement": row["statement"],
            "evidence_refs": json.loads(row["evidence_refs_json"]),
            "source_kind": row["source_kind"],
            "extractor_version": row["extractor_version"],
            "confidence": row["confidence"],
            "status": row["status"],
            "created_at": row["created_at"],
            "created_by": row["created_by"],
        }

    def list_lessons(self, experience_id: str, tenant_id: str, limit: int = 50) -> list[dict[str, Any]]:
        if not 1 <= limit <= 100:
            raise ExperienceValidationError("limit must be between 1 and 100")
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT * FROM learning_lessons
                WHERE tenant_id = ? AND experience_id = ?
                ORDER BY created_at DESC, lesson_id LIMIT ?""",
                (tenant_id, experience_id, limit),
            ).fetchall()
        return [self._lesson_record(row) for row in rows]

    def select_fitness(
        self, profile_id: str, profile_version: str, tenant_id: str,
        min_samples: int = 3, limit: int = 50,
    ) -> list[dict[str, Any]]:
        if not 1 <= min_samples <= 1000 or not 1 <= limit <= 100:
            raise ExperienceValidationError("min_samples must be 1..1000 and limit must be 1..100")
        with self._connection() as connection:
            profile = connection.execute(
                """SELECT content_hash FROM evaluation_profiles
                WHERE tenant_id = ? AND profile_id = ? AND version = ?""",
                (tenant_id, profile_id, profile_version),
            ).fetchone()
            if profile is None:
                raise ExperienceNotFoundError(f"{profile_id}@{profile_version}")
            rows = connection.execute(
                """SELECT agent_id, agent_version, agent_content_hash,
                    COUNT(*) AS sample_count, AVG(evaluation_score) AS mean_score,
                    AVG(evaluation_passed) AS pass_rate,
                    AVG(case_pass_rate) AS mean_case_pass_rate,
                    AVG(avg_latency_ms) AS mean_latency_ms,
                    AVG(total_cost_usd) AS mean_cost_usd,
                    MAX(created_at) AS last_observed_at
                FROM agent_experiences
                WHERE tenant_id = ? AND profile_id = ? AND profile_version = ?
                    AND profile_content_hash = ?
                GROUP BY agent_id, agent_version, agent_content_hash
                HAVING COUNT(*) >= ?
                ORDER BY mean_score ASC, sample_count DESC, last_observed_at DESC
                LIMIT ?""",
                (tenant_id, profile_id, profile_version, profile["content_hash"], min_samples, limit),
            ).fetchall()
        items = []
        for row in rows:
            count = int(row["sample_count"])
            mean_score = float(row["mean_score"])
            confidence = count / (count + 3.0)
            items.append({
                "agent_id": row["agent_id"],
                "agent_version": row["agent_version"],
                "agent_content_hash": row["agent_content_hash"],
                "profile_id": profile_id,
                "profile_version": profile_version,
                "sample_count": count,
                "mean_score": round(mean_score, 6),
                "pass_rate": round(float(row["pass_rate"]), 6),
                "mean_case_pass_rate": round(float(row["mean_case_pass_rate"]), 6),
                "mean_latency_ms": round(float(row["mean_latency_ms"]), 3),
                "mean_cost_usd": round(float(row["mean_cost_usd"]), 8),
                "last_observed_at": row["last_observed_at"],
                "sample_confidence": round(confidence, 6),
                "improvement_priority": round((1.0 - mean_score) * confidence, 6),
            })
        return items
