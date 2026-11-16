"""Bounded, provider-adapter execution service.

This first runtime slice performs one model invocation. It never executes manifest
instructions as code and deliberately rejects tool-enabled manifests until an
authorized tool registry is installed.
"""
from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from .registry import LEGACY_TENANT_ID, AgentRegistry, canonical_json


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class _ClosingSQLiteConnection(sqlite3.Connection):
    """Preserve sqlite transaction context semantics and always release the handle."""

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


class ExecutionError(Exception):
    """Base execution failure."""


class ExecutionConflictError(ExecutionError):
    """Idempotency key reused for a different request."""


class ExecutionNotFoundError(ExecutionError):
    """Execution record not found."""


class ExecutionPolicyError(ExecutionError):
    """Manifest is not eligible for this runtime."""


class ProviderError(ExecutionError):
    """Provider adapter failed."""


@dataclass(frozen=True)
class ProviderRequest:
    provider_id: str
    model_id: str
    objective: str
    user_input: Any
    max_output_tokens: int


@dataclass(frozen=True)
class ProviderResponse:
    output: Any
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float | None = None


class ProviderAdapter(Protocol):
    provider_id: str

    def invoke(self, request: ProviderRequest, timeout_seconds: int) -> ProviderResponse:
        """Invoke a provider with an adapter-enforced timeout."""


class DeterministicFakeProvider:
    provider_id = "provider.fake"

    def invoke(self, request: ProviderRequest, timeout_seconds: int) -> ProviderResponse:
        del timeout_seconds
        return ProviderResponse(
            output={
                "objective": request.objective,
                "input": request.user_input,
                "model": request.model_id,
                "provider": self.provider_id,
            },
            input_tokens=0,
            output_tokens=0,
            cost_usd=0.0,
        )


