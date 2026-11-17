> **Historical snapshot (2026-11-11):** This gap analysis predates the current FastAPI backend, OIDC/tenant services, execution jobs, sandbox adapter and dual frontend foundations. Do not use it as the current implementation inventory; see `docs/architecture-conformance-audit-2026-11-14.md` and `ARCHITECTURE.md`.\n\n# AgentBox repository gap analysis — 2026-11-11

> **Evidence basis:** GitHub tree for `CMKIXVI/AgentBox` at commit `54c9579fe954d0b74e17aab1b6dcf0576e579c90`, plus fetched README, design documents, engine contracts and legacy extracts. This is a repository-content assessment, not a CI run or runtime test.

## 1. Verified repository shape

The repository currently contains:
- Root README and research/source registers.
- Architecture/design documents for agent evolution, retrieval evolution and model genetics.
- Shared evolution-platform contracts.
- ZIP-derived research extracts.
- Six small legacy Python/TypeScript reference files under `research/legacy-extracts/`.

The inspected tree contains **no application runtime, frontend application, API service, database migrations, worker service, provider adapter implementation, tool registry implementation, package importer/exporter, offline model manager, test suite or CI workflow**. No production execution path is present in the inspected repository tree.

## 2. Current implementation classification

| Area | Repository evidence | Status |
|---|---|---|
| Product intent and source provenance | README and research registers | Documented |
| Agent manifest/genome concept | Agent Evolution Engine spec | Design only |
| Immutable candidate lifecycle | Agent evolution design/spec | Design only |
| Lineage and shared artifact envelope | Evolution platform contracts | Design only |
| Retrieval evolution | Retrieval Evolution Engine spec | Design only |
| Model genetics | Model Genetics Engine spec | Design only |
| Agent execution runtime | Legacy executor extract only | Not implemented |
| Durable task store and queue | Legacy task model/API/worker extracts only | Not implemented |
| Provider/model routing | Research/design concepts only | Not implemented |
| BYOK secret handling | Design requirement only | Not implemented |
| Tool registry and policy enforcement | Design concepts; unsafe legacy tool example | Not implemented |
| Secure code sandbox | No isolation implementation | Not implemented |
| Orchestrator/specialist runtime | Research/design only | Not implemented |
| Agent package/export/import | Product requirement and architecture notes | Not implemented |
| Offline model discovery/download/update | User-requested in source; no runtime | Not implemented |
| Evaluation harness and promotion gates | Architecture specs only | Not implemented |
| Flutter/web/mobile UI | No frontend project in inspected tree | Not implemented |
| Billing/credits/hiring | Product concepts only | Not implemented |
| Automated tests/CI | No test or workflow paths in inspected tree | Not implemented |

## 3. Critical legacy-code warnings

### `research/legacy-extracts/tools.py`
- The function named `safe_eval_tool` launches arbitrary Python with `subprocess.run`.
- A timeout limits duration but does not isolate filesystem, network, process privileges, secrets or host resources.
- The file uses a legacy OpenAI Completion API pattern and should not be treated as a current provider adapter.
- The source is retained for provenance only. It must not be imported into a production runtime.

### `research/legacy-extracts/agent_executor.py`
- It contains a simple bounded loop, but trusts a JSON action response and dispatches based on action names.
- The extracted example is not a complete authorization, schema-validation, durable-state or sandbox design.
- It is a reference for task-loop shape only.

## 4. Implementation sequence and acceptance gates

### Phase 0 — repository foundation
- Establish the actual application structure and supported runtime/language.
- Add formatting, linting, type checking, unit-test runner and CI.
- Keep research extracts outside importable application packages.
- Define threat model and security invariants.

**Gate:** clean CI on an empty but correctly structured project; no legacy research module imported by runtime code.

### Phase 1 — agent definition and immutable registry
- Define a versioned agent manifest schema.
- Validate IDs, model/provider references, prompt references, tool declarations, policies, dependencies and compatibility.
- Store immutable versions with content hashes and provenance.
- Add list/get/validate operations.

**Gate:** schema tests, invalid-manifest rejection, stable hashing and immutable-version tests.

