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



def test_execution_migration_quarantines_pre_tenant_rows(tmp_path: Path) -> None:
    path = tmp_path / "legacy-execution.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute(
            """CREATE TABLE executions (
                execution_id TEXT PRIMARY KEY, agent_id TEXT NOT NULL,
                agent_version TEXT NOT NULL, idempotency_key TEXT NOT NULL UNIQUE,
                request_hash TEXT NOT NULL, status TEXT NOT NULL, result_json TEXT,
                error_code TEXT, created_at TEXT NOT NULL, completed_at TEXT)"""
        )
        connection.execute(
            """INSERT INTO executions VALUES (
                'legacy-run', 'legacy.agent', '1.0.0', 'legacy-key', 'hash',
                'completed', '{}', NULL, '2026-01-01T00:00:00+00:00',
                '2026-01-01T00:00:01+00:00')"""
        )
    registry = AgentRegistry(path)
    service = ExecutionService(path, registry, [DeterministicFakeProvider()])
    assert service.get("legacy-run")["execution_id"] == "legacy-run"
    with pytest.raises(ExecutionNotFoundError):
        service.get("legacy-run", "tenant-alpha")


def test_evaluation_migration_quarantines_pre_tenant_rows(tmp_path: Path) -> None:
    path = tmp_path / "legacy-evaluation.sqlite3"
    profile_payload = json.dumps(PROFILE, separators=(",", ":"))
    run_payload = json.dumps({"run_id": "legacy-evaluation", "agent_id": "legacy.agent"})
    with sqlite3.connect(path) as connection:
        connection.execute(
            """CREATE TABLE evaluation_profiles (
                profile_id TEXT NOT NULL, version TEXT NOT NULL,
                content_hash TEXT NOT NULL, profile_json TEXT NOT NULL,
                created_at TEXT NOT NULL, PRIMARY KEY (profile_id, version))"""
        )
        connection.execute(
            """CREATE TABLE evaluation_runs (
                run_id TEXT PRIMARY KEY, agent_id TEXT NOT NULL,
                agent_version TEXT NOT NULL, profile_id TEXT NOT NULL,
                profile_version TEXT NOT NULL, status TEXT NOT NULL,
                score REAL NOT NULL, passed INTEGER NOT NULL,
                result_json TEXT NOT NULL, created_at TEXT NOT NULL,
                FOREIGN KEY (profile_id, profile_version)
                REFERENCES evaluation_profiles(profile_id, version))"""
        )
        connection.execute(
            "INSERT INTO evaluation_profiles VALUES (?, ?, ?, ?, ?)",
            (PROFILE["profile_id"], PROFILE["version"], "legacy-hash", profile_payload, "2026-01-01"),
        )
        connection.execute(
            "INSERT INTO evaluation_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "legacy-evaluation", "legacy.agent", "1.0.0", PROFILE["profile_id"],
                PROFILE["version"], "completed", 0.0, 0, run_payload, "2026-01-01",
            ),
        )
    service = EvaluationService(path)
    assert service.get_profile(PROFILE["profile_id"], PROFILE["version"])["profile"] == PROFILE
    with pytest.raises(EvaluationProfileNotFoundError):
        service.get_profile(PROFILE["profile_id"], PROFILE["version"], "tenant-alpha")
    assert service.get_run("legacy-evaluation")["run_id"] == "legacy-evaluation"
    with pytest.raises(EvaluationRunNotFoundError):
        service.get_run("legacy-evaluation", "tenant-alpha")



def test_same_agent_identity_can_exist_in_multiple_tenants(tmp_path: Path) -> None:
    registry = AgentRegistry(tmp_path / "shared-agent.sqlite3")
    manifest = tenant_agent("agent.same-id")
    first, created_first = registry.create(manifest, tenant_id="tenant-alpha")
    second, created_second = registry.create(manifest, tenant_id="tenant-beta")
    assert created_first is True
    assert created_second is True
    assert first.agent_id == second.agent_id
    assert first.tenant_id == "tenant-alpha"
    assert second.tenant_id == "tenant-beta"
    assert registry.get("agent.same-id", "1.0.0", "tenant-alpha").tenant_id == "tenant-alpha"
    assert registry.get("agent.same-id", "1.0.0", "tenant-beta").tenant_id == "tenant-beta"


def test_same_evaluation_profile_identity_can_exist_in_multiple_tenants(tmp_path: Path) -> None:
    service = EvaluationService(tmp_path / "shared-evaluation.sqlite3")
    first, created_first = service.create_profile(PROFILE, tenant_id="tenant-alpha")
    second, created_second = service.create_profile(PROFILE, tenant_id="tenant-beta")
    assert created_first is True
    assert created_second is True
    assert first["profile_id"] == second["profile_id"]
    assert service.get_profile(PROFILE["profile_id"], PROFILE["version"], "tenant-alpha")
    assert service.get_profile(PROFILE["profile_id"], PROFILE["version"], "tenant-beta")


def test_evaluation_run_cannot_reference_another_tenants_profile(tmp_path: Path) -> None:
    service = EvaluationService(tmp_path / "evaluation-fk.sqlite3")
    service.create_profile(PROFILE, tenant_id="tenant-alpha")
    with pytest.raises(sqlite3.IntegrityError):
        service.create_run(
            "agent.beta", "1.0.0", PROFILE["profile_id"], PROFILE["version"], [], "tenant-beta"
        )
