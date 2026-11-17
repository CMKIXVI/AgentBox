from __future__ import annotations

import hashlib
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.execution_jobs import (
    DurableExecutionJobService,
    JobConflictError,
    JobLeaseError,
    JobNotFoundError,
)


@pytest.fixture
def jobs(tmp_path):
    return DurableExecutionJobService(
        tmp_path / "jobs.sqlite3",
        allowed_handlers={("provider_invocation", "provider.fake", "1.0.0")},
    )


def create(jobs, key="job-1", tenant="tenant-a"):
    return jobs.create(
        tenant_id=tenant, subject_id="user-1", principal_type="user",
        workload_kind="provider_invocation", handler_id="provider.fake",
        handler_version="1.0.0", workload_ref="agent-a@1.0.0",
        workload_hash=hashlib.sha256(b"artifact").hexdigest(),
        payload={"input": "hello"}, idempotency_key=key,
    )


def test_unregistered_handler_is_denied(jobs):
    with pytest.raises(JobConflictError):
        jobs.create(
            tenant_id="tenant-a", subject_id="user-1", principal_type="user",
            workload_kind="sandbox_workload", handler_id="arbitrary.handler",
            handler_version="1.0.0", workload_ref="artifact://untrusted",
            workload_hash=hashlib.sha256(b"artifact").hexdigest(),
            payload={}, idempotency_key="unregistered",
        )


def test_create_is_durable_and_appends_initial_event(jobs):
    record, created = create(jobs)
    assert created is True
    assert record["state"] == "queued"
    assert jobs.get(record["job_id"], "tenant-a")["job_id"] == record["job_id"]
    events = jobs.list_events(record["job_id"], "tenant-a")
    assert [(e["from_state"], e["to_state"]) for e in events] == [(None, "queued")]


def test_idempotent_replay_returns_original_job(jobs):
    first, created = create(jobs)
    second, replayed = create(jobs)
    assert created is True and replayed is False
    assert first["job_id"] == second["job_id"]


def test_idempotency_conflict_is_tenant_scoped(jobs):
    create(jobs)
    with pytest.raises(JobConflictError):
        jobs.create(
            tenant_id="tenant-a", subject_id="user-1", principal_type="user",
            workload_kind="provider_invocation", handler_id="provider.fake",
            handler_version="1.0.0", workload_ref="agent-a@1.0.0",
            workload_hash=hashlib.sha256(b"artifact").hexdigest(),
            payload={"input": "different"}, idempotency_key="job-1",
        )
    other, created = create(jobs, tenant="tenant-b")
    assert created and other["tenant_id"] == "tenant-b"


def test_claim_is_atomic_under_competing_workers(jobs):
    create(jobs)
    with ThreadPoolExecutor(max_workers=8) as pool:
        claims = list(pool.map(lambda worker: jobs.claim(worker), [f"w-{i}" for i in range(8)]))
    successful = [claim for claim in claims if claim is not None]
    assert len(successful) == 1


def test_worker_lifecycle_and_lease_token_fencing(jobs):
    record, _ = create(jobs)
    claim = jobs.claim("worker-1")
    assert claim["job_id"] == record["job_id"]
    running = jobs.start(record["job_id"], "tenant-a", "worker-1", claim["lease_token"])
    assert running["state"] == "running"
    with pytest.raises(JobLeaseError):
        jobs.complete(record["job_id"], "tenant-a", "worker-2", claim["lease_token"], {"ok": True})
    done = jobs.complete(record["job_id"], "tenant-a", "worker-1", claim["lease_token"], {"ok": True})
    assert done["state"] == "succeeded"
    assert done["result"] == {"ok": True}
    with pytest.raises(JobLeaseError):
        jobs.start(record["job_id"], "tenant-a", "worker-1", claim["lease_token"])


def test_cross_tenant_get_is_not_found(jobs):
    record, _ = create(jobs)
    with pytest.raises(JobNotFoundError):
        jobs.get(record["job_id"], "tenant-b")


