from __future__ import annotations

import copy
import json
from pathlib import Path

from auth_helpers import configure_test_access
from fastapi.testclient import TestClient

from app.authentication import require_authenticated_principal
from app.main import create_app
from app.principal import Principal

ROOT = Path(__file__).resolve().parents[2]
AGENT = json.loads((ROOT / "examples" / "agent-manifest-v1.json").read_text(encoding="utf-8"))


def make_client(tmp_path):
    app = configure_test_access(create_app(str(tmp_path / "cognitive-api.sqlite3")))
    client = TestClient(app)
    agent = copy.deepcopy(AGENT)
    agent["agent_id"] = "runtime.test"
    agent["tools"] = []
    response = client.post("/v1/agents", json={"manifest": agent})
    assert response.status_code == 201, response.text
    return app, client, f'{agent["agent_id"]}@{agent["version"]}'


def create_run(client, agent_ref, key="run-create-1"):
    return client.post(
        "/v1/cognitive-runs",
        headers={"Idempotency-Key": key},
        json={"goal_ref": "goal:lead-triage@1.0.0", "agent_ref": agent_ref},
    )


def test_cognitive_run_api_creates_immutable_agent_binding_and_is_idempotent(tmp_path):
    _, client, agent_ref = make_client(tmp_path)
    first = create_run(client, agent_ref)
    assert first.status_code == 201, first.text
    assert first.json()["created"] is True
    assert first.json()["run"]["agent_ref"] == agent_ref
    assert len(first.json()["run"]["agent_content_hash"]) == 64
    assert first.json()["initial_event"]["event_type"] == "intent.accepted"
    replay = create_run(client, agent_ref)
    assert replay.status_code == 201
    assert replay.json()["created"] is False
    assert replay.json()["run"]["run_id"] == first.json()["run"]["run_id"]


def test_cognitive_run_api_requires_immutable_existing_agent_version(tmp_path):
    _, client, _ = make_client(tmp_path)
    invalid = create_run(client, "runtime.test")
    assert invalid.status_code == 422
    missing = create_run(client, "runtime.test@9.9.9", "missing-run")
    assert missing.status_code == 404


def test_cognitive_event_api_enforces_order_idempotency_and_reads(tmp_path):
    _, client, agent_ref = make_client(tmp_path)
    created = create_run(client, agent_ref)
    run_id = created.json()["run"]["run_id"]
    headers = {"Idempotency-Key": "context-event-1"}
    payload = {
        "stage": "context",
        "event_type": "context.assembled",
        "payload": {"context_ref": "context:snapshot-1"},
    }
    first = client.post(f"/v1/cognitive-runs/{run_id}/events", headers=headers, json=payload)
    assert first.status_code == 201, first.text
    assert first.json()["created"] is True
    replay = client.post(f"/v1/cognitive-runs/{run_id}/events", headers=headers, json=payload)
    assert replay.status_code == 201
    assert replay.json()["created"] is False
    skipped = client.post(
        f"/v1/cognitive-runs/{run_id}/events",
        headers={"Idempotency-Key": "skip-event"},
        json={"stage": "execution", "event_type": "execution.started"},
    )
    assert skipped.status_code == 422
    fetched = client.get(f"/v1/cognitive-runs/{run_id}")
    assert fetched.status_code == 200
    assert fetched.json()["current_stage"] == "context"
    events = client.get(f"/v1/cognitive-runs/{run_id}/events")
    assert events.status_code == 200
    assert [item["sequence"] for item in events.json()["items"]] == [1, 2]


def test_cognitive_run_api_hides_runs_from_other_tenants(tmp_path):
    app, client, agent_ref = make_client(tmp_path)
    run_id = create_run(client, agent_ref).json()["run"]["run_id"]
    app.state.tenants.create("tenant-other", "Other Tenant", "test")
    app.state.tenants.transition("tenant-other", "active", "test")
    app.dependency_overrides[require_authenticated_principal] = lambda: Principal(
        "other-user", "user", "tenant-other"
    )
    response = client.get(f"/v1/cognitive-runs/{run_id}")
    assert response.status_code == 404


def test_cognitive_run_api_requires_idempotency_key(tmp_path):
    _, client, agent_ref = make_client(tmp_path)
    response = client.post(
        "/v1/cognitive-runs",
        json={"goal_ref": "goal:lead-triage@1.0.0", "agent_ref": agent_ref},
    )
    assert response.status_code == 422
