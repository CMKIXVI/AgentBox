from __future__ import annotations

import copy
import json
from pathlib import Path

from auth_helpers import configure_test_access
from fastapi.testclient import TestClient
from app.main import create_app

ROOT = Path(__file__).resolve().parents[2]
AGENT = json.loads((ROOT / "examples" / "agent-manifest-v1.json").read_text(encoding="utf-8"))


def client_for(tmp_path: Path) -> TestClient:
    app = configure_test_access(create_app(str(tmp_path / "candidate.sqlite3")))
    return TestClient(app)


def create_agent(client: TestClient) -> tuple[str, str]:
    manifest = copy.deepcopy(AGENT)
    manifest["agent_id"] = "runtime.test"
    response = client.post("/v1/agents", json={"manifest": manifest})
    assert response.status_code == 201, response.text
    return manifest["agent_id"], manifest["version"]


def test_candidate_generation_is_bounded_and_preserves_parent(tmp_path: Path) -> None:
    client = client_for(tmp_path)
    agent_id, parent_version = create_agent(client)
    parent_before = client.get(
        f"/v1/agents/{agent_id}/versions/{parent_version}"
    ).json()["manifest"]

    response = client.post(
        f"/v1/agents/{agent_id}/versions/{parent_version}/candidates",
        json={
            "candidate_version": "1.0.1",
            "operator_ids": [
                "behavior.max_steps.decrement",
                "model.parameters.temperature.lower",
            ],
            "seed": 42,
        },
    )
    assert response.status_code == 201, response.text
    result = response.json()
    candidate = result["manifest"]

    assert result["created"] is True
    assert result["parent_artifact_id"] == f"{agent_id}@{parent_version}"
    assert result["parent_content_hash"]
    assert result["candidate_content_hash"] == result["content_hash"]
    assert result["trust_status"] == "unverified_candidate"
    assert result["promotion_eligible"] is False
    assert candidate["version"] == "1.0.1"
    assert candidate["behavior"]["max_steps"] == parent_before["behavior"]["max_steps"] - 1
    assert candidate["permissions"] == parent_before["permissions"]
    assert candidate["tools"] == parent_before["tools"]
    assert parent_before["version"] == parent_version
    assert client.get(
        f"/v1/agents/{agent_id}/versions/{parent_version}"
    ).json()["manifest"] == parent_before
    assert result["parent_artifact_id"] in candidate["provenance"]["source_refs"]
    assert any(
        item.startswith("agentbox:mutation/")
        for item in candidate["provenance"]["source_refs"]
    )


def test_candidate_generation_rejects_unknown_or_security_mutation(tmp_path: Path) -> None:
    client = client_for(tmp_path)
    agent_id, version = create_agent(client)

    unknown = client.post(
        f"/v1/agents/{agent_id}/versions/{version}/candidates",
        json={
            "candidate_version": "1.0.1",
            "operator_ids": ["permissions.expand"],
            "seed": 1,
        },
    )
    assert unknown.status_code == 422

    invalid_seed = client.post(
        f"/v1/agents/{agent_id}/versions/{version}/candidates",
        json={
            "candidate_version": "1.0.1",
            "operator_ids": ["behavior.max_steps.decrement"],
            "seed": -1,
        },
    )
    assert invalid_seed.status_code == 422


def test_candidate_generation_rejects_duplicate_version_and_noop(tmp_path: Path) -> None:
    client = client_for(tmp_path)
    agent_id, version = create_agent(client)
    endpoint = f"/v1/agents/{agent_id}/versions/{version}/candidates"
    payload = {
        "candidate_version": "1.0.1",
        "operator_ids": ["behavior.max_steps.decrement"],
        "seed": 7,
    }
    assert client.post(endpoint, json=payload).status_code == 201
    duplicate = client.post(endpoint, json=payload)
    assert duplicate.status_code == 409

    # At the schema lower bound, decrementing max_steps cannot create a change.
    parent = client.get(f"/v1/agents/{agent_id}/versions/{version}").json()["manifest"]
    parent["behavior"]["max_steps"] = 1
    # Create a second source version with the lower-bound value.
    parent["version"] = "1.0.2"
    created = client.post("/v1/agents", json={"manifest": parent})
    assert created.status_code == 201, created.text
    noop = client.post(
        f"/v1/agents/{agent_id}/versions/1.0.2/candidates",
        json={
            "candidate_version": "1.0.3",
            "operator_ids": ["behavior.max_steps.decrement"],
            "seed": 7,
        },
    )
    assert noop.status_code == 422



def test_clone_api_cannot_override_security_boundaries(tmp_path: Path) -> None:
    client = client_for(tmp_path)
    agent_id, version = create_agent(client)
    parent = client.get(f"/v1/agents/{agent_id}/versions/{version}").json()["manifest"]

    for field in ("permissions", "tools"):
        response = client.post(
            f"/v1/agents/{agent_id}/versions/{version}/clone",
            json={
                "new_version": "1.0.1" if field == "permissions" else "1.0.2",
                "overrides": {field: parent[field]},
            },
        )
        assert response.status_code == 422
        assert field in response.json()["detail"]["fields"]
