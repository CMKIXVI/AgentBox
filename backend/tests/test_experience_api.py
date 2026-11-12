from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from auth_helpers import configure_test_access
from fastapi.testclient import TestClient

from app.execution import DeterministicFakeProvider
from app.main import create_app

ROOT = Path(__file__).resolve().parents[2]
AGENT = json.loads((ROOT / "examples" / "agent-manifest-v1.json").read_text(encoding="utf-8"))
PROFILE = json.loads(
    (ROOT / "examples" / "evaluation-profile-v1.json").read_text(encoding="utf-8")
)


def client_for(tmp_path: Path) -> TestClient:
    app = configure_test_access(create_app(str(tmp_path / "experience.sqlite3")))
    app.state.executions.providers["provider.fake"] = DeterministicFakeProvider()
    return TestClient(app)


def prepare(client: TestClient) -> tuple[str, str]:
    agent = copy.deepcopy(AGENT)
    agent["agent_id"] = "runtime.test"
    agent["model_binding"]["provider_id"] = "provider.fake"
    agent["tools"] = []
    assert client.post("/v1/agents", json={"manifest": agent}).status_code == 201
    assert client.post("/v1/evaluation-profiles", json={"profile": PROFILE}).status_code == 201
    return agent["agent_id"], agent["version"]