def test_cancellation_is_request_then_confirmation(jobs):
    record, _ = create(jobs)
    requested = jobs.request_cancel(record["job_id"], "tenant-a", "user-1")
    assert requested["state"] == "cancel_requested"
    cancelled = jobs.confirm_cancel(record["job_id"], "tenant-a", "supervisor")
    assert cancelled["state"] == "cancelled"


def test_worker_must_own_lease_to_confirm_running_cancellation(jobs):
    record, _ = create(jobs)
    claim = jobs.claim("worker-1")
    jobs.start(record["job_id"], "tenant-a", "worker-1", claim["lease_token"])
    jobs.request_cancel(record["job_id"], "tenant-a", "user-1")
    with pytest.raises(JobLeaseError):
        jobs.confirm_cancel(record["job_id"], "tenant-a", "worker-2")
    assert jobs.confirm_cancel(
        record["job_id"], "tenant-a", "worker-1", "worker-1", claim["lease_token"]
    )["state"] == "cancelled"


def test_expired_lease_before_start_is_requeued(jobs):
    record, _ = create(jobs)
    jobs.claim("worker-1", lease_seconds=1)
    with jobs._connect() as connection:
        connection.execute(
            "UPDATE execution_jobs SET lease_expires_at='2000-01-01T00:00:00+00:00' WHERE job_id=?",
            (record["job_id"],),
        )
    assert jobs.recover_expired_leases() == {
        "requeued_leased": 1, "failed_ambiguous_running": 0,
    }
    assert jobs.get(record["job_id"], "tenant-a")["state"] == "queued"
    reclaimed = jobs.claim("worker-2")
    assert reclaimed is not None
    assert reclaimed["job_id"] == record["job_id"]
    assert jobs.start(
        record["job_id"], "tenant-a", "worker-2", reclaimed["lease_token"]
    )["attempt"] == 1


def test_expired_running_job_fails_closed_without_replay(jobs):
    record, _ = create(jobs)
    claim = jobs.claim("worker-1", lease_seconds=1)
    jobs.start(record["job_id"], "tenant-a", "worker-1", claim["lease_token"])
    with jobs._connect() as connection:
        connection.execute(
            "UPDATE execution_jobs SET lease_expires_at='2000-01-01T00:00:00+00:00' WHERE job_id=?",
            (record["job_id"],),
        )
    assert jobs.recover_expired_leases()["failed_ambiguous_running"] == 1
    failed = jobs.get(record["job_id"], "tenant-a")
    assert failed["state"] == "failed"
    assert failed["error_code"] == "worker_lost_ambiguous_outcome"
    assert jobs.claim("worker-2") is None


def test_events_are_append_only(jobs):
    record, _ = create(jobs)
    with pytest.raises(sqlite3.IntegrityError), jobs._connect() as connection:
        connection.execute(
            "UPDATE execution_job_events SET reason_code='tampered' WHERE job_id=?",
            (record["job_id"],),
        )
    with pytest.raises(sqlite3.IntegrityError), jobs._connect() as connection:
        connection.execute(
            "DELETE FROM execution_job_events WHERE job_id=?", (record["job_id"],)
        )


def test_payload_and_result_limits(jobs):
    with pytest.raises(ValueError):
        jobs.create(
            tenant_id="tenant-a", subject_id="user-1", principal_type="user",
            workload_kind="provider_invocation", handler_id="provider.fake",
            handler_version="1.0.0", workload_ref="agent-a@1.0.0",
            workload_hash=hashlib.sha256(b"artifact").hexdigest(),
            payload={"large": "x" * (300 * 1024)}, idempotency_key="large",
        )
    create(jobs)
    claim = jobs.claim("worker-1")
    jobs.start(claim["job_id"], "tenant-a", "worker-1", claim["lease_token"])
    with pytest.raises(ValueError):
        jobs.complete(
            claim["job_id"], "tenant-a", "worker-1", claim["lease_token"],
            {"large": "x" * (70 * 1024)},
        )
