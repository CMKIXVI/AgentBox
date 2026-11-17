from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from auth_helpers import configure_test_access
from fastapi.testclient import TestClient

from app.execution import DeterministicFakeProvider
from app.main import create_app
from app.worker import ExecutionJobWorker


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
    app = configure_test_access(create_app(str(tmp_path / "worker.sqlite3")))
    app.state.executions.providers["provider.fake"] = DeterministicFakeProvider()
    return TestClient(app)


def create_agent(client):
    root = Path(__file__).resolve().parents[2]
    manifest = json.loads((root / "examples" / "agent-manifest-v1.json").read_text())
    manifest["agent_id"] = "runtime.test"
    manifest["model_binding"]["provider_id"] = "provider.fake"
    manifest["tools"] = []
    response = client.post("/v1/agents", json={"manifest": manifest})
    assert response.status_code == 201


def submit(client, key="worker-test-job"):
    return client.post(
        "/v1/agents/runtime.test/versions/1.0.0/jobs",
        headers={"Idempotency-Key": key},
        json={"input": {"prompt": "hello"}, "max_output_tokens": 64},
    )


def make_worker(client, worker_id="test-worker"):
    state = client.app.state
    return ExecutionJobWorker(
        state.execution_jobs, state.registry, state.executions,
        worker_id=worker_id, lease_seconds=6, poll_interval_seconds=0.05,
    )


def test_worker_dispatches_registered_provider_job(client):
    create_agent(client)
    submitted = submit(client)
    assert submitted.status_code == 202

    worker = make_worker(client)
    assert worker.run_once() is True
    job = client.get(f"/v1/execution-jobs/{submitted.json()['job_id']}").json()
    assert job["state"] == "succeeded"
    assert job["result"]["execution"]["provider_id"] == "provider.fake"
    assert job["result"]["execution"]["output"]["input"] == {"prompt": "hello"}
    assert worker.run_once() is False


def test_worker_rejects_sandbox_workload(client):
    worker = make_worker(client)
    sandbox_job = {
        "workload_kind": "sandbox_workload",
        "handler_id": "sandbox.gvisor",
        "handler_version": "1.0.0",
    }
    with pytest.raises(ValueError, match="does not support"):
        worker._dispatch(sandbox_job)


def test_worker_fails_closed_when_workload_hash_changes(client):
    create_agent(client)
    submitted = submit(client, "worker-hash-test")
    job_id = submitted.json()["job_id"]
    with client.app.state.execution_jobs._connect() as connection:
        connection.execute(
            "UPDATE execution_jobs SET workload_hash=? WHERE job_id=?",
            (hashlib.sha256(b"tampered").hexdigest(), job_id),
        )
    assert make_worker(client).run_once() is True
    job = client.get(f"/v1/execution-jobs/{job_id}").json()
    assert job["state"] == "failed"
    assert job["error_code"] == "provider_execution_failed"
