from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from auth_helpers import configure_test_access
from app.execution import DeterministicFakeProvider
from app.main import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "AGENTBOX_JOB_ALLOWED_HANDLERS",
        json.dumps([{
            "workload_kind": "provider_invocation",
            "handler_id": "provider.fake",
            "handler_version": "1.0.0",
        }]),
    )
    monkeypatch.setenv("AGENTBOX_JOB_WORKER_TOKEN", "test-worker-secret")
    app = configure_test_access(create_app(str(tmp_path / "jobs-api.sqlite3")))
    app.state.executions.providers["provider.fake"] = DeterministicFakeProvider()
    return TestClient(app)


def create_agent(client):
    path = __import__("pathlib").Path(__file__).resolve().parents[2]
    value = json.loads((path / "examples" / "agent-manifest-v1.json").read_text())
    value["agent_id"] = "runtime.test"
    value["model_binding"]["provider_id"] = "provider.fake"
    value["tools"] = []
    response = client.post("/v1/agents", json={"manifest": value})
    assert response.status_code == 201
    return "runtime.test", "1.0.0"


def submit_job(client, key="job-api-1"):
    agent_id, version = "runtime.test", "1.0.0"
    return client.post(
        f"/v1/agents/{agent_id}/versions/{version}/jobs",
        headers={"Idempotency-Key": key},
        json={"input": {"question": "hello"}, "max_output_tokens": 64},
    )


def worker_headers():
    return {"Authorization": "Bearer test-worker-secret"}


def test_submit_job_is_tenant_scoped_and_idempotent(client):
    create_agent(client)
    first = submit_job(client)
    assert first.status_code == 202
    assert first.json()["state"] == "queued"
    assert first.json()["created"] is True
    second = submit_job(client)
    assert second.status_code == 202
    assert second.json()["job_id"] == first.json()["job_id"]
    assert second.json()["created"] is False
    fetched = client.get(f"/v1/execution-jobs/{first.json()['job_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["tenant_id"] == "test-tenant"


def test_worker_lifecycle_requires_dedicated_secret(client):
    create_agent(client)
    job = submit_job(client).json()
    denied = client.post(
        "/internal/v1/execution-jobs/claim",
        json={"worker_id": "worker-1"},
    )
    assert denied.status_code == 401

    claim_response = client.post(
        "/internal/v1/execution-jobs/claim",
        headers=worker_headers(),
        json={"worker_id": "worker-1", "lease_seconds": 60},
    )
    assert claim_response.status_code == 200
    claim = claim_response.json()["job"]
    assert claim["job_id"] == job["job_id"]
    lease = {
        "tenant_id": "test-tenant",
        "worker_id": "worker-1",
        "lease_token": claim["lease_token"],
    }
    started = client.post(
        f"/internal/v1/execution-jobs/{job['job_id']}/start",
        headers=worker_headers(),
        json=lease,
    )
    assert started.status_code == 200
    completed = client.post(
        f"/internal/v1/execution-jobs/{job['job_id']}/complete",
        headers=worker_headers(),
        json={**lease, "result": {"answer": "done"}},
    )
    assert completed.status_code == 200
    assert completed.json()["state"] == "succeeded"


def test_cancel_is_a_request_until_worker_confirms(client):
    create_agent(client)
    job = submit_job(client).json()
    requested = client.post(f"/v1/execution-jobs/{job['job_id']}/cancel")
    assert requested.status_code == 200
    assert requested.json()["state"] == "cancel_requested"
    confirmed = client.post(
        f"/internal/v1/execution-jobs/{job['job_id']}/cancelled",
        headers=worker_headers(),
        json={"tenant_id": "test-tenant", "actor_id": "worker-supervisor"},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["state"] == "cancelled"


def test_unconfigured_worker_auth_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTBOX_JOB_ALLOWED_HANDLERS", "[]")
    monkeypatch.delenv("AGENTBOX_JOB_WORKER_TOKEN", raising=False)
    app = configure_test_access(create_app(str(tmp_path / "no-worker-secret.sqlite3")))
    response = TestClient(app).post(
        "/internal/v1/execution-jobs/claim",
        headers={"Authorization": "Bearer anything"},
        json={"worker_id": "worker-1"},
    )
    assert response.status_code == 503
