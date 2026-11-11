from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.execution import DeterministicFakeProvider
from app.main import create_app


def manifest():
    path = __import__("pathlib").Path(__file__).resolve().parents[2] / "examples" / "agent-manifest-v1.json"
    value = json.loads(path.read_text())
    value["agent_id"] = "runtime.test"
    value["model_binding"]["provider_id"] = "provider.fake"
    value["tools"] = []
    return value


@pytest.fixture
def client(tmp_path):
    app = create_app(str(tmp_path / "runtime.sqlite3"))
    app.state.executions.providers["provider.fake"] = DeterministicFakeProvider()
    return TestClient(app)


def create_agent(client):
    response = client.post("/v1/agents", json={"manifest": manifest()})
    assert response.status_code == 201
    return "runtime.test", "1.0.0"


def test_execute_persists_output_and_usage(client):
    agent_id, version = create_agent(client)
    response = client.post(
        f"/v1/agents/{agent_id}/versions/{version}/executions",
        headers={"Idempotency-Key": "exec-1"},
        json={"input": {"question": "hello"}, "max_output_tokens": 128},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed"
    assert body["result"]["output"]["input"] == {"question": "hello"}
    assert body["result"]["steps"] == 1
    fetched = client.get(f"/v1/executions/{body['execution_id']}")
    assert fetched.json() == body


def test_idempotency_returns_same_execution(client):
    agent_id, version = create_agent(client)
    url = f"/v1/agents/{agent_id}/versions/{version}/executions"
    headers = {"Idempotency-Key": "same-key"}
    first = client.post(url, headers=headers, json={"input": "x"}).json()
    second = client.post(url, headers=headers, json={"input": "x"}).json()
    assert first["execution_id"] == second["execution_id"]


def test_idempotency_conflict_rejected(client):
    agent_id, version = create_agent(client)
    url = f"/v1/agents/{agent_id}/versions/{version}/executions"
    headers = {"Idempotency-Key": "same-key"}
    assert client.post(url, headers=headers, json={"input": "x"}).status_code == 201
    assert client.post(url, headers=headers, json={"input": "different"}).status_code == 409


def test_tool_enabled_agent_denied(client):
    value = manifest()
    value["tools"] = [{
        "tool_id": "tool.example", "version_range": "^1.0.0",
        "permission_profile": "read-only"
    }]
    assert client.post("/v1/agents", json={"manifest": value}).status_code == 201
    response = client.post(
        "/v1/agents/runtime.test/versions/1.0.0/executions",
        headers={"Idempotency-Key": "tool-deny"},
        json={"input": "x"},
    )
    assert response.status_code == 403


def test_unknown_provider_denied(client):
    value = manifest()
    value["model_binding"]["provider_id"] = "provider.not-configured"
    assert client.post("/v1/agents", json={"manifest": value}).status_code == 201
    response = client.post(
        "/v1/agents/runtime.test/versions/1.0.0/executions",
        headers={"Idempotency-Key": "no-provider"},
        json={"input": "x"},
    )
    assert response.status_code == 503


def test_execution_limits_validated(client):
    agent_id, version = create_agent(client)
    response = client.post(
        f"/v1/agents/{agent_id}/versions/{version}/executions",
        headers={"Idempotency-Key": "bad-limit"},
        json={"input": "x", "max_output_tokens": 90000},
    )
    assert response.status_code == 422


def test_execution_not_found(client):
    assert client.get("/v1/executions/not-real").status_code == 404