### Phase 2 — safe task runtime
- Create task/run records with queued/running/succeeded/failed/cancelled states.
- Add bounded steps, deadlines, cancellation, durable logs and checkpoint handling.
- Use a deterministic fake model and fake tools first.
- Add tool schema validation and per-run authorization.
- Exclude arbitrary code execution from the first runtime.

**Gate:** unit and integration tests for state transitions, retries, duplicate submissions, cancellation, step limits, malformed tool calls and unauthorized tool calls.

### Phase 3 — provider adapters and BYOK
- Define a provider-neutral model interface.
- Add one real provider adapter only after deterministic fake-provider tests.
- Resolve credentials through server-side secret references; never put raw keys in agent manifests, exports, logs or prompts.
- Add routing policy and fallback with explicit cost/latency/quality constraints.

**Gate:** credential redaction tests, provider contract tests, timeout/retry tests and routing evaluation.

### Phase 4 — orchestration and shared workspace
- Define typed agent-to-agent task envelopes.
- Implement orchestrator delegation and specialist execution as ordinary agent runs.
- Add scoped shared artifacts, ownership, concurrency controls and resumability.
- Avoid free-form unrestricted agent-to-agent messaging.

**Gate:** deterministic multi-agent integration tests, state recovery, permission-boundary and deadlock/loop-limit tests.

### Phase 5 — evaluation and controlled evolution
- Define reproducible evaluation suites and immutable baseline results.
- Clone a parent version to a candidate; allow bounded mutations to declared fields.
- Compare parent and candidate on identical tests.
- Require policy and evaluation gates before promotion.
- Support rollback by changing an active-version pointer, not mutating historical artifacts.

**Gate:** lineage integrity, repeatable evaluation, failed-candidate non-promotion and rollback tests.

### Phase 6 — portability, local models and product layers
- Define export package manifest, dependency lock and compatibility checks.
- Add import validation and signed/provenance-aware packages.
- Add local model catalogue, model file integrity checks, supported runtime matrix and resource constraints.
- Add marketplace and commercial layers only after usage metering and authorization are reliable.

**Gate:** export/import round-trip, tamper detection, compatibility rejection, local-model resource tests and billing idempotency/reconciliation tests.

## 5. Decisions that must not be silently assumed

| Topic | Source/user signal | Required decision |
|---|---|---|
| Frontend | Flutter was specified in Agent Factory OS conversation | Confirm current target surfaces and choose Flutter architecture only after inspecting build constraints |
| Backend/runtime language | Legacy sample is Python; design docs are language-neutral | Select based on runtime/security/deployment needs; do not inherit legacy stack by default |
| Storage/queue | Legacy sample suggests SQLite/Postgres + Redis/RQ | Choose durable store and queue after task consistency and scale requirements are defined |
| Provider strategy | Multiple integrations, OpenRouter-like routing and BYOK requested | Decide provider contract, secret manager and routing policy |
| Offline support | Local model discovery/download/update requested | Define supported OS, hardware, model formats, licensing and runtime matrix |
| Export target | User says agents should export to any environment | Define concrete target environments and portability contract; “any environment” is not technically testable |
| Hiring/payment | User requested payment and hiring/charging systems | Define whether hiring means human talent, agent marketplace, autonomous agent workforce, or more than one |
| Marketplace trust | Agent publishing requested | Define publisher identity, signatures, permissions, review, revocation and update policy |

## 6. Readiness statement

**Current software implementation readiness: not yet assessable / research-and-design stage.**

The repository has meaningful architecture and source research, but the inspected tree does not contain an executable product runtime or automated tests. Therefore:
- No percentage is assigned.
- No production-ready claim is justified.
- No live end-to-end workflow has been validated.
- The next correct milestone is Phase 0 plus Phase 1, not adding more speculative subsystems.

## 7. Immediate next engineering task

Create the application skeleton and CI first, then implement the agent manifest schema and immutable registry with tests. Keep the first slice narrow: create an agent definition, validate it, save version 1, retrieve it, clone it into version 2, and prove that version 1 remains unchanged.