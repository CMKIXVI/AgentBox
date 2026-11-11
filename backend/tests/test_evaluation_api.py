from __future__ import annotations

import copy
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from auth_helpers import configure_test_access

ROOT = Path(__file__).resolve().parents[2]
AGENT = json.loads((ROOT / "examples" / "agent-manifest-v1.json").read_text(encoding="utf-8"))
PROFILE = json.loads(
    (ROOT / "examples" / "evaluation-profile-v1.json").read_text(encoding="utf-8")
)


def client_for(tmp_path: Path) -> TestClient:
    return TestClient(configure_test_access(create_app(str(tmp_path / "evaluation.sqlite3"))))


def seed_agent_and_profile(client: TestClient) -> None:
    agent_response = client.post("/v1/agents", json={"manifest": AGENT})
    profile_response = client.post("/v1/evaluation-profiles", json={"profile": PROFILE})
    assert agent_response.status_code == 201
    assert profile_response.status_code == 201


def passing_results() -> list[dict]:
    return [
        {
            "case_id": "summary.has-conclusion",
            "output": {
                "summary": "Technical summary",
                "conclusion": "The conclusion is supported by the report.",
                "sources": ["report.pdf"],
            },
            "latency_ms": 1000,
            "cost_usd": 0.01,
        },
        {
            "case_id": "summary.output-contract",
            "output": {
                "summary": "Technical summary",
                "conclusion": "Supported conclusion",
                "sources": ["report.pdf"],
            },
            "latency_ms": 2000,
            "cost_usd": 0.01,
        },
    ]


def test_evaluation_profile_example_passes_authoritative_schema(tmp_path: Path) -> None:
    response = client_for(tmp_path).post(
        "/v1/evaluation-profiles/validate", json={"profile": PROFILE}
    )
    assert response.status_code == 200
    assert response.json() == {"valid": True, "errors": []}


def test_evaluation_profile_rejects_bad_weights_and_duplicate_case_ids(
    tmp_path: Path,
) -> None:
    invalid = copy.deepcopy(PROFILE)
    invalid["scoring"]["correctness_weight"] = 0.5
    invalid["cases"][1]["case_id"] = invalid["cases"][0]["case_id"]
    response = client_for(tmp_path).post(
        "/v1/evaluation-profiles/validate", json={"profile": invalid}
    )
    assert response.json()["valid"] is False
    assert len(response.json()["errors"]) == 2


def test_profile_create_is_immutable_and_idempotent(tmp_path: Path) -> None:
    client = client_for(tmp_path)
    first = client.post("/v1/evaluation-profiles", json={"profile": PROFILE})
    replay = client.post("/v1/evaluation-profiles", json={"profile": PROFILE})
    assert first.status_code == replay.status_code == 201
    assert first.json()["created"] is True
    assert replay.json()["created"] is False
    assert first.json()["content_hash"] == replay.json()["content_hash"]


def test_profile_version_conflict_and_retrieval(tmp_path: Path) -> None:
    client = client_for(tmp_path)
    assert client.post("/v1/evaluation-profiles", json={"profile": PROFILE}).status_code == 201
    changed = copy.deepcopy(PROFILE)
    changed["description"] = "Changed under the same immutable version."
    conflict = client.post("/v1/evaluation-profiles", json={"profile": changed})
    assert conflict.status_code == 409
    fetched = client.get(
        "/v1/evaluation-profiles/quality.research-summary/versions/1.0.0"
    )
    assert fetched.status_code == 200
    assert fetched.json()["profile"] == PROFILE


def test_evaluation_run_scores_gates_and_persists_results(tmp_path: Path) -> None:
    client = client_for(tmp_path)
    seed_agent_and_profile(client)
    response = client.post(
        "/v1/agents/research.summarizer/versions/1.0.0/evaluations",
        json={
            "profile_id": "quality.research-summary",
            "profile_version": "1.0.0",
            "results": passing_results(),
        },
    )
    assert response.status_code == 201
    result = response.json()
    assert result["status"] == "completed"
    assert result["passed"] is True, result
    assert result["score"] == 0.93
    assert result["case_pass_rate"] == 1.0
    assert result["avg_latency_ms"] == 1500
    assert result["total_cost_usd"] == 0.02
    assert all(gate["passed"] for gate in result["gate_results"].values())

    fetched = client.get(f"/v1/evaluations/{result['run_id']}")
    assert fetched.status_code == 200
    assert fetched.json() == result
    listed = client.get(
        "/v1/agents/research.summarizer/versions/1.0.0/evaluations"
    )
    assert len(listed.json()["items"]) == 1


