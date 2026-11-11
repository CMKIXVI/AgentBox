from __future__ import annotations

import copy
import json
import sqlite3
from pathlib import Path

import pytest

from app.evaluation import (
    EvaluationProfileNotFoundError,
    EvaluationRunNotFoundError,
    EvaluationService,
)
from app.execution import (
    DeterministicFakeProvider,
    ExecutionNotFoundError,
    ExecutionService,
)
from app.registry import AgentNotFoundError, AgentRegistry

ROOT = Path(__file__).resolve().parents[2]
AGENT = json.loads((ROOT / "examples" / "agent-manifest-v1.json").read_text())
PROFILE = json.loads((ROOT / "examples" / "evaluation-profile-v1.json").read_text())


def tenant_agent(agent_id: str) -> dict:
    value = copy.deepcopy(AGENT)
    value["agent_id"] = agent_id
    value["model_binding"]["provider_id"] = "provider.fake"
    value["tools"] = []
    return value


def test_registry_reads_are_scoped_to_tenant(tmp_path: Path) -> None:
    registry = AgentRegistry(tmp_path / "registry.sqlite3")
    registry.create(tenant_agent("tenant.alpha.agent"), tenant_id="tenant-alpha")
    assert registry.get("tenant.alpha.agent", "1.0.0", "tenant-alpha").tenant_id == "tenant-alpha"
    with pytest.raises(AgentNotFoundError):
        registry.get("tenant.alpha.agent", "1.0.0", "tenant-beta")
    assert registry.list("tenant.alpha.agent", tenant_id="tenant-beta") == []


def test_registry_migration_quarantines_pre_tenant_rows(tmp_path: Path) -> None:
    path = tmp_path / "legacy-registry.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute(
            """CREATE TABLE agent_versions (
                agent_id TEXT NOT NULL, version TEXT NOT NULL, content_hash TEXT NOT NULL,
                manifest_json TEXT NOT NULL, parent_artifact_id TEXT, created_at TEXT NOT NULL,
                PRIMARY KEY (agent_id, version))"""
        )
        from app.registry import canonical_json, content_hash

        manifest = tenant_agent("legacy.agent")
        connection.execute(
            "INSERT INTO agent_versions VALUES (?, ?, ?, ?, ?, ?)",
            (
                manifest["agent_id"], manifest["version"], content_hash(manifest),
                canonical_json(manifest), None, manifest["provenance"]["created_at"],
            ),
        )
    registry = AgentRegistry(path)
    assert registry.get("legacy.agent", "1.0.0").tenant_id == "__legacy_unassigned__"
    with pytest.raises(AgentNotFoundError):
        registry.get("legacy.agent", "1.0.0", "tenant-alpha")


def test_execution_records_and_idempotency_are_tenant_scoped(tmp_path: Path) -> None:
    path = tmp_path / "execution.sqlite3"
    registry = AgentRegistry(path)
    registry.create(tenant_agent("tenant.alpha.agent"), tenant_id="tenant-alpha")
    registry.create(tenant_agent("tenant.beta.agent"), tenant_id="tenant-beta")
    service = ExecutionService(path, registry, [DeterministicFakeProvider()])
    first = service.execute(
        "tenant.alpha.agent", "1.0.0", "hello", "same-key", tenant_id="tenant-alpha"
    )
    second = service.execute(
        "tenant.beta.agent", "1.0.0", "hello", "same-key", tenant_id="tenant-beta"
    )
    assert first["execution_id"] != second["execution_id"]
    assert service.get(first["execution_id"], "tenant-alpha") == first
    with pytest.raises(ExecutionNotFoundError):
        service.get(first["execution_id"], "tenant-beta")


def test_evaluation_profiles_and_runs_are_tenant_scoped(tmp_path: Path) -> None:
    service = EvaluationService(tmp_path / "evaluation.sqlite3")
    service.create_profile(PROFILE, tenant_id="tenant-alpha")
    with pytest.raises(EvaluationProfileNotFoundError):
        service.get_profile(PROFILE["profile_id"], PROFILE["version"], "tenant-beta")
    run = service.create_run(
        "agent.alpha", "1.0.0", PROFILE["profile_id"], PROFILE["version"], [], "tenant-alpha"
    )
    assert service.get_run(run["run_id"], "tenant-alpha") == run
    with pytest.raises(EvaluationRunNotFoundError):
        service.get_run(run["run_id"], "tenant-beta")
    assert service.list_agent_runs("agent.alpha", "1.0.0", "tenant-beta") == []