class ExecutionService:
    def __init__(
        self,
        database_path: str | Path,
        registry: AgentRegistry,
        providers: list[ProviderAdapter] | None = None,
    ):
        self.database_path = str(database_path)
        self.registry = registry
        self.providers = {item.provider_id: item for item in (providers or [])}
        if self.database_path == ":memory:":
            self._dsn = f"file:agentbox-executions-{id(self)}?mode=memory&cache=shared"
            self._uri = True
            self._keeper = sqlite3.connect(self._dsn, uri=True, timeout=10)
        else:
            self._dsn = self.database_path
            self._uri = False
            self._keeper = None
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
        connection = sqlite3.connect(
            self._dsn, uri=self._uri, timeout=10, factory=_ClosingSQLiteConnection
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS executions (
                    execution_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    agent_version TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    request_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result_json TEXT,
                    error_code TEXT,
                    created_at TEXT NOT NULL,
                    completed_at TEXT
                )
                """
            )
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(executions)")}
            if "tenant_id" not in columns:
                connection.execute(
                    "ALTER TABLE executions ADD COLUMN tenant_id TEXT NOT NULL "
                    "DEFAULT '__legacy_unassigned__'"
                )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_executions_tenant_agent "
                "ON executions(tenant_id, agent_id, agent_version, created_at)"
            )
            # A synchronous provider call may be interrupted by process termination.
            # Never replay it automatically: the provider may already have completed
            # the request and charged for it. The SQLite runtime is single-instance;
            # on exclusive process startup, fence leftover running records as ambiguous.
            connection.execute(
                """UPDATE executions
                SET status='interrupted',
                    error_code='execution_interrupted_ambiguous_outcome',
                    completed_at=?
                WHERE status='running'""",
                (utc_now(),),
            )

    def _record(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "execution_id": row["execution_id"],
            "agent_id": row["agent_id"],
            "agent_version": row["agent_version"],
            "status": row["status"],
            "result": json.loads(row["result_json"]) if row["result_json"] else None,
            "error_code": row["error_code"],
            "created_at": row["created_at"],
            "completed_at": row["completed_at"],
        }

    def get(
        self, execution_id: str, tenant_id: str = LEGACY_TENANT_ID
    ) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM executions WHERE execution_id = ? AND tenant_id = ?",
                (execution_id, tenant_id),
            ).fetchone()
        if row is None:
            raise ExecutionNotFoundError(execution_id)
        return self._record(row)

    def execute(
        self,
        agent_id: str,
        version: str,
        user_input: Any,
        idempotency_key: str,
        max_output_tokens: int = 1024,
        tenant_id: str = LEGACY_TENANT_ID,
    ) -> dict[str, Any]:
        if not idempotency_key or len(idempotency_key) > 128:
            raise ValueError("A non-empty idempotency key of at most 128 characters is required")
        if not 1 <= max_output_tokens <= 8192:
            raise ValueError("max_output_tokens must be between 1 and 8192")
        agent = self.registry.get(agent_id, version, tenant_id)
        manifest = agent.manifest
        # This vertical slice does not yet possess a tool registry or authorization
        # principal. Deny any manifest that requests tools rather than silently ignoring them.
        if manifest.get("tools"):
            raise ExecutionPolicyError("Tool-enabled agents are denied until tool authorization is available")
        provider_id = manifest["model_binding"]["provider_id"]
        provider = self.providers.get(provider_id)
        if provider is None:
            raise ExecutionPolicyError(f"Provider is not configured: {provider_id}")
        request_payload = {
            "agent_id": agent_id,
            "version": version,
            "input": user_input,
            "max_output_tokens": max_output_tokens,
        }
        request_hash = hashlib.sha256(canonical_json(request_payload).encode()).hexdigest()
        tenant_idempotency_key = hashlib.sha256(
            canonical_json({"tenant_id": tenant_id, "idempotency_key": idempotency_key}).encode()
        ).hexdigest()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM executions WHERE idempotency_key = ? AND tenant_id = ?",
                (tenant_idempotency_key, tenant_id),
            ).fetchone()
            if existing:
                if existing["request_hash"] != request_hash:
                    raise ExecutionConflictError("Idempotency key was already used for a different request")
                return self._record(existing)
            execution_id = str(uuid.uuid4())
            created_at = utc_now()
            connection.execute(
                """INSERT INTO executions
                (execution_id, agent_id, agent_version, idempotency_key, request_hash,
                 status, created_at, tenant_id) VALUES (?, ?, ?, ?, ?, 'running', ?, ?)""",
                (execution_id, agent_id, version, tenant_idempotency_key, request_hash, created_at, tenant_id),
            )

        timeout = min(manifest["behavior"]["timeout_seconds"], 3600)
        request = ProviderRequest(
            provider_id=provider_id,
            model_id=manifest["model_binding"]["model_id"],
            objective=manifest["behavior"]["objective"],
            user_input=user_input,
            max_output_tokens=max_output_tokens,
        )
        started_monotonic = time.perf_counter()
        try:
            response = provider.invoke(request, timeout)
            if not isinstance(response, ProviderResponse):
                raise ProviderError("Provider returned an invalid response envelope")
            if (
                type(response.input_tokens) is not int
                or type(response.output_tokens) is not int
                or response.input_tokens < 0
                or response.output_tokens < 0
                or (
                    response.cost_usd is not None
                    and (
                        isinstance(response.cost_usd, bool)
                        or not isinstance(response.cost_usd, (int, float))
                        or not math.isfinite(response.cost_usd)
                        or response.cost_usd < 0
                    )
                )
            ):
                raise ProviderError("Provider returned invalid usage metrics")
            result = {
                "output": response.output,
                "usage": {
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "cost_usd": response.cost_usd,
                },
                "provider_id": provider_id,
                "model_id": request.model_id,
                "steps": 1,
                "latency_ms": round((time.perf_counter() - started_monotonic) * 1000, 3),
            }
            completed_at = utc_now()
            with self._connect() as connection:
                connection.execute(
                    """UPDATE executions SET status='completed', result_json=?,
                    completed_at=? WHERE execution_id=?""",
                    (canonical_json(result), completed_at, execution_id),
                )
        except Exception as exc:
            completed_at = utc_now()
            code = "provider_error" if isinstance(exc, ProviderError) else "provider_failure"
            with self._connect() as connection:
                connection.execute(
                    """UPDATE executions SET status='failed', error_code=?,
                    completed_at=? WHERE execution_id=?""",
                    (code, completed_at, execution_id),
                )
            if isinstance(exc, ExecutionError):
                raise
            raise ProviderError("Provider invocation failed") from exc
        return self.get(execution_id, tenant_id)