def test_failed_assertion_and_budget_gates_block_promotion(tmp_path: Path) -> None:
    client = client_for(tmp_path)
    seed_agent_and_profile(client)
    results = passing_results()
    results[0]["output"]["conclusion"] = "No evidence."
    results[0]["latency_ms"] = 9000
    results[1]["latency_ms"] = 9000
    results[0]["cost_usd"] = 0.04
    results[1]["cost_usd"] = 0.04
    response = client.post(
        "/v1/agents/research.summarizer/versions/1.0.0/evaluations",
        json={
            "profile_id": "quality.research-summary",
            "profile_version": "1.0.0",
            "results": results,
        },
    )
    result = response.json()
    assert result["passed"] is False
    assert result["case_pass_rate"] == 0.5
    assert result["gate_results"]["case_pass_rate"]["passed"] is False
    assert result["gate_results"]["avg_latency_ms"]["passed"] is False
    assert result["gate_results"]["total_cost_usd"]["passed"] is False


def test_missing_case_is_counted_as_failure(tmp_path: Path) -> None:
    client = client_for(tmp_path)
    seed_agent_and_profile(client)
    response = client.post(
        "/v1/agents/research.summarizer/versions/1.0.0/evaluations",
        json={
            "profile_id": "quality.research-summary",
            "profile_version": "1.0.0",
            "results": passing_results()[:1],
        },
    )
    result = response.json()
    assert result["case_pass_rate"] == 0.5
    assert result["case_results"][1]["passed"] is False
    assert "No output" in result["case_results"][1]["reason"]


def test_duplicate_and_unknown_case_results_are_rejected(tmp_path: Path) -> None:
    client = client_for(tmp_path)
    seed_agent_and_profile(client)
    duplicate = passing_results()
    duplicate.append(copy.deepcopy(duplicate[0]))
    base = {
        "profile_id": "quality.research-summary",
        "profile_version": "1.0.0",
    }
    first = client.post(
        "/v1/agents/research.summarizer/versions/1.0.0/evaluations",
        json={**base, "results": duplicate},
    )
    assert first.status_code == 422
    unknown = passing_results()
    unknown[0]["case_id"] = "not.in.profile"
    second = client.post(
        "/v1/agents/research.summarizer/versions/1.0.0/evaluations",
        json={**base, "results": unknown},
    )
    assert second.status_code == 422


def test_evaluation_requires_existing_agent_and_profile(tmp_path: Path) -> None:
    client = client_for(tmp_path)
    seed_agent_and_profile(client)
    missing_agent = client.post(
        "/v1/agents/not.registered/versions/1.0.0/evaluations",
        json={
            "profile_id": "quality.research-summary",
            "profile_version": "1.0.0",
            "results": [],
        },
    )
    assert missing_agent.status_code == 404
    missing_profile = client.post(
        "/v1/agents/research.summarizer/versions/1.0.0/evaluations",
        json={
            "profile_id": "missing.profile",
            "profile_version": "1.0.0",
            "results": [],
        },
    )
    assert missing_profile.status_code == 404


def test_unknown_evaluation_run_returns_404(tmp_path: Path) -> None:
    response = client_for(tmp_path).get("/v1/evaluations/not-a-run")
    assert response.status_code == 404


def test_evaluation_profile_rejects_invalid_embedded_assertion_schema(
    tmp_path: Path,
) -> None:
    invalid = copy.deepcopy(PROFILE)
    invalid["cases"][1]["assertions"][0]["schema"] = {"type": "not-a-json-schema-type"}
    response = client_for(tmp_path).post(
        "/v1/evaluation-profiles/validate", json={"profile": invalid}
    )
    assert response.json()["valid"] is False
    assert any(
        "Invalid embedded JSON Schema" in error["message"]
        for error in response.json()["errors"]
    )
