# AgentBox Autonomous Improvement Architecture

**Status:** architecture specification with a first runtime slice implemented in PR #19; no autonomous controller or end-to-end evolution runtime is claimed.  
**Source reviewed:** user-supplied `YNDRA-autonomous-self-evolving-1.0.0.zip`.  
**Product and namespace:** AgentBox only.

## 1. Decision

Adopt the archive's strongest contribution as a native **Autonomous Improvement Controller** within AgentBox's existing agent and capability evolution platform.

The adopted pattern is a closed, evidence-driven loop:

`approved agent version -> bounded execution -> experience records -> lessons -> candidate generation -> parent/candidate evaluation on the same workload -> mandatory gates -> promotion decision -> retained lineage -> next cycle`

The evolutionary unit is an immutable, versioned AgentBox artifact (initially an agent manifest and its referenced configuration), not arbitrary repository source code, a live process, or model weights. A candidate is materialized separately from its parent. Only the existing AgentBox registry and promotion authority may make a candidate active.

This is an architectural adoption, not a wholesale import of the archive's Go code. AgentBox remains the sole product, API, persistence, identity, authorization and deployment authority.

## 2. What was reviewed

The archive contains 6,642 ZIP entries (including directories), approximately 2.19 MB uncompressed. The principal implementation is Go 1.23 and includes:

- `core/capability`: stable capability identity, version, genome and lineage.
- `core/experience`: execution records, fitness, observations and lessons.
- `core/memory`: experience retention and retrieval.
- `core/learning`: deterministic lesson extraction with an optional context-aware extractor.
- `core/evolution`: candidate population generation, bounded genome mutation, crossover, optional LLM-proposed variation and lineage.
- `core/lifecycle` and `core/improvement`: execute, learn, evaluate candidates and compare them with the parent.
- `core/autonomy`: cancellable repeated controller, work selection, reporting and optional acquisition fallback.
- `core/registry`: version-aware capability registration and resolution.
- `core/acquisition`: a separate boundary for genuinely missing capability identities.
- `core/portfolio` and `core/adaptation`: improvement of existing implementations through registered factories.
- `docs/autonomy/`: operating model, controller goals and explicit definition-of-done conditions.

The archive's own design states that memory does not directly rewrite behavior, the evaluator—not generated text—decides fitness, the live version is not mutated in place, and acquisition is a fallback after improvement opportunities have been considered.

The ZIP was inspected as source material. Its Go programs were not executed or treated as production-verified. The archive's own test/build claims have not been independently verified here.

## 3. AgentBox naming normalization

The following names are the canonical AgentBox terms. Archive product names and package names must not leak into AgentBox APIs, schemas, configuration, telemetry or UI.

| Archive concept | Canonical AgentBox term | AgentBox boundary |
|---|---|---|
| YNDRA platform/runtime | AgentBox | Sole product identity; no parallel platform |
| Capability | Agent capability | Existing capability contract and agent manifest |
| Capability genome | Agent configuration genome | Bounded, schema-validated mutable fields of an immutable manifest version |
| Capability definition/version | Agent manifest version | Existing immutable agent registry |
| Experience record | Execution experience record | Tenant-scoped persisted execution/evaluation evidence |
| Memory store | Experience repository | Tenant-scoped retention and retrieval; not an unrestricted prompt memory |
| Lesson extractor | Learning service | Derives traceable lessons from retained experience |
| Fitness | Evaluation result / fitness report | Versioned evaluation profile and raw measurements |
| Evolution engine | Candidate generation service | Approved operators and factories create isolated candidates |
| Factory | Candidate materializer | Creates a new immutable artifact from a parent and bounded change plan |
| Improvement service | Candidate evaluation and comparison service | Runs parent and candidates against the same benchmark |
| Autonomy service/controller | Autonomous improvement controller | Selects and schedules governed improvement work |
| Portfolio | Agent portfolio | Existing registered agents eligible for improvement |
| Acquisition | Capability acquisition workflow | Separate, policy-gated creation of genuinely missing capability identities |
| Reporter | Improvement event/audit publisher | Append-only audit and operational telemetry |
| LLM proposer | Optional model-assisted change proposer | Untrusted proposal source; never evaluator or promotion authority |

Historical archive names may appear only in source-provenance records and this research document. Do not add legacy package aliases, environment variables, API routes, CLI commands or compatibility names.

## 4. Mapping to existing AgentBox foundations

