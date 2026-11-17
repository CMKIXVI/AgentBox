"""Dedicated worker for trusted AgentBox provider-invocation jobs.

This process dispatches only explicitly registered provider handlers. It does not
interpret agent manifests as code and intentionally rejects sandbox workloads.
"""
from __future__ import annotations

import logging
import os
import signal
import threading
import uuid
from typing import Any

from .execution import ExecutionService
from .execution_jobs import DurableExecutionJobService, JobLeaseError
from .registry import AgentRegistry

LOGGER = logging.getLogger("agentbox.worker")


class ExecutionJobWorker:
    """Single-job-at-a-time worker using the durable job service as its authority."""

    def __init__(
        self,
        jobs: DurableExecutionJobService,
        registry: AgentRegistry,
        executions: ExecutionService,
        *,
        worker_id: str | None = None,
        lease_seconds: int = 30,
        poll_interval_seconds: float = 1.0,
    ) -> None:
        if not 3 <= lease_seconds <= 3600:
            raise ValueError("lease_seconds must be between 3 and 3600")
        if not 0.05 <= poll_interval_seconds <= 60:
            raise ValueError("poll_interval_seconds must be between 0.05 and 60")
        self.jobs = jobs
        self.registry = registry
        self.executions = executions
        self.worker_id = worker_id or f"worker-{uuid.uuid4()}"
        if not self.worker_id or len(self.worker_id) > 128:
            raise ValueError("worker_id must be between 1 and 128 characters")
        self.lease_seconds = lease_seconds
        self.poll_interval_seconds = poll_interval_seconds

    def run_once(self) -> bool:
        """Claim and process at most one job; return False when the queue is empty."""
        claim = self.jobs.claim(self.worker_id, self.lease_seconds)
        if claim is None:
            return False

        job_id = claim["job_id"]
        tenant_id = claim["tenant_id"]
        lease_token = claim["lease_token"]
        lease = {
            "job_id": job_id,
            "tenant_id": tenant_id,
            "worker_id": self.worker_id,
            "lease_token": lease_token,
        }
        try:
            started = self.jobs.start(job_id, tenant_id, self.worker_id, lease_token)
            claim["attempt"] = started["attempt"]
        except JobLeaseError:
            LOGGER.warning("Worker lost lease before start for job %s", job_id)
            return True

        stop_heartbeat = threading.Event()
        cancel_requested = threading.Event()
        lease_lost = threading.Event()
        heartbeat_thread = threading.Thread(
            target=self._maintain_lease,
            args=(lease, stop_heartbeat, cancel_requested, lease_lost),
            name=f"agentbox-heartbeat-{job_id}",
            daemon=True,
        )
        heartbeat_thread.start()
        try:
            result = self._dispatch(claim)
            if lease_lost.is_set():
                LOGGER.warning(
                    "Lease lost during execution for job %s; leaving outcome for recovery",
                    job_id,
                )
                return True
            current = self.jobs.get(job_id, tenant_id)
            if cancel_requested.is_set() or current["state"] == "cancel_requested":
                self.jobs.confirm_cancel(
                    job_id, tenant_id, self.worker_id, self.worker_id, lease_token
                )
                return True
            self.jobs.complete(job_id, tenant_id, self.worker_id, lease_token, result)
        except JobLeaseError:
            LOGGER.warning("Lease lost while finalizing job %s; leaving outcome for recovery", job_id)
        except Exception:
            LOGGER.exception("Trusted handler failed for job %s", job_id)
            if not lease_lost.is_set():
                if cancel_requested.is_set():
                    try:
                        self.jobs.confirm_cancel(
                            job_id, tenant_id, self.worker_id, self.worker_id, lease_token
                        )
                    except JobLeaseError:
                        LOGGER.warning("Could not confirm cancellation for job %s", job_id)
                else:
                    try:
                        self.jobs.fail(
                            job_id, tenant_id, self.worker_id, lease_token,
                            "provider_execution_failed",
                        )
                    except JobLeaseError:
                        LOGGER.warning("Could not record failure after lease loss for job %s", job_id)
        finally:
            stop_heartbeat.set()
            # Do not let shutdown close the job store while heartbeat I/O is
            # still in flight; SQLite may legitimately wait up to busy_timeout.
            heartbeat_thread.join()
        return True

    def _maintain_lease(
        self,
        lease: dict[str, str],
        stop: threading.Event,
        cancel_requested: threading.Event,
        lease_lost: threading.Event,
    ) -> None:
        interval = max(0.5, self.lease_seconds / 3)
        while not stop.wait(interval):
            try:
                self.jobs.heartbeat(
                    lease["job_id"], lease["tenant_id"], self.worker_id,
                    lease["lease_token"], self.lease_seconds,
                )
                current = self.jobs.get(lease["job_id"], lease["tenant_id"])
                if current["state"] == "cancel_requested":
                    # Provider adapters are synchronous; do not claim termination until
                    # the invocation returns and this worker can safely confirm it.
                    cancel_requested.set()
            except Exception:
                lease_lost.set()
                LOGGER.exception("Lease heartbeat failed for job %s", lease["job_id"])
                return

    def _dispatch(self, job: dict[str, Any]) -> dict[str, Any]:
        if job["workload_kind"] != "provider_invocation":
            raise ValueError("worker does not support this workload kind")
        allowed = {
            (provider_id, version)
            for kind, provider_id, version in self.jobs.allowed_handlers
            if kind == "provider_invocation"
        }
        if (job["handler_id"], job["handler_version"]) not in allowed:
            raise ValueError("provider handler is not in the trusted allowlist")

        agent_id, separator, version = job["workload_ref"].rpartition("@")
        if not separator or not agent_id or not version:
            raise ValueError("workload reference is invalid")
        artifact = self.registry.get(agent_id, version, job["tenant_id"])
        if artifact.content_hash != job["workload_hash"]:
            raise ValueError("registered workload hash does not match admitted job")
        binding = artifact.manifest.get("model_binding", {})
        if binding.get("provider_id") != job["handler_id"]:
            raise ValueError("manifest provider does not match the admitted handler")
        if artifact.manifest.get("tools"):
            raise ValueError("tool-enabled manifests are not supported by this worker")
        payload = job.get("payload")
        if not isinstance(payload, dict) or set(payload) != {"input", "max_output_tokens"}:
            raise ValueError("provider job payload is invalid")

        execution = self.executions.execute(
            agent_id,
            version,
            payload["input"],
            idempotency_key=f"job:{job['job_id']}:attempt:{job['attempt']}",
            max_output_tokens=payload["max_output_tokens"],
            tenant_id=job["tenant_id"],
        )
        return {
            "execution_id": execution["execution_id"],
            "execution": execution["result"],
        }

    def run_forever(self, stop_event: threading.Event | None = None) -> None:
        """Poll until stopped; in-flight work is allowed to finish."""
        stop = stop_event or threading.Event()
        while not stop.is_set():
            if not self.run_once():
                stop.wait(self.poll_interval_seconds)


def main() -> None:
    """Start the standalone worker using the same configured SQLite database as the API."""
    import logging

    logging.basicConfig(
        level=os.getenv("AGENTBOX_WORKER_LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    from .main import create_app

    app = create_app()
    worker = ExecutionJobWorker(
        app.state.execution_jobs,
        app.state.registry,
        app.state.executions,
        worker_id=os.getenv("AGENTBOX_WORKER_ID") or None,
        lease_seconds=int(os.getenv("AGENTBOX_WORKER_LEASE_SECONDS", "30")),
        poll_interval_seconds=float(os.getenv("AGENTBOX_WORKER_POLL_INTERVAL_SECONDS", "1")),
    )
    stop = threading.Event()

    def request_shutdown(signum: int, frame: Any) -> None:
        del signum, frame
        LOGGER.info("Shutdown requested; waiting for current job to finish")
        stop.set()

    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(signal.SIGTERM, request_shutdown)
    LOGGER.info("Starting worker %s", worker.worker_id)
    try:
        worker.run_forever(stop)
    finally:
        app.state.close_stores()
        LOGGER.info("Worker %s stopped", worker.worker_id)


if __name__ == "__main__":
    main()
