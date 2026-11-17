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

The v1 evaluation service **does not execute an agent or call a model**. A trusted runner must submit each case's output, latency and cost. The service validates and scores those submitted results and persists an immutable run record. Missing case outputs count as failures; duplicate or unknown case IDs are rejected. This avoids presenting caller-supplied results as proof of a live model execution.

Evaluation success is an eligibility signal, not an automatic publish/deploy action. Authentication, tenant isolation, trusted execution provenance, PostgreSQL migrations and production deployment controls remain future work.

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
