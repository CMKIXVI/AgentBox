# AgentBox architecture conformance audit — 2026-11-14

**Repository:** `CMKIXVI/AgentBox`  
**Audited branch:** `feature/agentbox-openai-compatible-provider`  
**Audit method:** GitHub source/tree inspection of the canonical architecture, backend modules/routes, frontend entry points, contracts, tests and engine specifications.  
**Execution evidence:** No tests, CI workflows, live providers, deployed clients or production services were executed during this audit.

## 1. Executive finding

AgentBox has not lost its platform foundations, but recent implementation batches have drifted toward low-level persistence hardening rather than advancing the defining intelligence and agent-factory architecture.

The current code is a meaningful backend/security foundation, not yet the autonomous agent operating system described by the source architecture. The most important missing connection is the complete governed agent lifecycle: cognitive processing and planning, capability invocation, multi-step orchestration, trusted observation and verification, learning, candidate comparison, and controlled evolution.

**Conclusion:** preserve the existing foundation; do not replace it. Rebalance the roadmap toward cognition, agent execution, capability orchestration and evidence-driven evolution. Infrastructure hardening remains necessary when it directly blocks those flows, but must not become the default workstream.

## 2. Five-pillar conformance

| Pillar | Existing implementation | Actual status | Critical missing capabilities |
|---|---|---|---|
| **1. AI Intelligence** | Agent manifests, one-call provider execution, evaluation of submitted outputs, ECE, execution experiences and proposed lessons | Foundational data and evaluation slices only | Goal formation, perception, cognition/reasoning, planning, decision, reflection, persistent cognitive state, agent memory, world/context model integration, cognitive evolution |
| **2. Agent Factory** | Immutable manifest registry, versioning, cloning, lineage, bounded deterministic candidate operators | Partial implementation | Full agent genome, mutation proposals/diffs, experiment records, trusted parent/candidate execution on identical workloads, independent gates, approval, promotion and rollback |
| **3. Application Factory** | Capability and workflow JSON Schema/graph validation | Contract-only | Workflow interpreter, capability composition, application generation, app packaging/import/export, deployment lifecycle, runtime app testing |
| **4. Execution Engine** | Synchronous provider invocation, durable SQLite jobs, provider worker, execution records, separate gVisor sandbox adapter | Narrow provider-job runtime | Agent loop, DAG execution, planner/orchestrator, multi-agent delegation, permission-aware tool/action gateway, resumable checkpoints, sandbox-to-worker integration |
| **5. Platform Foundation** | OIDC/JWT, principal and tenant lifecycle, deny-by-default authorization, audit, SQLite stores, backup/restore, provider adapter, Flutter and Next.js foundations | Strongest and most advanced pillar; still pre-production | Production database/HA, secret broker, live provider/issuer deployment, operational telemetry, live recovery/security drills, functional client workspaces |

### 2.1 Pillar 1 — AI Intelligence

Current evidence:
- `backend/app/execution.py` invokes one provider call; it is not a reasoning/planning loop.
- `backend/app/evaluation.py` scores caller-submitted results; it does not execute benchmark cases.
- `backend/app/enterprise_context.py` provides tenant-scoped enterprise context entities, relationships, evidence and events. It is not a cognitive memory or reasoning engine.
- `backend/app/experience.py` stores execution/evaluation experience and proposed lessons. Linkage is caller-asserted and unverified; lessons do not alter agent behavior.
- No executable goal engine, perception layer, cognition engine, planner, reflection engine, or working/episodic/semantic/procedural memory subsystem was found in the runtime tree.

**Assessment:** intelligence is currently represented mostly by provider invocation plus supporting records. The cognition architecture is not implemented.

### 2.2 Pillar 2 — Agent Factory

Current evidence:
- `backend/app/registry.py` provides immutable tenant-scoped manifest versions and lineage.
- `backend/app/candidate_generation.py` creates bounded candidates from registered mutation operators and protects identity, tools and permissions.
- Candidate responses explicitly remain `unverified_candidate` and `promotion_eligible=false`.

Missing:
- A complete agent genome contract with explicit mutable/protected partitions.
- First-class mutation proposal and structured diff artifacts.
- A durable experiment runner that executes parent and candidate on the same pinned workload.
- Trusted evaluation evidence and independent hard gates.
- Approval-controlled promotion and rollback.

**Assessment:** registry and candidate generation are real runtime slices; the Agent Evolution Engine is not end-to-end.

### 2.3 Pillar 3 — Application Factory

Current evidence:
- `backend/app/capability_contract.py` validates declarative capability contracts.
- `backend/app/workflow_contract.py` validates workflow structure and graph invariants.
- Their module contracts explicitly state they do not invoke capabilities or execute workflows.

Missing:
- Capability resolution and invocation.
- Workflow interpreter and durable node execution.
- Application composition/build artifacts.
- Application package lifecycle, import/export, deployment and runtime verification.

**Assessment:** schemas and validation are groundwork only. No application factory runtime exists.

### 2.4 Pillar 4 — Execution Engine

