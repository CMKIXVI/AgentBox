from __future__ import annotations

import copy
import json
from pathlib import Path

from auth_helpers import configure_test_access
from fastapi.testclient import TestClient

from app.execution import ProviderResponse
from app.main import create_app

ROOT = Path(__file__).resolve().parents[2]
AGENT = json.loads((ROOT / "examples" / "agent-manifest-v1.json").read_text(encoding="utf-8"))
PROFILE = json.loads((ROOT / "examples" / "evaluation-profile-v1.json").read_text(encoding="utf-8"))


class EvaluationProvider:
    provider_id = "provider.fake"

    def invoke(self, request, timeout_seconds):
        del request, timeout_seconds
        return ProviderResponse(
            output={
                "summary": "A technical summary",
                "conclusion": "The conclusion is supported by the source.",
                "sources": ["source://report/1"],
            },
            input_tokens=12,
            output_tokens=18,
            cost_usd=0.001,
        )


def client_for(tmp_path: Path) -> TestClient:
    app = configure_test_access(create_app(str(tmp_path / "verified-comparison.sqlite3")))
    app.state.executions.providers["provider.fake"] = EvaluationProvider()
    return TestClient(app)


def prepare_execution_backed_pair(client: TestClient) -> tuple[str, str, str, dict, dict]:
    manifest = copy.deepcopy(AGENT)
    manifest["agent_id"] = "research.summarizer"
    manifest["model_binding"]["provider_id"] = "provider.fake"
    manifest["tools"] = []
    created = client.post("/v1/agents", json={"manifest": manifest})
    assert created.status_code == 201, created.text
    parent_version = manifest["version"]
    candidate = client.post(
        f"/v1/agents/{manifest['agent_id']}/versions/{parent_version}/candidates",
        json={
            "candidate_version": "1.0.1",
            "operator_ids": ["behavior.max_steps.decrement"],
            "seed": 42,
        },
    )
    assert candidate.status_code == 201, candidate.text
    profile = client.post("/v1/evaluation-profiles", json={"profile": PROFILE})
    assert profile.status_code == 201, profile.text

    runs = []
    for version in (parent_version, "1.0.1"):
        response = client.post(
            f"/v1/agents/{manifest['agent_id']}/versions/{version}/evaluations/execute",
            headers={"Idempotency-Key": f"verified-comparison-{version}"},
            json={"profile_id": PROFILE["profile_id"], "profile_version": PROFILE["version"]},
        )
        assert response.status_code == 201, response.text
        runs.append(response.json())
    return manifest["agent_id"], parent_version, "1.0.1", runs[0], runs[1]


def test_comparison_verifies_both_execution_evidence_chains(tmp_path: Path) -> None:
    client = client_for(tmp_path)
    agent_id, parent_version, candidate_version, parent_run, candidate_run = (
        prepare_execution_backed_pair(client)
    )
    workload_hash = parent_run["execution_evidence"]["workload_hash"]
    assert candidate_run["execution_evidence"]["workload_hash"] == workload_hash
    response = client.post(
        "/v1/agent-experiment-comparisons",
        json={
            "agent_id": agent_id,
            "parent_version": parent_version,
            "candidate_version": candidate_version,
            "parent_evaluation_run_id": parent_run["run_id"],
            "candidate_evaluation_run_id": candidate_run["run_id"],
            "workload_ref": "benchmark://research-summary/v1",
            "workload_hash": workload_hash,
        },
    )
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["evidence_status"] == "verified"
    assert result["comparison"]["execution_evidence_verified"] is True
    assert result["comparison"]["workload_provenance"] == "execution_records"
    assert result["promotion_eligible"] is False
    assert result["decision_authority"] == "advisory_only"


def test_comparison_does_not_verify_mismatched_workload_hash(tmp_path: Path) -> None:
    client = client_for(tmp_path)
    agent_id, parent_version, candidate_version, parent_run, candidate_run = (
        prepare_execution_backed_pair(client)
    )
    response = client.post(
        "/v1/agent-experiment-comparisons",
        json={
            "agent_id": agent_id,
            "parent_version": parent_version,
            "candidate_version": candidate_version,
            "parent_evaluation_run_id": parent_run["run_id"],
            "candidate_evaluation_run_id": candidate_run["run_id"],
            "workload_ref": "benchmark://research-summary/v1",
            "workload_hash": "f" * 64,
        },
    )
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["evidence_status"] == "unverified"
    assert result["comparison"]["execution_evidence_verified"] is False
    assert result["promotion_eligible"] is False


def test_caller_submitted_runs_remain_advisory(tmp_path: Path) -> None:
    client = client_for(tmp_path)
    manifest = copy.deepcopy(AGENT)
    manifest["agent_id"] = "research.summarizer"
    created = client.post("/v1/agents", json={"manifest": manifest})
    assert created.status_code == 201, created.text
    parent_version = manifest["version"]
    candidate = client.post(
        f"/v1/agents/{manifest['agent_id']}/versions/{parent_version}/candidates",
        json={
            "candidate_version": "1.0.1",
            "operator_ids": ["behavior.max_steps.decrement"],
            "seed": 42,
        },
    )
    assert candidate.status_code == 201, candidate.text
    assert client.post("/v1/evaluation-profiles", json={"profile": PROFILE}).status_code == 201
    output = {"summary": "A technical summary", "conclusion": "Supported", "sources": ["source://1"]}
    run_ids = []
    for version in (parent_version, "1.0.1"):
        response = client.post(
            f"/v1/agents/{manifest['agent_id']}/versions/{version}/evaluations",
            json={
                "profile_id": PROFILE["profile_id"],
                "profile_version": PROFILE["version"],
                "results": [
                    {"case_id": case["case_id"], "output": output, "latency_ms": 10, "cost_usd": 0.01}
                    for case in PROFILE["cases"]
                ],
            },
        )
        assert response.status_code == 201, response.text
        run_ids.append(response.json()["run_id"])
    comparison = client.post(
        "/v1/agent-experiment-comparisons",
        json={
            "agent_id": manifest["agent_id"],
            "parent_version": parent_version,
            "candidate_version": "1.0.1",
            "parent_evaluation_run_id": run_ids[0],
            "candidate_evaluation_run_id": run_ids[1],
            "workload_ref": "benchmark://research-summary/v1",
            "workload_hash": "d" * 64,
        },
    )
    assert comparison.status_code == 201, comparison.text
    assert comparison.json()["evidence_status"] == "unverified"
