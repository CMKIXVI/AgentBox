# AgentBox backend

Python 3.11+ / FastAPI service. The backend is frontend-independent and exposes an OpenAPI-described HTTP API.

## Run locally

From this directory:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload
```

The default SQLite database is stored at `backend/data/agentbox.sqlite3`. Override it with `AGENTBOX_DATABASE_PATH`. The API loads its authoritative schemas from `../schemas/`; override the paths with `AGENTBOX_SCHEMA_PATH` and `AGENTBOX_EVALUATION_SCHEMA_PATH` if required.

## Agent registry API

- `GET /health` — service health.
- `POST /v1/agents/validate` — validate a manifest without storing it.
- `POST /v1/agents` — validate and create an immutable agent version.
- `GET /v1/agents/{agent_id}/versions` — list versions.
- `GET /v1/agents/{agent_id}/versions/{version}` — retrieve a version.
- `POST /v1/agents/{agent_id}/versions/{version}/clone` — create a derived version with parent lineage. Optional `overrides` apply a schema-validated deep merge to mutable manifest sections; identity and provenance cannot be overridden.

## Evaluation API

- `POST /v1/evaluation-profiles/validate` — validate an evaluation profile, scoring weights, case IDs and embedded assertion schemas.
- `POST /v1/evaluation-profiles` — create an immutable profile version.
- `GET /v1/evaluation-profiles/{profile_id}/versions` — list profile versions.
- `GET /v1/evaluation-profiles/{profile_id}/versions/{profile_version}` — retrieve a profile version.
- `POST /v1/agents/{agent_id}/versions/{version}/evaluations` — evaluate submitted per-case outputs and measurements against a profile.
- `GET /v1/evaluations/{run_id}` — retrieve a persisted evaluation result.
- `GET /v1/agents/{agent_id}/versions/{version}/evaluations` — list evaluation runs for an agent version.

Evaluation assertions supported in v1: `exact_match`, `contains`, `required_fields`, and `json_schema_valid`. The scoring profile weights correctness, latency and cost. Promotion gates independently enforce minimum case pass rate, maximum average latency and maximum total cost.

## Evaluation boundary — important

The original `POST /v1/agents/{agent_id}/versions/{version}/evaluations` submission endpoint does **not** execute an agent or call a model; it scores caller-submitted outputs and measurements and labels those runs `caller_submitted`. The separate `/evaluations/execute` endpoint executes pinned profile inputs through the server-configured provider, persists per-case execution records, and labels the run `server_recorded` only after checking the execution evidence. Missing case outputs count as failures; duplicate or unknown case IDs are rejected.

Evaluation success is an eligibility signal, not an automatic publish/deploy action. Execution-backed evaluation is currently synchronous and limited to agents without declared tools. Durable batch orchestration, production database migration/backup procedures, live provider validation and production deployment controls remain outstanding.

Interactive API documentation is available at `/docs`; the OpenAPI document is at `/openapi.json`.

## Persistence

SQLite is currently intended for local development and early tests. It is not yet a multi-instance production persistence layer.


## Agent execution runtime v1

- `POST /v1/agents/{agent_id}/versions/{version}/executions` — invoke a configured provider adapter for an immutable agent version. Requires an `Idempotency-Key` header; request body accepts `input` and bounded `max_output_tokens`.
- `GET /v1/executions/{execution_id}` — retrieve persisted execution state and result.

The first vertical slice is intentionally narrow: it performs one provider invocation, records status/result/usage, and ships with a deterministic fake provider for integration tests. The fake provider is the only adapter registered by default. Live providers require an explicitly installed adapter and a separate secret-resolution facility; credential references are never resolved or persisted by this service.

**Security boundary:** manifests with any declared tools are denied (HTTP 403) until a principal-aware tool registry and authorization enforcement exist. Agent instructions are treated as data, never executed as Python, JavaScript, shell, or other host code. The adapter contract requires the adapter itself to enforce the supplied timeout. This initial synchronous request path is not a durable worker queue, cannot guarantee interruption of a misbehaving adapter, and has no authentication or tenant isolation. SQLite remains a single-instance development store.


## Enterprise Context Engine foundation

The Enterprise Context Engine is an additive, tenant-scoped metadata and relationship layer over the existing AgentBox SQLite database. It reuses OIDC authentication, active-tenant enforcement and exact-match authorization. Its v1 API supports immutable entity versions, typed relationships, evidence references, bounded queries and append-only context events.

See [Enterprise Context architecture map](../docs/enterprise-context-architecture-map.md) for the existing-module mapping, scope boundaries and implementation sequence. ECE does not yet include external discovery connectors, a natural-language reasoning agent, a workflow interpreter or a production action gateway. The current API routes are under `/v1/enterprise-context`; grants use capability ID `enterprise.context` and explicit context actions.


## Trusted capability worker adapter

Capability invocation requests are admitted to the durable queue only when the API deployment binds the exact `capability_id@version` to an exact handler tuple in `AGENTBOX_CAPABILITY_HANDLERS`; that tuple must also appear in `AGENTBOX_JOB_ALLOWED_HANDLERS`. The request cannot choose a handler.

The worker dispatches capability jobs only through reviewed Python callables registered in `app.worker.CAPABILITY_HANDLERS`, keyed by `(handler_id, handler_version)`. Add a handler in trusted application code and pass the same mapping to `ExecutionJobWorker`; the standalone worker entrypoint uses this static registry. The registry is empty by default, so capability jobs fail closed until a handler is installed. Never import or execute a contract's `implementation_ref`, and never load Python module paths from job payloads or environment variables.

Each handler receives an immutable context (tenant, subject, capability version, contract hash and declared timeout) plus the validated input. The worker independently reloads the tenant-owned immutable contract, checks its content hash, revalidates input, and validates handler output against the contract's output schema before completing the job. Handler implementations must enforce the supplied timeout and perform any required downstream authorization themselves; the worker does not infer business permissions from a handler name.

This is a trusted adapter boundary, not a general-purpose sandbox. `sandbox_workload` remains unsupported. A registered handler is executable trusted server code and must be reviewed, tested and deployed as part of the worker release.



### Capability handler execution budgets

Capability handlers receive a monotonic deadline through `CapabilityInvocationContext`. They should call `context.raise_if_expired()` at safe checkpoints and may use `context.remaining_seconds()` to bound downstream HTTP, database or subprocess operations. The worker checks the deadline before dispatch and after the handler returns, and discards results returned after the deadline.

Capability handlers run in a disposable spawned Python process. The parent worker enforces the contract timeout, terminates the child on expiry and rejects late results. Handlers must be importable module-level callables so they can be serialized into a spawned process; local closures and lambdas are not supported. The child receives only the immutable invocation context and validated input, not the worker's live database connections or application object.

This provides a hard process-termination boundary for trusted code, not a security sandbox. The child still runs under the worker's OS identity and inherits its environment; it is not protected by seccomp, namespaces, cgroups, a restricted filesystem or a separate credential set. Never register untrusted code. OS-level resource isolation and per-handler credential scoping remain production hardening requirements.

## Linux capability worker hardening

A hardened systemd deployment profile is provided at [`deploy/systemd/agentbox-capability-worker.service`](../deploy/systemd/agentbox-capability-worker.service), with installation steps and explicit security boundaries in [the worker hardening guide](../docs/deployment/capability-worker-os-hardening.md). The profile applies OS restrictions and aggregate resource limits to the worker and its spawned children. It does **not** provide handler-scoped credentials, destination-level network allowlisting or a hostile-code sandbox. Never place secrets in the worker environment because spawned children inherit it.


### Capability-scoped secret access

Capability handlers may request opaque `secret://` references through `CapabilityInvocationContext.resolve_secret`. The request is bound to tenant, subject, capability version and immutable contract hash. The default broker denies all requests. The standalone worker's `CAPABILITY_SECRET_BROKER` defaults to deny-all; production deployments must replace it in reviewed application code with an authenticated remote broker that enforces exact scope, short TTLs and revocation; no concrete Vault/KMS adapter is included yet. Never place secret values in contracts, job payloads, process environment or audit events. See [the worker hardening guide](../docs/deployment/capability-worker-os-hardening.md).