| Adopted function | Existing AgentBox authority to reuse | Additive work required |
|---|---|---|
| Agent identity and immutable versions | `backend/app/registry.py`, agent manifest schema | Candidate versions and active-version pointer semantics |
| Capability/genome constraints | `backend/app/capability_contract.py`, manifest validation | Explicit allowlist of evolvable fields and immutable/security-sensitive fields |
| Execution | `backend/app/execution.py` | Repeatable candidate execution adapter and real provider only when separately integrated |
| Evaluation and fitness | `backend/app/evaluation.py`, evaluation profiles/runs | Compare parent and candidate on identical versioned workload; retain raw metrics |
| Experience | Execution/evaluation records | Durable, tenant-scoped experience linkage, privacy/retention rules |
| Learning | Existing evaluation evidence and future learning service | Traceable lesson records; model-generated lessons remain untrusted proposals |
| Candidate generation | Existing clone/lineage and evolution architecture contracts | Bounded deterministic operators and candidate materializer |
| Promotion/rollback | Registry plus shared evolution contracts | Atomic active-version pointer, mandatory gates, approvals and rollback events |
| Autonomous scheduling | Existing API/service composition | Cancellable controller, bounded cycles, concurrency guard, durable job state |
| Missing capability acquisition | Agent/capability registry | Distinct request/proposal workflow; must reject duplicate identities |
| Tenant/security | OIDC, active tenant, exact-match authorization, audit | Per-operation grants, resource limits, approval policy and tenant-scoped records |
| Recovery | Encrypted tenant backup/restore | Include all new experience, experiment, event and active-version records in backup inventory |

No new database, graph service, message broker, microservice or Go runtime is introduced by this adoption. The initial implementation must fit the existing Python/FastAPI and SQLite architecture. A future implementation may move storage behind interfaces only when operational evidence justifies it.

## 5. Canonical improvement cycle

1. **Discover eligible agents.** Read approved, active agent versions from the tenant-scoped registry. Exclude suspended, retired, unverified or policy-ineligible agents.
2. **Select improvement work.** Rank eligible agents using retained evaluation evidence. Lowest reliable performance may be prioritized, but sample count, recency, uncertainty, failure rate, cost and business priority must prevent misleading single-run rankings.
3. **Load a fixed benchmark.** Pin the exact evaluation profile, cases, datasets/corpus versions, runtime/provider/model/tool versions and configuration snapshot.
4. **Establish the parent baseline.** Execute the approved parent against the workload and retain raw output, errors, latency, cost and evaluation results.
5. **Learn from experience.** Derive traceable lessons from structured records. Lessons can inform a proposal but cannot directly change an agent or grant permissions.
6. **Generate a bounded candidate population.** Clone the immutable parent; apply only allowlisted, typed mutation operators with explicit parameter bounds, operator version and deterministic seed where supported. Every candidate receives a new immutable version and parent lineage.
7. **Evaluate candidates fairly.** Run every candidate against the same workload and environment as the parent. Record nondeterministic dependencies. A failed or incomplete run cannot be interpreted as a successful improvement.
8. **Apply hard gates.** Schema, compatibility, policy, security, correctness, regression, resource/cost and required human-review gates are independent. A high aggregate score cannot override a failed mandatory gate.
9. **Select and promote.** A candidate must beat the parent by the configured margin and satisfy every mandatory gate. Promotion is a separate authorized operation that changes the active-version pointer; it never overwrites artifact contents.
10. **Retain and repeat.** Store experiment, evidence, lessons, lineage, evaluation, approval and promotion events. Continue only within bounded controller policy and stop promptly on cancellation, tenant suspension or policy revocation.

If no candidate qualifies, retain the current approved version. A no-op or failed cycle is a valid outcome, not a reason to force promotion.

## 6. Learning, memory and evidence rules

- Every experience record identifies tenant, agent ID, exact manifest version/hash, execution ID, evaluation profile/version, workload reference, runtime versions and observation time.
- Store raw metrics and provenance separately from derived lessons and aggregate fitness.
- Lessons carry source experience references, extraction method/version and confidence. They are hypotheses for candidate design, not facts or policy.
- Experience retrieval is tenant-scoped, access-controlled, bounded and subject to retention/deletion policy.
- Do not retain sensitive input/output payloads by default. Prefer redacted, minimized or referenced evidence with explicit data classification and retention.
- Model-assisted extraction must identify model/provider/version and prompt/template reference. Provider output is untrusted and must be validated.
- A score is meaningful only with its evaluation profile, benchmark, workload, sample size and raw measurements. Do not compare scores from incompatible profiles as if they were directly comparable.

## 7. Candidate mutation and model-assisted proposals

Initial candidate changes may cover only declared mutable manifest fields: prompt/instruction references, bounded model parameters and routing, allowlisted tool selection without permission expansion, workflow references, memory/retrieval configuration and other explicitly approved configuration fields.

The following are immutable or separately approval-gated: agent identity, tenant, ownership, authorization policy, tool/data/network permissions, credential references, secret access, external side-effect authority, deployment target and runtime isolation policy.

Mutation proposals record parent hashes, changed paths, operator and version, bounds, seed, expected effect, permission impact, risk class, required test suites and a structured diff.

An optional LLM may propose lessons or candidate changes. It cannot:
- determine correctness or fitness;
- alter evaluation profiles or mandatory gates;
- approve itself or promote a candidate;
- grant permissions, retrieve secrets or select production credentials;
- execute arbitrary code on the host.

A proposal is accepted only after schema, policy and compatibility validation. Deterministic operators remain available without an LLM or API key.

## 8. Controller and operational controls

The controller is a service over AgentBox authorities, not an independent autonomous administrator.

