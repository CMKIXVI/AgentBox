# Durable execution-job lifecycle

**Status:** implementation contract; not a claim of a deployed queue or worker  
**Scope:** asynchronous, tenant-owned work items, including opt-in sandbox workloads  
**Architecture boundary:** additive to the existing synchronous provider invocation path

## 1. Purpose and separation

AgentBox currently has a synchronous provider invocation service with execution records. A
sandbox runner is a low-level process adapter. Neither is a durable job scheduler.

Introduce a separate job lifecycle service. It owns admission, durable state transitions,
worker leases, cancellation requests, recovery and job-to-audit correlation. It does not
execute model calls itself and must not turn ordinary model invocations into arbitrary
code execution.

Initial workload kinds are explicit and allowlisted:

- `provider_invocation`: a bounded provider task delegated to an approved handler.
- `sandbox_workload`: an immutable, digest-pinned workload delegated to the gVisor adapter.

A job handler is selected by trusted server configuration, never by a client-supplied
module path, shell command, runtime name, image, or arbitrary URL. The sandbox kind is
unavailable unless the deployment has a healthy, approved gVisor worker.

## 2. State machine

Allowed states:

`queued → leased → running → succeeded | failed | cancelled | timed_out`

Additional recovery transitions:

- `leased → queued` when an expired lease is safely reclaimed before execution starts.
- `running → queued` only when the handler declares the operation idempotent and its
  execution attempt is known not to have produced an externally visible side effect.
- `running → failed` when outcome is ambiguous after worker loss; never blindly replay.
- `queued | leased | running → cancel_requested` for cooperative cancellation.
- `cancel_requested → cancelled` only after the worker confirms termination or the
  supervisor proves the workload is no longer running.
- `cancel_requested → succeeded | failed | timed_out` when completion wins the race and
  the terminal outcome is confirmed.

Terminal states are immutable. All transitions use compare-and-set against the expected
current state and append a transition event in the same database transaction.

## 3. Durable job envelope

Every record contains:

- globally unique `job_id`
- `tenant_id`, `subject_id`, and authenticated principal type
- workload kind and registered handler ID/version
- immutable workload reference and SHA-256 content hash
- canonical request hash and tenant-scoped idempotency key
- state, attempt number, max attempts, priority and enqueue timestamp
- `available_at`, lease owner, lease token, lease expiry and heartbeat timestamp
- created, started, completed and updated timestamps
- bounded result reference or structured error code (never unbounded stdout/stderr)
- cancellation request timestamp and reason code
- correlation ID plus authorization-decision and audit-event references

Persist only the minimum request data needed for execution. Sensitive input belongs in
an approved encrypted payload store and must not be copied into logs or audit metadata.
Secrets are resolved by a trusted handler at execution time, not embedded in the job
payload or returned to clients.

## 4. Admission and isolation

Admission is server-side and deny-by-default:

1. Authenticate principal and resolve the active tenant from server-owned identity.
2. Authorize the workload-specific submit action against the exact agent/workload resource.
3. Validate registered handler, workload kind, immutable artifact hash and policy version.
4. Enforce per-tenant queued-job, running-job, payload-size and rate limits.
5. Require a tenant-scoped idempotency key. Same key + same canonical request returns
   the original job; same key + different request returns conflict.
6. Write the job, initial transition event and audit correlation atomically.
7. Return a job identifier and current server-owned state; do not execute inline.

No client may select worker identity, Docker runtime, host path, environment allowlist,
network mode, image pull policy, or resource limits.

## 5. Worker lease and bounded execution

Workers claim jobs transactionally using a short lease and unique lease token. A worker
must renew its lease with heartbeats. Every state mutation verifies the lease token,
preventing a stale worker from completing a job after another worker has reclaimed it.

Concurrency is bounded globally and per tenant. Queue admission and worker concurrency
are separate controls. The first implementation may use a database-backed queue and
single worker process; it must not claim multi-host throughput or exactly-once execution.

At-least-once delivery is the realistic queue guarantee. Handlers must declare idempotency
and side-effect behavior. External side effects require an idempotency key or an explicit
reconciliation strategy. Never describe the system as exactly-once.

## 6. Cancellation and timeouts

Cancellation is a durable request, not an immediate assertion that execution stopped.
Workers check cancellation between safe steps. For sandbox workloads, the supervisor
must terminate the specific container/process group and confirm cleanup before marking
the job cancelled. A hard timeout is enforced outside the workload process.

The API reports `cancel_requested` until termination is confirmed. If completion races
with cancellation, the confirmed terminal outcome wins and is recorded with timestamps.

## 7. Restart recovery

On startup, the worker reconciles expired leases:

- queued jobs remain eligible.
- expired leased jobs may be requeued because execution has not been acknowledged.
- expired running jobs are treated as ambiguous by default and moved to failed with
  `worker_lost_ambiguous_outcome`.
- a narrowly approved idempotent handler may opt into retry after a handler-specific
  recovery check proves no side effect occurred.
- cancellation requests are reconciled against the supervisor before terminalization.

Recovery decisions append immutable transition/audit events. No startup routine silently
resets all running jobs to queued.

## 8. Audit and tenant isolation

Every state transition records job ID, tenant ID, actor/worker identity, previous state,
new state, reason code, attempt, lease token fingerprint, timestamp and correlation ID.
Do not persist raw lease tokens or secrets in the audit stream.

Job reads, cancellation, retry and result access are tenant-scoped and independently
authorized. Cross-tenant lookup must return not-found semantics. Audit records are
append-only; job state is mutable only through validated transitions.

## 9. Persistence and migration

The first adapter may use the existing SQLite database in single-instance mode. Define
tables for jobs, transition events and tenant-scoped idempotency. Use foreign-key and
uniqueness constraints where supported, explicit indexes for claim and tenant queries,
and transactional compare-and-set updates.

A later PostgreSQL adapter must preserve the same service contract and state semantics.
Do not claim horizontal worker safety from SQLite. Add new tenant-owned tables to backup,
restore, retention and migration inventories before enabling the service in production.

## 10. Required acceptance tests

- valid and invalid state transitions, including immutable terminal states
- concurrent claim attempts and stale lease-token rejection
- tenant isolation for get/list/cancel/result and idempotency
- same-key replay and same-key/different-request conflict
- bounded admission and per-tenant/global concurrency
- cancellation request vs confirmed termination semantics
- lease expiry before start vs worker loss after start
- ambiguous outcome is not blindly replayed
- handler opt-in retry only after positive recovery proof
- atomic job + initial event + audit correlation
- restart recovery and duplicate worker heartbeat races
- bounded payload/result/error handling and secret redaction

## 11. Release gates

The job lifecycle is not production-ready until a deployed worker proves queue admission,
lease ownership, bounded concurrency, cancellation, restart recovery, tenant isolation,
audit integrity, monitoring, backup/restore and failure handling. Live sandbox tests must
add network/filesystem isolation, resource limits, timeout cleanup and image provenance.