## Execution-backed evaluation

- `POST /v1/agents/{agent_id}/versions/{version}/evaluations/execute` — execute every input in an immutable evaluation profile through the server-configured provider, then score the recorded outputs. Requires an `Idempotency-Key` header and separate authorization for agent execution, evaluation creation and profile read.
- The endpoint caps a run at 100 cases, rejects tool-enabled manifests, derives per-case execution idempotency keys, and fails closed when provider cost or latency evidence is missing.
- Evaluation records include server-recorded execution IDs, agent/profile content hashes, per-case input/output hashes, provider/model identifiers and a server-derived workload hash. Existing caller-submitted evaluation remains available but is explicitly labelled `caller_submitted`.
- This is synchronous provider execution with durable per-case execution records, not yet a durable batch-orchestration workflow. A process interruption may leave a partial set of completed case executions; retry with the same idempotency key reuses completed per-case executions. The comparison service verifies matching parent/candidate execution evidence, but every comparison remains advisory and cannot authorize promotion.


## Parent/candidate comparison evidence

- The existing parent/candidate comparison endpoint now rechecks both evaluation runs against the tenant-scoped immutable agent versions, pinned evaluation profile, workload hash, and completed execution records.
- A comparison is labelled `verified` only when both runs are `server_recorded`, their profile-derived workload hashes match the submitted workload hash, and every case's execution ID, input/output hash, provider/model, latency, and cost match the persisted execution record.
- Caller-submitted runs and mismatched evidence remain `unverified`; they are never upgraded based on a caller assertion. Existing comparison rows are migrated with `evidence_verified=0` and remain unverified.
- Verified evidence does not grant promotion authority. Every comparison remains `promotion_eligible=false` and `decision_authority=advisory_only` pending a separate reviewed promotion gate.
