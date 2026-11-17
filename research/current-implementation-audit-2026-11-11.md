> **Historical snapshot (2026-11-11):** This audit is retained as dated evidence and is superseded for current repository status by `docs/architecture-conformance-audit-2026-11-14.md` and `ARCHITECTURE.md`.\n\n# AgentBox current implementation audit — 2026-11-11

Repository: `CMKIXVI/AgentBox`  
Default branch: `main`  
Audit basis: live GitHub files and Actions evidence fetched on 2026-11-11.  
Scope: bounded audit of the current API/backend slice; not a full security review or production certification.

## 1. Verified repository state

The current backend is a real, small FastAPI application—not only a research extraction.

Verified files:
- `backend/pyproject.toml`: Python >=3.11, FastAPI, Pydantic, Uvicorn, jsonschema; dev extras include httpx, pytest and Ruff.
- `backend/app/main.py`: API composition and route definitions.
- `backend/app/registry.py`: SQLite immutable agent-version registry.
- `backend/app/validation.py`: authoritative JSON Schema validation for agent manifests and evaluation profiles.
- `backend/app/evaluation.py`: immutable evaluation profiles/runs and deterministic scoring of submitted outputs.
- `backend/app/execution.py`: bounded provider-adapter execution service.
- `backend/tests/test_registry_api.py`, `test_evaluation_api.py`, `test_execution_api.py`: API-level test suites.
- `.github/workflows/backend-ci.yml`: GitHub Actions workflow runs Ruff and pytest.

## 2. Implemented API surface

Observed in `backend/app/main.py`:
- `GET /health`
- `POST /v1/agents/validate`
- `POST /v1/agents`
- `GET /v1/agents/{agent_id}/versions`
- `GET /v1/agents/{agent_id}/versions/{version}`
- `POST /v1/agents/{agent_id}/versions/{version}/clone`
- `POST /v1/agents/{agent_id}/versions/{version}/executions`
- `GET /v1/executions/{execution_id}`
- Evaluation profile validate/create/list/get endpoints.
- Evaluation run create/get/list endpoints.

## 3. Current implementation findings

### Registry — implemented vertical slice
- Immutable `agent_id + version` records in SQLite.
- Canonical JSON serialization and SHA-256 content hash.
- Idempotent create for identical content; conflict for different content under the same immutable version.
- Clone/derive with parent lineage and validated overrides.
- Schema validation and API-level tests, including concurrent duplicate create.

### Evaluation — implemented, but not an agent runner
- Immutable evaluation profiles and persisted evaluation runs.
- Deterministic assertions include exact match, contains, required fields and JSON Schema validation.
- Weighted correctness/latency/cost scoring and gates.
- Evaluation consumes submitted outputs and measurements. It does not invoke the agent or provider itself.

### Execution — deliberately narrow
- Provider request/response protocol and adapter interface.
- Deterministic fake provider is the only provider registered by the API factory.
- Persists execution records and supports idempotency-key replay/conflict handling.
- Validates output-token bounds and checks returned usage metrics.
- Executes one provider call (`steps=1`).
- Rejects tool-enabled manifests because no principal-aware tool authorization/registry is available.
- No real provider adapter or secret resolver is wired into the API.

### Security and production gaps
- No established authenticated principal or tenant-scoped authorization in the API.
- No multi-tenant isolation guarantee.
- No executable tool registry, sandbox, tool permission evaluator or approval service.
- No durable background queue, worker orchestration or cancellation.
- SQLite is the current persistence implementation; production deployment/backup/concurrency requirements are not yet addressed.
- No package signing, marketplace, workflow interpreter, RAG/knowledge service or multi-agent orchestration in the verified backend slice.
- The health endpoint is a process-level response, not a complete dependency/readiness probe.
- A successful fake-provider call is not evidence of external model connectivity or real-world agent capability.

## 4. CI failure investigation and correction

The previous workflow run failed before tests:
- Failed run: [42998451779](https://github.com/CMKIXVI/AgentBox/actions/runs/42998451779)
- Failure stage: Ruff lint.
- Exact issue: `backend/app/main.py:24` contained ` )from .registry...` without a newline between import statements.
- The test step was skipped on that failed run.

Correction:
- Commit: `569f03c4e968ecf4f39a014f5928c69bed34e9d5`
- Change: inserted the missing newline between the execution and registry import blocks.
- Verified the resulting source line separation through GitHub file retrieval.

Green verification:
- [CI run 43002485988](https://github.com/CMKIXVI/AgentBox/actions/runs/43002485988)
- Head SHA: `569f03c4e968ecf4f39a014f5928c69bed34e9d5`
- Job: `test` — success.
- Install: success.
- Ruff: `All checks passed!`
- Pytest: **32 passed**.
- One dependency warning remains: Starlette reports that using `httpx` with `starlette.testclient` is deprecated and recommends `httpx2`.
- This is backend CI evidence only. It does not validate external providers, tenant isolation, tools, payments, SAP, offline mode or production operations.

## 5. Evidence-backed readiness by subsystem

| Subsystem | Current status | Evidence / limitation |
|---|---|---|
| Manifest schema and validation | Implemented + CI tested | Authoritative JSON Schema and API tests |
| Immutable agent registry | Implemented + CI tested | SQLite, hashes, idempotency, lineage and concurrency test |
| Clone/version derivation | Implemented + CI tested | Validated overrides and parent lineage tests |
| Evaluation profiles/runs | Implemented + CI tested | 32-test green run; evaluation scores submitted results only |
| Execution API | Implemented + CI tested (fake provider) | Idempotency, persistence, limits and explicit tool denial |
| Real LLM provider integration | Not implemented/verified | No provider other than fake registered |
| Tool/action execution | Not implemented | Denied by policy until principal-aware authorization exists |
| Identity/authentication/tenancy | Not implemented/verified | No tenant principal or isolation demonstrated |
| Multi-agent orchestration | Not implemented | No delegation runtime |
| Workflow interpreter | Not implemented | No canonical workflow runtime yet |
| Knowledge/RAG | Not implemented in verified backend | Research only |
| Package signing/marketplace | Not implemented | Requirements only |
| Offline/edge deployment | Not implemented | Research only |
| Production operations | Not verified | No deployment, load, backup/restore, security or external E2E evidence |

## 6. Immediate next implementation gate

**Do not enable tools yet.** The next engineering milestone should close the trust boundary:

1. Define an authenticated principal/context object and test identity propagation.
2. Add workspace/tenant ownership to agent, execution and evaluation records.
3. Add server-side authorization checks for every read, clone, execution and evaluation operation.
4. Ensure idempotency keys are scoped to principal/tenant rather than globally shared.
5. Add audit events for policy decisions and attempted/denied operations.
6. Keep tools denied until a typed tool registry, per-tool permission policy, secret isolation, bounded invocation and postcondition checks exist.
7. Add tests proving cross-tenant reads/writes are denied and that unauthorized users cannot execute or inspect another tenant's agents.

Only after this gate passes should the platform introduce a first read-only tool adapter, then a narrowly scoped write action with approval and idempotency.

## 7. Current conclusion

AgentBox has a credible initial foundation: immutable agent manifests, version lineage, deterministic evaluation and a bounded fake-provider execution path. The latest backend CI is green with 32 tests.

It is **not yet a production agent platform**. The critical missing layer is principal-aware authorization and tenant isolation; real provider integration and safe tool execution follow. The repository README has been corrected to describe this actual state and to avoid the earlier inaccurate statement that no runtime exists.