def make_experience(
    client: TestClient, agent_id: str, version: str, id_suffix: str,
    latency: float = 1000, cost: float = 0.01,
) -> dict:
    execution = client.post(
        f"/v1/agents/{agent_id}/versions/{version}/executions",
        headers={"Idempotency-Key": f"experience-exec-{id_suffix}"},
        json={"input": {"case": id_suffix}},
    )
    assert execution.status_code == 201, execution.text
    results = [
        {
            "case_id": case["case_id"],
            "output": {
                "summary": "Technical summary",
                "conclusion": "The conclusion is supported by the report.",
                "sources": ["report.pdf"],
            },
            "latency_ms": latency,
            "cost_usd": cost,
        }
        for case in PROFILE["cases"]
    ]
    evaluation = client.post(
        f"/v1/agents/{agent_id}/versions/{version}/evaluations",
        json={
            "profile_id": PROFILE["profile_id"],
            "profile_version": PROFILE["version"],
            "results": results,
        },
    )
    assert evaluation.status_code == 201, evaluation.text
    workload_hash = hashlib.sha256(f"workload-{id_suffix}".encode()).hexdigest()
    response = client.post(
        "/v1/agent-experiences",
        json={
            "execution_id": execution.json()["execution_id"],
            "evaluation_run_id": evaluation.json()["run_id"],
            "workload_ref": f"benchmark://test/{id_suffix}",
            "workload_hash": workload_hash,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_experience_is_minimized_immutable_and_idempotent(tmp_path: Path) -> None:
    client = client_for(tmp_path)
    agent_id, version = prepare(client)
    experience = make_experience(client, agent_id, version, "one")
    assert experience["created"] is True
    assert experience["linkage_status"] == "caller_asserted"
    assert experience["evidence_status"] == "unverified"
    assert experience["evaluation"]["passed"] is True
    assert "output" not in experience
    assert "input" not in experience

    replay = client.post(
        "/v1/agent-experiences",
        json={
            "execution_id": experience["execution_id"],
            "evaluation_run_id": experience["evaluation_run_id"],
            "workload_ref": experience["workload_ref"],
            "workload_hash": experience["workload_hash"],
        },
    )
    assert replay.status_code == 201
    assert replay.json()["created"] is False
    assert replay.json()["experience_id"] == experience["experience_id"]


def test_experience_rejects_conflicting_replay_and_bad_hash(tmp_path: Path) -> None:
    client = client_for(tmp_path)
    agent_id, version = prepare(client)
    experience = make_experience(client, agent_id, version, "conflict")
    conflict = client.post(
        "/v1/agent-experiences",
        json={
            "execution_id": experience["execution_id"],
            "evaluation_run_id": experience["evaluation_run_id"],
            "workload_ref": "benchmark://different",
            "workload_hash": experience["workload_hash"],
        },
    )
    assert conflict.status_code == 409
    bad = client.post(
        "/v1/agent-experiences",
        json={
            "execution_id": experience["execution_id"],
            "evaluation_run_id": experience["evaluation_run_id"],
            "workload_ref": "benchmark://bad",
            "workload_hash": "not-a-hash",
        },
    )
    assert bad.status_code == 422


def test_experience_rejects_cross_agent_and_unknown_links(tmp_path: Path) -> None:
    client = client_for(tmp_path)
    agent_id, version = prepare(client)
    experience = make_experience(client, agent_id, version, "source")
    other = copy.deepcopy(AGENT)
    other["agent_id"] = "runtime.other"
    other["model_binding"]["provider_id"] = "provider.fake"
    other["tools"] = []
    assert client.post("/v1/agents", json={"manifest": other}).status_code == 201
    evaluation = client.post(
        f"/v1/agents/{other['agent_id']}/versions/{version}/evaluations",
        json={
            "profile_id": PROFILE["profile_id"],
            "profile_version": PROFILE["version"],
            "results": [],
        },
    )
    assert evaluation.status_code == 201
    mismatch = client.post(
        "/v1/agent-experiences",
        json={
            "execution_id": experience["execution_id"],
            "evaluation_run_id": evaluation.json()["run_id"],
            "workload_ref": "benchmark://mismatch",
            "workload_hash": hashlib.sha256(b"mismatch").hexdigest(),
        },
    )
    assert mismatch.status_code == 422
    missing = client.post(
        "/v1/agent-experiences",
        json={
            "execution_id": "missing-execution",
            "evaluation_run_id": evaluation.json()["run_id"],
            "workload_ref": "benchmark://missing",
            "workload_hash": hashlib.sha256(b"missing").hexdigest(),
        },
    )
    assert missing.status_code == 404


def test_lessons_are_proposed_idempotent_and_traceable(tmp_path: Path) -> None:
    client = client_for(tmp_path)
    agent_id, version = prepare(client)
    experience = make_experience(client, agent_id, version, "lesson")
    payload = {
        "lesson_type": "quality.failure-pattern",
        "statement": "The candidate should improve source attribution.",
        "evidence_refs": [experience["experience_id"]],
        "source_kind": "model_proposal",
        "extractor_version": "lesson-extractor/1.0.0",
        "confidence": 0.7,
    }
    first = client.post(
        f"/v1/agent-experiences/{experience['experience_id']}/lessons", json=payload
    )
    replay = client.post(
        f"/v1/agent-experiences/{experience['experience_id']}/lessons", json=payload
    )
    assert first.status_code == replay.status_code == 201
    assert first.json()["created"] is True
    assert replay.json()["created"] is False
    assert first.json()["status"] == "proposed"
    assert first.json()["source_kind"] == "model_proposal"
    assert client.get(
        f"/v1/agent-experiences/{experience['experience_id']}/lessons"
    ).json()["items"][0]["lesson_id"] == first.json()["lesson_id"]


def test_lesson_requires_source_experience_reference(tmp_path: Path) -> None:
    client = client_for(tmp_path)
    agent_id, version = prepare(client)
    experience = make_experience(client, agent_id, version, "untraced")
    response = client.post(
        f"/v1/agent-experiences/{experience['experience_id']}/lessons",
        json={
            "lesson_type": "quality.lesson",
            "statement": "Untraceable lesson",
            "evidence_refs": ["benchmark://unrelated"],
            "source_kind": "deterministic_rule",
            "extractor_version": "rules/1.0.0",
            "confidence": 0.5,
        },
    )
    assert response.status_code == 422


def test_fitness_selection_requires_minimum_samples_and_pins_profile(tmp_path: Path) -> None:
    client = client_for(tmp_path)
    agent_id, version = prepare(client)
    make_experience(client, agent_id, version, "fitness-1", latency=1000)
    selection = client.get(
        "/v1/fitness/selection",
        params={
            "profile_id": PROFILE["profile_id"],
            "profile_version": PROFILE["version"],
            "min_samples": 2,
        },
    )
    assert selection.status_code == 200
    assert selection.json()["items"] == []

    make_experience(client, agent_id, version, "fitness-2", latency=1500)
    selection = client.get(
        "/v1/fitness/selection",
        params={
            "profile_id": PROFILE["profile_id"],
            "profile_version": PROFILE["version"],
            "min_samples": 2,
        },
    )
    assert selection.status_code == 200
    item = selection.json()["items"][0]
    assert item["sample_count"] == 2
    assert item["profile_version"] == PROFILE["version"]
    assert 0 <= item["sample_confidence"] <= 1
    assert 0 <= item["improvement_priority"] <= 1


def test_experience_and_fitness_endpoints_enforce_authorization(tmp_path: Path) -> None:
    client = client_for(tmp_path)
    client.app.state.authorization_policies = []
    assert client.post(
        "/v1/agent-experiences",
        json={
            "execution_id": "x",
            "evaluation_run_id": "y",
            "workload_ref": "benchmark://x",
            "workload_hash": hashlib.sha256(b"x").hexdigest(),
        },
    ).status_code == 403
    assert client.get(
        "/v1/fitness/selection",
        params={"profile_id": PROFILE["profile_id"], "profile_version": PROFILE["version"]},
    ).status_code == 403