Required controls:
- disabled by default until an operator enables a specific tenant-scoped policy;
- bounded interval, work queue, population size, generations, execution count, time, memory and cost;
- one active cycle per configured scope unless explicit safe concurrency is proven;
- context cancellation and immediate stop on tenant suspension or authorization revocation;
- retry classification and stop/continue policy for failures;
- durable job state and append-only audit events before unattended operation;
- explicit maximum promotion rate and cooldown;
- approval requirements by risk class and target environment;
- rollback target and tested rollback procedure;
- observable cycle status, selected parent, candidates, gate results, cost and failure reasons.

Do not introduce unattended periodic production evolution until durable jobs, recovery, idempotency, cancellation, isolation and promotion authorization are implemented and tested.

## 9. Acquisition is separate from improvement

Follow the priority order:
1. Improve an existing eligible agent/capability identity.
2. If no eligible improvement work exists, inspect explicit missing-capability requests.
3. Check the tenant registry and reject any identity that already exists.
4. Create a proposal and materialize a new identity only through the acquisition workflow.
5. Subject the acquired capability to normal validation, evaluation, approval and lifecycle controls.

Acquisition must not be used to evade a weak candidate result, duplicate an existing identity or bypass ownership and policy checks.

## 10. Implementation sequence — ten batches

| Batch | AgentBox delivery | Acceptance evidence |
|---:|---|---|
| 1 | Normalize source concepts and map them to AgentBox registry, execution, evaluation and security authorities | Reviewed naming map; no legacy product/package surface |
| 2 | Define tenant-scoped execution experience and provenance contract | Version/hash/profile/workload linkage; data-minimization rules |
| 3 | Define traceable lesson and experience-retrieval contract | Lessons reference source records; no direct behavior mutation |
| 4 | Define comparable fitness reports and evidence-aware work selection | Raw metrics, profile compatibility, sample/recency/uncertainty handling |
| 5 | Define bounded candidate population, mutation operators and materializer | Allowlisted mutable paths, immutable parent, deterministic seed and lineage |
| 6 | Integrate parent/candidate execution on the same pinned workload | Repeatable comparison with complete experiment records |
| 7 | Enforce independent hard gates, approval-controlled promotion and rollback | No aggregate-score bypass; atomic active pointer and audit |
| 8 | Implement a disabled-by-default, cancellable, bounded controller | Durable cycle state, concurrency guard, stop/recovery semantics |
| 9 | Add missing-capability acquisition as a separate fallback | Existing identity check and ordinary validation/promotion path |
| 10 | Add optional model-assisted lessons/proposals and operational observability | LLM cannot evaluate, approve, grant access or promote; full test/CI evidence |

The sequence is additive. A batch is not considered production-ready merely because its schema or unit tests pass.

## 11. Explicit non-goals and deferred work

- No arbitrary self-modifying source code, runtime binary mutation or unrestricted shell execution.
- No model-weight evolution or training pipeline is implied by configuration-genome evolution.
- No live multi-agent autonomous orchestration is created by the controller design.
- No production provider, sandbox, secret manager, durable queue or scheduler is assumed to exist.
- No cross-tenant learning or experience retrieval by default.
- No automatic production promotion without independent policy and approval.
- No blind import of thousands of Go files or their dependencies.

## 12. Runtime slices implemented

PR #19 adds tenant-scoped execution experience records, traceable proposed lessons, profile-version-pinned fitness selection with minimum sample counts, exact authorization and encrypted backup/restore coverage. See [Execution experience and learning records](execution-experience.md).

PR #20 adds deterministic bounded candidate generation from an immutable parent version. Registered operators adjust only bounded behavioural settings and selected numeric model parameters. Agent identity, tenant, tools and permissions remain unchanged; schema validation and parent lineage are required. See [Bounded candidate generation](candidate-generation.md).

The experience-to-execution/evaluation linkage remains caller-asserted and unverified. The existing evaluation service scores caller-submitted outputs; it does not execute a benchmark suite. Fitness selection is a triage signal, not a promotion gate. A tenant-scoped parent/candidate comparison record now verifies immutable candidate lineage, exact agent versions, completed evaluation-run ownership and profile-version compatibility, then records metric deltas against a caller-asserted workload reference/hash. The comparison remains unverified and advisory; it is not same-workload execution evidence or a hard-gate decision. Candidates remain unverified and cannot be promoted. A trusted runner, cryptographic workload attestation, mandatory independent gates, approval-controlled promotion, rollback and durable autonomous controller remain unimplemented.

## 13. Readiness and definition of done

The architecture is adopted as a design direction only. Runtime readiness requires, at minimum:

- persistent tenant-scoped experience and experiment records;
- pinned, repeatable parent/candidate workload execution;
- tested bounded mutation and immutable candidate materialization;
- evaluator-backed hard gates and regression comparisons;
- policy-authorized promotion and rollback;
- durable cancellable controller operation across restart;
- acquisition duplicate protection;
- model-proposal trust boundaries;
- backup/restore, tenant-isolation, authorization-denial and failure-recovery tests;
- live end-to-end validation with an actual configured provider and isolated execution environment.

Report design, code, unit tests, integration tests, end-to-end tests, security validation and production observation as separate readiness dimensions.