Current evidence:
- The synchronous execution service performs a single provider call.
- Durable execution jobs and a separate worker support the allowlisted `provider_invocation` workload.
- The worker explicitly rejects `sandbox_workload`.
- The gVisor adapter exists separately and is not connected to the public execution API, worker, candidate evaluator or controller.

Missing:
- Goal/task interpreter and bounded multi-step agent loop.
- Planner and orchestrator with explicit state transitions.
- Typed agent-to-agent handoff and shared-workspace controls.
- Permission-aware tool/action gateway and runtime capability enforcement.
- Checkpoint/resume for multi-step execution.
- A connected isolated runner for generated or untrusted workloads.

**Assessment:** provider-job processing exists; a general agent runtime does not.

### 2.5 Pillar 5 — Platform Foundation

Current evidence:
- OIDC/JWT principal validation, tenant context, authorization policy, audit and tenant-scoped persistence exist.
- Tenant backup/restore is encrypted and includes tenant-owned tables.
- SQLite remains a single-instance persistence boundary.
- Flutter and Next.js have OIDC/client transport foundations, but the web landing page labels Evaluation and Evolution as planned and the mobile client remains an operational shell.
- The OpenAI-compatible adapter exists as a module on the feature branch, but the live provider path, credentials, billing, latency and deployed operation have not been verified.

**Assessment:** this is the most developed pillar, but it is not production-certified and must serve the other four pillars rather than displace them.

## 3. Canonical lifecycle mapping

The source lifecycle is retained as the AgentBox architectural lifecycle:

`Intent → Context → Cognition → Capability → Responsibility → Execution → Observation → Verification → Memory`

| Lifecycle stage | Current implementation mapping | Status |
|---|---|---|
| Intent | Agent manifest objective and user input | Partial; no goal decomposition/management |
| Context | Tenant identity, ECE entities/relationships/evidence | Partial; no integrated cognitive context assembly |
| Cognition | No runtime cognition/planning/reflection engine | Missing |
| Capability | Capability contract validation; manifest tool declarations | Contract only; no invocation gateway |
| Responsibility | Principal, tenant and authorization policies | Platform authorization exists; no per-step capability responsibility model |
| Execution | One-call provider service and durable provider-invocation worker | Narrow implementation |
| Observation | Execution records, worker/job events and ECE events | Partial; no unified trace/event model across cognition and tools |
| Verification | Evaluation of submitted outputs and fitness summaries | Partial/untrusted; no trusted same-workload benchmark runner |
| Memory | Experience records and proposed lessons | Partial; no cognitive memory hierarchy or automated evidence-grounded consolidation |

The lifecycle is not a decorative sequence. Each transition needs a typed contract, durable state, provenance, authorization, failure semantics and observable evidence.

## 4. Engine boundaries — preserve distinctions

| Engine/service | Repository status | Architectural decision |
|---|---|---|
| Cognition Engine | No executable runtime found | Build as a distinct reasoning/planning domain; do not bury it inside provider invocation |
| Agent Evolution Engine (AEE) | Bounded candidate-generation slice only | Keep agent configuration evolution separate from model-weight evolution |
| Retrieval Evolution Engine (REE) | Specification only | Evolve retrieval/query/ranking configurations against versioned retrieval benchmarks |
| Model Genetics Engine (MGE) | Research/registry specification only | Preserve as a separate experimental model-lineage/reproduction domain; do not imply neural crossover works |
| Cognitive Evolution | No runtime found | Keep distinct from agent-manifest mutation; define what cognitive strategies/state can evolve and how they are evaluated |
| Knowledge Evolution | No runtime found | Keep source knowledge immutable; evolve retrieval/representation/curation policy under evidence and provenance controls |
| Autonomous Improvement Controller | Architecture specification plus experience/candidate slices | Do not enable unattended control until trusted execution, verification, gates, approval and durable controller state exist |

Shared artifact lineage, evaluation, policy and approval services may be reused, but engine-specific genomes, operators and evaluation semantics must remain separate.

## 5. Frontend conformance

- **Next.js:** authentication/session and API proxy foundations exist. The current home page is a workspace shell; Agent Studio, execution inspection, evaluation comparison and evolution controls are not yet complete.
- **Flutter:** authentication and transport foundations exist. The current app is an operational shell, not a complete mobile agent operations client.
- Both remain clients of the same FastAPI authority. Do not move cognition, agent orchestration, evaluation or promotion logic into either client.

## 6. Documentation and consistency findings

1. `ARCHITECTURE.md` describes backend domains but does not yet make the five pillars and the full cognitive lifecycle explicit enough to govern implementation priorities.
2. The implementation sequence in `ARCHITECTURE.md` contains a progress paragraph inside the stage table, breaking the table structure. Move that paragraph below the table.
3. `docs/repository-gap-analysis-2026-11-11.md` describes an earlier repository snapshot with no application runtime or CI. It is stale relative to the current backend, frontends and workflows and must be marked historical or superseded.
4. `research/current-implementation-audit-2026-11-11.md` is a dated historical audit, not the current implementation baseline.
5. The engine specifications correctly warn that design documents are not implementation evidence. Keep that distinction in all future readiness reporting.

## 7. Priority roadmap reset

