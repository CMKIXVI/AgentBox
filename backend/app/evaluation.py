"""Versioned evaluation profiles and deterministic evaluation of submitted agent outputs.

This module deliberately does not execute agents. A future trusted runner will supply
per-case outputs and measurements; this layer validates and scores those results.
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

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

LEGACY_TENANT_ID = "__legacy_unassigned__"


class EvaluationProfileConflictError(Exception):
    """An immutable evaluation profile version already exists with other content."""


class EvaluationProfileNotFoundError(Exception):
    """The requested evaluation profile version does not exist."""


class EvaluationRunNotFoundError(Exception):
    """The requested evaluation run does not exist."""


def canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(value: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class EvaluationService:
    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)
        self._use_uri = self.database_path == ":memory:"
        self._dsn = (
            f"file:agentbox-evaluation-{id(self)}?mode=memory&cache=shared"
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
            if not self._use_uri:
                connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS evaluation_profiles (
                    profile_id TEXT NOT NULL,
                    version TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    profile_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (profile_id, version)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS evaluation_runs (
                    run_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    agent_version TEXT NOT NULL,
                    profile_id TEXT NOT NULL,
                    profile_version TEXT NOT NULL,
                    status TEXT NOT NULL,
                    score REAL NOT NULL,
                    passed INTEGER NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (profile_id, profile_version)
                        REFERENCES evaluation_profiles(profile_id, version)
                )
                """
            )
            for table in ("evaluation_profiles", "evaluation_runs"):
                columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
                if "tenant_id" not in columns:
                    connection.execute(
                        f"ALTER TABLE {table} ADD COLUMN tenant_id TEXT NOT NULL "
                        "DEFAULT '__legacy_unassigned__'"
                    )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_eval_profiles_tenant "
                "ON evaluation_profiles(tenant_id, profile_id, created_at)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_eval_runs_tenant_agent "
                "ON evaluation_runs(tenant_id, agent_id, agent_version, created_at)"
            )

    def create_profile(
        self, profile: dict[str, Any], tenant_id: str = LEGACY_TENANT_ID
    ) -> tuple[dict[str, Any], bool]:
        profile_id = profile["profile_id"]
        version = profile["version"]
        digest = sha256_json(profile)
        serialized = canonical_json(profile)
        created_at = utc_now()
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM evaluation_profiles WHERE tenant_id = ? AND profile_id = ? AND version = ?",
                (tenant_id, profile_id, version),
            ).fetchone()
            if existing:
                if existing["content_hash"] != digest:
                    raise EvaluationProfileConflictError(
                        f"{profile_id}@{version} is immutable and already exists"
                    )
                return self._profile_record(existing), False
            connection.execute(
                """
                INSERT INTO evaluation_profiles
                    (profile_id, version, content_hash, profile_json, created_at, tenant_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (profile_id, version, digest, serialized, created_at, tenant_id),
            )
            row = connection.execute(
                "SELECT * FROM evaluation_profiles WHERE tenant_id = ? AND profile_id = ? AND version = ?",
                (tenant_id, profile_id, version),
            ).fetchone()
        return self._profile_record(row), True

    @staticmethod
    def _profile_record(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "profile_id": row["profile_id"],
            "version": row["version"],
            "content_hash": row["content_hash"],
            "profile": json.loads(row["profile_json"]),
            "created_at": row["created_at"],
        }

    def get_profile(
        self, profile_id: str, version: str, tenant_id: str = LEGACY_TENANT_ID
    ) -> dict[str, Any]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM evaluation_profiles WHERE tenant_id = ? AND profile_id = ? AND version = ?",
                (tenant_id, profile_id, version),
            ).fetchone()
        if row is None:
            raise EvaluationProfileNotFoundError(f"{profile_id}@{version} was not found")
        return self._profile_record(row)

    def list_profile_versions(
        self, profile_id: str, tenant_id: str = LEGACY_TENANT_ID
    ) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM evaluation_profiles WHERE tenant_id = ? AND profile_id = ? "
                "ORDER BY created_at DESC, version DESC",
                (tenant_id, profile_id),
            ).fetchall()
        return [self._profile_record(row) for row in rows]

    @staticmethod
    def _contains_text(value: Any, expected: str) -> bool:
        if isinstance(value, str):
            return expected in value
        if isinstance(value, dict):
            return any(
                EvaluationService._contains_text(item, expected)
                for item in value.values()
            )
        if isinstance(value, list):
            return any(
                EvaluationService._contains_text(item, expected)
                for item in value
            )
        return False

    @staticmethod
    def _assertion_result(assertion: dict[str, Any], actual: Any) -> dict[str, Any]:
        assertion_type = assertion["type"]
        passed = False
        if assertion_type == "exact_match":
            passed = actual == assertion["expected_value"]
        elif assertion_type == "contains":
            passed = EvaluationService._contains_text(actual, assertion["expected_value"])
        elif assertion_type == "required_fields":
            passed = isinstance(actual, dict) and all(
                field in actual for field in assertion["fields"]
            )
        elif assertion_type == "json_schema_valid":
            try:
                schema = assertion["schema"]
                Draft202012Validator.check_schema(schema)
                Draft202012Validator(schema).validate(actual)
                passed = True
            except (SchemaError, ValidationError, TypeError):
                passed = False
        return {"type": assertion_type, "passed": passed}

    @classmethod
    def score(
        cls,
        profile: dict[str, Any],
        submitted_results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        cases = profile["cases"]
        result_by_id: dict[str, dict[str, Any]] = {}
        for result in submitted_results:
            case_id = result["case_id"]
            if case_id in result_by_id:
                raise ValueError(f"Duplicate result for case_id: {case_id}")
            result_by_id[case_id] = result

        expected_ids = {case["case_id"] for case in cases}
        unexpected_ids = sorted(set(result_by_id) - expected_ids)
        if unexpected_ids:
            raise ValueError(f"Unknown case_id values: {', '.join(unexpected_ids)}")

        case_results = []
        latency_values = []
        total_cost = 0.0
        for case in cases:
            submitted = result_by_id.get(case["case_id"])
            if submitted is None:
                case_results.append({
                    "case_id": case["case_id"],
                    "passed": False,
                    "reason": "No output was submitted for this case",
                    "assertions": [],
                })
                continue

            latency = float(submitted["latency_ms"])
            cost = float(submitted["cost_usd"])
            latency_values.append(latency)
            total_cost += cost
            assertions = [
                cls._assertion_result(assertion, submitted.get("output"))
                for assertion in case["assertions"]
            ]
            passed = all(item["passed"] for item in assertions)
            case_results.append({
                "case_id": case["case_id"],
                "passed": passed,
                "assertions": assertions,
                "latency_ms": latency,
                "cost_usd": cost,
            })

        case_pass_rate = (
            sum(1 for item in case_results if item["passed"]) / len(cases)
        )
        avg_latency = sum(latency_values) / len(latency_values) if latency_values else 0.0
        gates = profile["gates"]
        scoring = profile["scoring"]
        latency_score = (
            max(0.0, 1.0 - avg_latency / gates["max_avg_latency_ms"])
            if latency_values else 0.0
        )
        cost_score = (
            max(0.0, 1.0 - total_cost / gates["max_total_cost_usd"])
            if gates["max_total_cost_usd"] > 0
            else (1.0 if total_cost == 0 else 0.0)
        )
        score = (
            case_pass_rate * scoring["correctness_weight"]
            + latency_score * scoring["latency_weight"]
            + cost_score * scoring["cost_weight"]
        )
        gate_results = {
            "case_pass_rate": {
                "passed": case_pass_rate >= gates["min_case_pass_rate"],
                "actual": case_pass_rate,
                "required": gates["min_case_pass_rate"],
            },
            "avg_latency_ms": {
                "passed": avg_latency <= gates["max_avg_latency_ms"],
                "actual": avg_latency,
                "maximum": gates["max_avg_latency_ms"],
            },
            "total_cost_usd": {
                "passed": total_cost <= gates["max_total_cost_usd"],
                "actual": total_cost,
                "maximum": gates["max_total_cost_usd"],
            },
        }
        passed = all(item["passed"] for item in gate_results.values())
        return {
            "score": round(score, 6),
            "passed": passed,
            "case_pass_rate": round(case_pass_rate, 6),
            "avg_latency_ms": round(avg_latency, 3),
            "total_cost_usd": round(total_cost, 8),
            "latency_score": round(latency_score, 6),
            "cost_score": round(cost_score, 6),
            "gate_results": gate_results,
            "case_results": case_results,
        }

    def create_run(
        self,
        agent_id: str,
        agent_version: str,
        profile_id: str,
        profile_version: str,
        submitted_results: list[dict[str, Any]],
        tenant_id: str = LEGACY_TENANT_ID,
    ) -> dict[str, Any]:
        profile_record = self.get_profile(profile_id, profile_version, tenant_id)
        evaluation = self.score(profile_record["profile"], submitted_results)
        run_id = str(uuid.uuid4())
        created_at = utc_now()
        payload = {
            "run_id": run_id,
            "agent_id": agent_id,
            "agent_version": agent_version,
            "profile_id": profile_id,
            "profile_version": profile_version,
            "status": "completed",
            "created_at": created_at,
            **evaluation,
        }
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO evaluation_runs
                    (run_id, agent_id, agent_version, profile_id, profile_version,
                     status, score, passed, result_json, created_at, tenant_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id, agent_id, agent_version, profile_id, profile_version,
                    "completed", evaluation["score"], int(evaluation["passed"]),
                    canonical_json(payload), created_at, tenant_id,
                ),
            )
        return payload

    def get_run(
        self, run_id: str, tenant_id: str = LEGACY_TENANT_ID
    ) -> dict[str, Any]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT result_json FROM evaluation_runs WHERE run_id = ? AND tenant_id = ?",
                (run_id, tenant_id),
            ).fetchone()
        if row is None:
            raise EvaluationRunNotFoundError(f"Evaluation run {run_id} was not found")
        return json.loads(row["result_json"])

    def list_agent_runs(
        self, agent_id: str, agent_version: str, tenant_id: str = LEGACY_TENANT_ID
    ) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT result_json FROM evaluation_runs "
                "WHERE tenant_id = ? AND agent_id = ? AND agent_version = ? ORDER BY created_at DESC",
                (tenant_id, agent_id, agent_version),
            ).fetchall()
        return [json.loads(row["result_json"]) for row in rows]
