from __future__ import annotations

import hashlib
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from threading import Event

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


def test_worker_executes_openai_provider_job_through_mocked_http(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "AGENTBOX_JOB_ALLOWED_HANDLERS",
        json.dumps([{
            "workload_kind": "provider_invocation",
            "handler_id": "provider.openai",
            "handler_version": "1.0.0",
        }]),
    )
    monkeypatch.setenv("AGENTBOX_OPENAI_API_KEY", "test-only-secret")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AGENTBOX_OPENAI_INPUT_USD_PER_MILLION", raising=False)
    monkeypatch.delenv("AGENTBOX_OPENAI_OUTPUT_USD_PER_MILLION", raising=False)

    class MockHTTPResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self, _size=-1):
            return json.dumps({
                "choices": [{"message": {"content": "worker provider result"}}],
                "usage": {"prompt_tokens": 11, "completion_tokens": 4},
            }).encode()

    monkeypatch.setattr(
        "app.openai_provider.urlopen",
        lambda *_args, **_kwargs: MockHTTPResponse(),
    )
    app = configure_test_access(create_app(str(tmp_path / "openai-worker.sqlite3")))
    client = TestClient(app)

    root = Path(__file__).resolve().parents[2]
    manifest = json.loads((root / "examples" / "agent-manifest-v1.json").read_text())
    manifest["agent_id"] = "runtime.test"
    manifest["model_binding"]["provider_id"] = "provider.openai"
    manifest["tools"] = []
    created = client.post("/v1/agents", json={"manifest": manifest})
    assert created.status_code == 201

    submitted = client.post(
        "/v1/agents/runtime.test/versions/1.0.0/jobs",
        headers={"Idempotency-Key": "openai-worker-integration"},
        json={"input": {"prompt": "hello from durable worker"}, "max_output_tokens": 48},
    )
    assert submitted.status_code == 202

    state = client.app.state
    worker = ExecutionJobWorker(
        state.execution_jobs, state.registry, state.executions,
        worker_id="openai-test-worker", lease_seconds=6, poll_interval_seconds=0.05,
    )
    assert worker.run_once() is True

    job = client.get(f"/v1/execution-jobs/{submitted.json()['job_id']}").json()
    assert job["state"] == "succeeded"
    execution = job["result"]["execution"]
    assert execution["provider_id"] == "provider.openai"
    assert execution["output"] == "worker provider result"
    assert execution["usage"]["input_tokens"] == 11
    assert execution["usage"]["output_tokens"] == 4
    assert execution["usage"]["cost_usd"] is None

def test_worker_waits_for_heartbeat_thread_before_returning(client):
    create_agent(client)
    submitted = submit(client, "worker-heartbeat-shutdown")
    worker = make_worker(client)
    heartbeat_started = Event()
    release_heartbeat = Event()

    def blocked_heartbeat(_lease, _stop, _cancel_requested, _lease_lost):
        heartbeat_started.set()
        release_heartbeat.wait(timeout=5)

    worker._maintain_lease = blocked_heartbeat
    with ThreadPoolExecutor(max_workers=1) as executor:
        result = executor.submit(worker.run_once)
        assert heartbeat_started.wait(timeout=2)
        assert result.done() is False
        release_heartbeat.set()
        assert result.result(timeout=3) is True

    job = client.get(f"/v1/execution-jobs/{submitted.json()['job_id']}").json()
    assert job["state"] == "succeeded"

