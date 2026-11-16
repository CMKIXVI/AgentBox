from __future__ import annotations

import copy
import json
from pathlib import Path

from auth_helpers import configure_test_access
from fastapi.testclient import TestClient

from app.main import create_app

ROOT = Path(__file__).resolve().parents[2]
AGENT = json.loads((ROOT / "examples" / "agent-manifest-v1.json").read_text(encoding="utf-8"))
PROFILE = json.loads((ROOT / "examples" / "evaluation-profile-v1.json").read_text(encoding="utf-8"))


def client_for(tmp_path: Path) -> TestClient:
    app = configure_test_access(create_app(str(tmp_path / "experiment-comparison.sqlite3")))
    return TestClient(app)


def prepare_runs(client: TestClient) -> tuple[str, str, str, str, str]:
    manifest = copy.deepcopy(AGENT)
    manifest["agent_id"] = "research.summarizer"
    created = client.post("/v1/agents", json={"manifest": manifest})
    assert created.status_code == 201, created.text
    agent_id, parent_version = manifest["agent_id"], manifest["version"]

    candidate_response = client.post(
        f"/v1/agents/{agent_id}/versions/{parent_version}/candidates",
        json={
            "candidate_version": "1.0.1",
            "operator_ids": ["behavior.max_steps.decrement"],
            "seed": 42,
        },
    )
    assert candidate_response.status_code == 201, candidate_response.text

    profile_response = client.post("/v1/evaluation-profiles", json={"profile": PROFILE})
    assert profile_response.status_code == 201, profile_response.text

    output = {
        "summary": "A concise conclusion from the report.",
        "conclusion": "The conclusion is supported by the report.",
        "sources": ["source://report/1"],
    }
    results = [
        {"case_id": "summary.has-conclusion", "output": output, "latency_ms": 900, "cost_usd": 0.01},
        {"case_id": "summary.output-contract", "output": output, "latency_ms": 900, "cost_usd": 0.01},
    ]
    run_ids = []
    for version in (parent_version, "1.0.1"):
        response = client.post(
            f"/v1/agents/{agent_id}/versions/{version}/evaluations",
            json={
                "profile_id": PROFILE["profile_id"],
                "profile_version": PROFILE["version"],
                "results": results,
            },
        )
        assert response.status_code == 201, response.text
        run_ids.append(response.json()["run_id"])
    return agent_id, parent_version, "1.0.1", run_ids[0], run_ids[1]


def test_parent_candidate_comparison_api_is_immutable_and_advisory(tmp_path: Path) -> None:
    client = client_for(tmp_path)
    agent_id, parent_version, candidate_version, parent_run, candidate_run = prepare_runs(client)
    payload = {
        "agent_id": agent_id,
        "parent_version": parent_version,
        "candidate_version": candidate_version,
        "parent_evaluation_run_id": parent_run,
        "candidate_evaluation_run_id": candidate_run,
        "workload_ref": "benchmark://research-summary/v1",
        "workload_hash": "b" * 64,
    }

    created = client.post("/v1/agent-experiment-comparisons", json=payload)
    assert created.status_code == 201, created.text
    record = created.json()
    assert record["created"] is True
    assert record["evidence_status"] == "unverified"
    assert record["promotion_eligible"] is False
    assert record["decision_authority"] == "advisory_only"
    assert record["comparison"]["workload_provenance"] == "caller_asserted"

    replay = client.post("/v1/agent-experiment-comparisons", json=payload)
    assert replay.status_code == 201, replay.text
    assert replay.json()["created"] is False
    assert replay.json()["comparison_id"] == record["comparison_id"]

    fetched = client.get(f"/v1/agent-experiment-comparisons/{record['comparison_id']}")
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["comparison_id"] == record["comparison_id"]


def test_parent_candidate_comparison_rejects_missing_parent_and_same_run(tmp_path: Path) -> None:
    client = client_for(tmp_path)
    agent_id, parent_version, candidate_version, parent_run, candidate_run = prepare_runs(client)
    payload = {
        "agent_id": agent_id,
        "parent_version": "0.9.0",
        "candidate_version": candidate_version,
        "parent_evaluation_run_id": parent_run,
        "candidate_evaluation_run_id": candidate_run,
        "workload_ref": "benchmark://research-summary/v1",
        "workload_hash": "c" * 64,
    }
    missing_parent = client.post("/v1/agent-experiment-comparisons", json=payload)
    assert missing_parent.status_code == 404

    payload["parent_version"] = parent_version
    payload["parent_evaluation_run_id"] = candidate_run
    same_run = client.post("/v1/agent-experiment-comparisons", json=payload)
    assert same_run.status_code == 422
