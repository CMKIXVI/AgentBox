# AgentBox provider execution worker

## Scope

The standalone worker is the first process that consumes durable execution jobs.
It supports only the trusted `provider_invocation` workload kind and exact
provider handler/version tuples already admitted by
`AGENTBOX_JOB_ALLOWED_HANDLERS`. It delegates model calls to the existing
`ExecutionService`; it does not execute manifest instructions as code.

`sandbox_workload` is deliberately rejected. The gVisor adapter is not yet
connected to this worker and no sandbox image is approved by this change.

## Run

Install the backend package and configure the API and worker to use the same
`AGENTBOX_DATABASE_PATH`. Configure the same exact
`AGENTBOX_JOB_ALLOWED_HANDLERS` JSON on both processes, and configure real
provider adapters/secrets before enabling non-test providers.

Start the API and worker as separate processes:

```sh
cd backend
AGENTBOX_DATABASE_PATH=/var/lib/agentbox/agentbox.sqlite3 \
  uvicorn app.main:app --host 127.0.0.1 --port 8000

AGENTBOX_DATABASE_PATH=/var/lib/agentbox/agentbox.sqlite3 \
AGENTBOX_WORKER_ID=worker-01 python -m app.worker
```

The worker uses `AGENTBOX_WORKER_ID` (generated if absent),
`AGENTBOX_WORKER_LEASE_SECONDS` (default 30; range 3–3600),
`AGENTBOX_WORKER_POLL_INTERVAL_SECONDS` (default 1; range 0.05–60), and
`AGENTBOX_WORKER_LOG_LEVEL` (default INFO). SIGINT/SIGTERM stop new polling
and allow the current synchronous provider call to return before exit.

## Execution and failure semantics

- The worker claims one job at a time and starts a lease heartbeat thread while
  the synchronous provider adapter is running.
- Before dispatch it verifies workload kind, handler allowlist, tenant-scoped
  registry lookup, immutable workload content hash, provider binding, empty
  tools list, and exact payload shape.
- Provider calls are recorded by the existing execution service with a
  job-and-attempt-scoped idempotency key.
- Provider errors are recorded as a bounded `provider_execution_failed`
  code; exception details are logged locally and are not returned to tenants.
- A lost lease prevents completion/failure writes. The durable recovery policy
  remains fail-closed for ambiguous running work; the worker does not blindly
  replay it.
- Cancellation is cooperative at the job boundary. A synchronous provider call
  cannot be forcibly interrupted by this worker; it confirms cancellation only
  after the call returns. Provider adapters must enforce their own timeout.

## Operational boundaries

This is a runnable single-instance worker process, not a production deployment
claim. SQLite remains single-instance storage; API and worker must share the
same local database file and host. No distributed queue, multi-host scheduling,
per-tenant concurrency quotas, worker autoscaling, sandbox execution, durable
provider idempotency guarantee, or production secret-management integration is
established. The fake provider is test-only. Live provider credentials,
network behavior, cancellation timing, restart/recovery, load, and deployment
security require separate integration and operational tests.