Implementation batches must trace to a pillar, lifecycle stage, engine, contract and acceptance test. Do not spend consecutive batches on isolated infrastructure cleanup unless it blocks a higher-priority flow.

| Priority | Workstream | Required outcome |
|---|---|---|
| **P0** | Architecture and traceability | Five pillars, lifecycle map, engine boundaries, implementation status and roadmap are canonical in `ARCHITECTURE.md` |
| **P1** | Cognitive runtime contracts | Typed goal, context, cognition, plan, decision, observation, verification and memory records/events; explicit engine boundaries |
| **P2** | Agent runtime/orchestrator | Bounded state machine and multi-step task loop; checkpoint, cancellation, retry and event trace |
| **P3** | Capability/action gateway | Versioned capability registry, input/output validation, policy-mediated invocation, least privilege and auditable side effects |
| **P4** | Trusted execution and verification | Connect isolated execution to worker; pinned workload snapshots; execute parent/candidate on identical workloads; retain trusted evidence |
| **P5** | Complete Agent Evolution Engine | Mutation proposals/diffs, experiment records, independent hard gates, approvals, promotion and rollback |
| **P6** | Memory and learning | Evidence-grounded consolidation, memory tiers, provenance, retention and tenant isolation |
| **P7** | Retrieval and Knowledge Evolution | Corpus/index/query-set snapshots, retrieval traces, held-out benchmarks and controlled strategy promotion |
| **P8** | Application Factory | Workflow interpreter, capability composition, application artifacts and governed deployment lifecycle |
| **P9** | Model Genetics Engine | Model genome registry and compatibility metadata first; only then isolated, reproducible adapter experiments |
| **Parallel** | Flutter and Next.js | Build functional views against the same API contracts; no duplicated domain authority |

### Immediate next implementation target

Start with **P1: Cognitive Runtime Contracts**, not another backup/SQLite hardening batch. First define the minimum typed domain model and lifecycle event vocabulary for Intent, Context, Cognition, Capability, Responsibility, Execution, Observation, Verification and Memory. Reuse current identity, registry, execution, ECE and audit authorities; do not create parallel stores or duplicate agent identities. Then implement one vertical slice that can be tested end-to-end before broadening.

## 8. Verification boundary

This audit is a repository inspection, not a test or production-readiness claim. The findings are based on source and documentation present on the audited branch. Tests were not run; CI was not invoked; no live provider, identity provider, sandbox host, frontend deployment or production database was exercised.


## 9. First P1 implementation slice — cognitive lifecycle contracts

The branch now contains `schemas/cognitive-event-v1.schema.json`, `backend/app/cognitive_contract.py`, and `backend/tests/test_cognitive_contract.py`. The contract fixes the lifecycle vocabulary and enforces stage/event matching, evidence requirements, explicit authorization-decision and capability references, and forward-only non-skipping transitions. See `docs/runtime/cognitive-runtime-contracts.md`.

This remains contract code only. No tests were executed in this batch; no API, durable state store, cognitive engine, planner, memory engine, or capability runtime is claimed.


## 10. P1 cognitive runtime implementation update

The branch now includes a tenant-scoped cognitive run journal and authenticated API:
- Runs bind to an existing immutable agent version and registry content hash.
- Tenant and actor identity are server-derived from the authenticated principal.
- Create and append operations require idempotency keys bound to actor/request.
- Events are ordered, stage-transition validated, bounded to 64 KiB, and append-only at the SQLite trigger level. Idempotency keys are stored only as SHA-256 digests; payloads reject nested reserved authority, credential and executable-field names, and event envelope digests are checked on read.
- Verification and accepted memory events require verified evidence references.
- Capability and responsibility events require explicit versioned capability and authorization-decision references.
- API routes support create, append, get and paginated event reads, with tenant isolation and authorization.

This is a stateful lifecycle journal only. It does not implement cognition, planning, capability invocation, trusted evidence, or memory consolidation. SQLite remains single-instance. The new tests were added but not executed; no CI or live integration evidence is claimed.


## 11. P2 cognitive context assembly implementation update

A deterministic context assembly engine and authenticated endpoint are now implemented:
- Reads only through the existing tenant-scoped Enterprise Context service.
- Binds relationships to exact selected entity versions and includes only edges whose endpoints are both selected.
- Excludes expired records; defaults to observed/human-validated assertions; inferred assertions require explicit opt-in; AI hypotheses are excluded.
- Omits raw attributes and limits snapshots to 48 KiB.
- Validates snapshots against a dedicated versioned JSON Schema and derives a content-addressed reference.
- Embeds the snapshot in the append-only `context.assembled` event with idempotent replay.
- Requires a distinct `cognition.context.assemble` grant plus existing entity, relationship and evidence read grants; tenant identity remains principal-derived. Snapshot references are tenant-bound.

Known blocker: the evidence store currently records evidence as unverified and has no authorized validation workflow. Context assembly therefore includes validated evidence only and currently cannot surface unverified records as proof. No evidence attestation, reasoning loop, retrieval-augmented generation, capability invocation, or agent execution is claimed. New regression tests were added but have not been executed; CI was not invoked.
