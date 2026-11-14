# AgentBox Master Architecture

**Document status:** Canonical architecture authority  
**Version:** 1.5  
**Updated:** 2026-11-14  
**Scope:** AgentBox platform, backend, runtime, security, data, and dual frontend strategy

> This document defines the intended architecture and decision boundaries for AgentBox. It does not claim that every described capability is implemented. The repository's implementation status, CI results, and production-readiness evidence must be reported separately from target architecture.

## 1. Product mission

AgentBox is a standalone environment for creating, configuring, versioning, executing, testing, evaluating, improving, governing, and operating AI agents and agent-based systems.

The platform should support an individual developer through an enterprise deployment without splitting into separate products or duplicating core authorities.

The lifecycle target is:

`define → configure → version → execute → observe → evaluate → learn → generate candidate → compare → approve → promote or rollback`

Autonomous improvement is evidence-driven and bounded. An agent or candidate must never gain permissions, tools, credentials, tenant access, or production authority merely because it was generated or scored well.

## 2. Architectural decisions

1. **One AgentBox platform.** Flutter and Next.js are two clients of the same platform, not separate products.
2. **One backend authority.** The existing Python/FastAPI application remains the authority for identity, tenant context, authorization, agent registry, execution, evaluation, experience, evolution, audit, and persistence.
3. **Contract-first integration.** OpenAPI, JSON Schemas, and versioned event contracts define the frontend/backend boundary.
4. **Additive evolution.** New capabilities extend existing services and contracts. Do not replace working architecture or introduce parallel authorities without an explicit architecture decision.
5. **Security by default.** Tenant identity and permissions are derived and enforced server-side. Clients never decide their own tenant authority or privileges.
6. **Immutable artifacts.** Agent versions, evaluation profiles, candidates, and evidence records preserve version identity and lineage.
7. **Evidence before autonomy.** Caller-asserted or synthetic evidence is not production proof. Promotion requires trusted execution, reproducible workloads, independent evaluation, mandatory gates, and an auditable approval decision.
8. **Portable deployment.** Keep the core runtime deployable on a modest Linux host first; scale-out infrastructure is introduced only when supported by workload and operational requirements.

## 2.1 Five architectural pillars and lifecycle authority

AgentBox implementation is governed by five connected pillars. These are architectural boundaries, not five separate products or deployable services.

1. **AI Intelligence** — intent interpretation, context assembly, cognition, reasoning, planning, decision, reflection, memory and learning.
2. **Agent Factory** — agent genomes and manifests, immutable versions, composition, mutation, lineage, evaluation, promotion and rollback.
3. **Application Factory** — capability composition, workflow interpretation, application assembly, packaging, deployment and lifecycle governance.
4. **Execution Engine** — bounded agent loops, orchestration, capability/tool invocation, multi-agent delegation, checkpoints, observation and recovery.
5. **Platform Foundation** — identity, tenancy, authorization, persistence, audit, provider/secret adapters, sandboxing, observability, deployment and both frontend clients.

The Platform Foundation supports and governs the other four pillars; it is not the product's primary purpose. Infrastructure work must be prioritized by the higher-level agent/intelligence flow it enables.

The canonical agent lifecycle is:

`Intent → Context → Cognition → Capability → Responsibility → Execution → Observation → Verification → Memory`

Each transition must have a typed contract, durable state where required, explicit provenance, server-side authorization, bounded failure semantics and observable evidence. The lifecycle is an end-to-end target; the existence of a schema or isolated service does not mean its stage is operational.

### Engine boundaries

Keep these domains distinct while reusing shared artifact, lineage, evaluation, policy, audit and approval services:

- **Cognition Engine:** reasoning, planning, decision and reflection; distinct from a provider HTTP adapter.
- **Agent Evolution Engine (AEE):** evolves immutable agent configuration/genomes; does not mutate foundation-model weights.
- **Retrieval Evolution Engine (REE):** evolves retrieval, ranking and query strategy against versioned corpus/query-set benchmarks.
- **Model Genetics Engine (MGE):** tracks model genomes, ancestry and compatibility; neural-weight reproduction remains experimental until independently implemented and validated.
- **Cognitive Evolution:** evolves bounded cognitive strategies or configurations under dedicated evaluation; it is not synonymous with manifest mutation.
- **Knowledge Evolution:** governs evolution of knowledge representations and retrieval/curation strategies while preserving source provenance and immutable source evidence.
- **Autonomous Improvement Controller:** coordinates the evidence loop across eligible engines; it is not an evaluator, policy authority, credential broker or promotion authority.

The detailed repository conformance and implementation gaps are tracked in [the 2026-11-14 architecture audit](docs/architecture-conformance-audit-2026-11-14.md). That audit is a snapshot; this master document remains the canonical target.

## 2.2 Evidence validation and provenance governance

Enterprise Context evidence submission is untrusted by default. Evidence records are immutable and begin as `unverified`; submitters cannot set a validated or rejected state. A separately authorized reviewer must be distinct from the recorded submitter. Each evidence record receives at most one terminal review (`validated` or `rejected`), stored in an append-only review table and represented by an append-only context event. Review decisions are tenant-scoped and cannot be edited or reversed in place; corrected evidence must be submitted as a new record with new provenance.

Validation requires a source SHA-256 digest and an independent reviewer confirmation matching that digest. For PostgreSQL catalog snapshots, an optional Ed25519 connector attestation now cryptographically binds the authenticated tenant, exact source locator, snapshot digest, discovery time, key ID and signing time to a server-provisioned trusted public key. Unsigned ingestion remains unverified. A valid connector signature establishes key possession and snapshot integrity, not database truth, least-privilege source-role configuration or human acceptance; evidence remains unverified until the separate reviewer decision. Trust keys are process configuration today; managed registration, rotation/revocation, hardware-backed private keys and live source E2E remain production gates. Context assembly exposes only evidence whose effective review status is `validated`; unverified and rejected records remain excluded.

## 2.3 Cognitive runtime contract baseline

The cognitive runtime now has a typed lifecycle event envelope (`schemas/cognitive-event-v1.schema.json`), deterministic validator (`backend/app/cognitive_contract.py`), and a tenant-scoped SQLite run journal (`backend/app/cognitive_runtime.py`). Authenticated APIs create runs bound to an existing immutable agent version, append ordered events, and read tenant-scoped run/event history. Events are append-only, idempotent, bounded, stage-validated, and tied to server-derived tenant/actor identity. Idempotency keys are stored only as SHA-256 digests; event payloads reject reserved authority, credential and executable-field names. Verification and accepted memory require verified evidence references; capability selection and responsibility decisions require explicit references.

This remains a state/journal foundation, not a cognitive engine. It does not reason, plan, invoke capabilities, execute agents, attest evidence, consolidate memory, or provide distributed persistence. Existing identity, tenant, registry, authorization, execution, experience, enterprise-context and audit services remain the authorities. See [Cognitive Runtime Contracts](docs/runtime/cognitive-runtime-contracts.md).

## 3. Platform topology

```text
                         AgentBox Platform
                                |
             +------------------+------------------+
             |                                     |
       Flutter Client                        Next.js Client
       Dart / Flutter                         TypeScript / React
       Mobile + Desktop                       Web Console
             |                                     |
             +------------------+------------------+
                                |
                    Shared API / Contract Boundary
                    OpenAPI + JSON Schema + Events
                                |
                       Python / FastAPI Core
                                |
       +------------------------+-------------------------+
       |           |            |            |            |
    Identity    Registry     Runtime      Evaluation    Context
    & Tenant    & Lineage    & Tools      & Evidence    Engine
       |           |            |            |            |
       +------------------------+-------------------------+
                                |
                 Persistence / Audit / Backup / Queue
                                |
                 Provider and Infrastructure Adapters
```

The diagram is a target logical architecture. It does not imply that every adapter, queue, runtime, or subsystem is already implemented.

## 4. Dual frontend strategy

AgentBox will maintain two first-class frontend applications.

### 4.1 Flutter — cross-platform operational client

**Primary role:** mobile-first and device-oriented access to AgentBox.

Target platforms:
- Android
- iOS
- Desktop (Windows, macOS, and Linux), introduced where there is a validated operational use case

Primary capabilities:
- Agent and run status overview
- Start, stop, and monitor permitted executions
- Notifications and approval requests
- Operational incident and task views
- Agent inventory and version inspection
- Basic agent configuration and controlled actions
- Offline-friendly read views and safely queued user intent where the API supports reconciliation
- Device-native capabilities such as secure local storage, push notifications, camera, and file selection when required

Flutter is not a second business-logic layer. It presents capabilities exposed by AgentBox APIs and applies client-side validation only as a usability aid.

### 4.2 Next.js — web console and engineering workspace

**Primary role:** browser-first administration, authoring, engineering, and observability.

Primary capabilities:
- Agent Studio: create, configure, inspect, clone, and version agents
- Workflow and capability design surfaces
- Evaluation profile and benchmark management
- Execution traces, logs, and observability explorers
- Candidate comparison and evolution history
- Tenant, user, role, policy, and integration administration
- Approval queues, audit history, and operational dashboards
- Documentation, developer tools, and API exploration

Next.js is the primary full-featured workspace for complex authoring and administration. Server-side rendering and server components may be used for presentation and secure session integration, but domain authority and business rules remain in the FastAPI backend.

### 4.3 Capability ownership

| Capability | Flutter | Next.js |
|---|---|---|
| Agent monitoring | First-class | First-class |
| Execution controls | First-class | First-class |
| Agent authoring | Guided/basic | Full workspace |
| Workflow visual designer | Optional compact view | Primary |
| Evaluation and candidate comparison | Summary view | Full analysis |
| Administration and policy configuration | Operational subset | Primary |
| Approval and notifications | First-class | First-class |
| Deep logs and trace exploration | Focused views | Primary |
| Device-native integrations | Primary | Browser capabilities only |

This is a prioritization matrix, not an artificial restriction. Both clients must respect the same server-side authorization rules.

## 5. Shared frontend contract architecture

The clients integrate through a shared, versioned contract boundary.

### Contract sources
- FastAPI-generated OpenAPI document for HTTP operations
- Authoritative JSON Schemas for agent manifests, evaluation profiles, and other structured artifacts
- Versioned event schemas for asynchronous updates and notifications
- Explicit API compatibility and deprecation policy

### Generated and shared assets
- TypeScript API client and types generated from OpenAPI
- Dart API client and models generated from OpenAPI
- Schema-derived validation where practical
- Shared semantic design tokens: color roles, spacing scale, typography roles, status vocabulary, and interaction principles
- Shared fixtures and contract tests used by both clients

Do not manually maintain duplicate API models when they can be generated from the authoritative contract. Do not share platform-specific UI components across Flutter and React; share semantic tokens, interaction rules, API contracts, and test fixtures instead.

### Client/backend boundary
- Clients submit user intent and render server-authoritative results.
- Backend validates every request, resource relationship, tenant boundary, and permission.
- Client-side feature flags may hide unavailable functionality but never grant access.
- Long-running operations use durable backend job/execution identifiers and server-reported state.
- Realtime updates may use a supported event transport; polling remains an acceptable first implementation where no event service exists.

## 6. Identity, tenant, and authorization

The existing AgentBox OIDC and authorization foundations remain authoritative.

Requirements:
- OIDC authentication and validated server-side principals
- Explicit active-tenant lifecycle and server-owned tenant context
- Exact-match, deny-by-default authorization
- Resource-level checks on every protected operation
- Tenant-scoped persistence and tenant-composite identity constraints
- Auditable administrative and privileged actions
- Short-lived access credentials and secure refresh/session handling
- No secrets embedded in frontend bundles, mobile binaries, source maps, or local configuration committed to source control

Web sessions must use secure browser session practices, preferably HttpOnly, Secure, appropriately SameSite cookies where the chosen OIDC flow supports them. Flutter must use platform-protected secure storage for credentials. Neither client may trust a tenant ID supplied by the user interface as proof of tenant membership. Both clients use OIDC Authorization Code Flow with PKCE. The web client uses a server-managed BFF session; Flutter uses the system browser and a maintained AppAuth implementation. The provider remains replaceable and is selected through deployment configuration, not product-specific code. See [the OIDC client integration contract](docs/security/oidc-client-integration-contract.md).

## 7. Backend and domain architecture

The current Python/FastAPI backend remains the modular core. Keep clear domain boundaries while avoiding premature microservice extraction.

Core domains:
1. Identity, principal, tenant lifecycle, and authorization
2. Agent manifest validation, registry, immutable versions, and lineage
3. Execution orchestration and provider adapters
4. Tool and capability registry with permission-aware invocation
5. Workflow contracts and, in a later stage, durable workflow execution
6. Evaluation profiles, trusted benchmark runner, scoring, and hard gates
7. Execution experience, evidence, lessons, and fitness analysis
8. Candidate generation and autonomous improvement controller
9. Enterprise Context Engine (ECE)
10. Audit, backup/restore, operations, and observability

The ECE remains an additive domain over the existing runtime, persistence, identity, and authorization foundations. It is not a replacement backend or a separate product.

## 8. Agent execution and autonomous improvement

The target improvement loop is:

`approved parent → trusted workload execution → immutable experience → proposed lesson → bounded candidate → same-workload comparison → hard gates → approval → promotion/rollback`

Mandatory safeguards:
- Execute untrusted or generated code only inside a genuine isolation boundary.
- Bind each experiment to immutable parent and candidate hashes, workload/profile versions, provider/model configuration, and execution policy.
- Compare parent and candidate on the same pinned workload.
- Separate objective measurements from caller assertions and model-generated explanations.
- Enforce security, correctness, quality, latency, cost, and policy gates independently.
- Require explicit approval for production promotion unless a separately governed policy authorizes a narrowly bounded automatic promotion.
- Preserve complete lineage and support rollback to a known immutable version.

Candidate generation alone is not autonomous evolution. Evaluation of caller-submitted outputs alone is not trusted benchmark execution.

### 8.1 Isolated execution adapter (implementation in progress)

A provider-neutral sandbox boundary is being added as a separate backend service. The
first adapter uses Docker with the gVisor `runsc` runtime and requires exact,
SHA-256-digest-pinned image allowlisting. It applies no-network/no-IPC isolation,
read-only root filesystem, bounded tmpfs, non-root execution, dropped Linux
capabilities, no-new-privileges, and CPU/memory/process/time/input/output limits.
It passes argv directly without shell interpolation and does not mount host paths.

The Docker daemon, host, gVisor installation, and approved image supply chain remain
trusted infrastructure. This adapter is not VM-grade isolation and is not a claim
that hostile multi-tenant execution is production-ready. It is not yet connected to
the public execution API, candidate evaluator, or autonomous controller. A live
worker deployment and end-to-end isolation tests remain mandatory gates. See
[the sandbox runtime foundation](docs/security/sandbox-runtime-foundation.md).


## 9. Data, persistence, and operations

The current SQLite persistence layer remains the initial implementation. Its limitations must be acknowledged: it is suitable for the bounded single-instance stage, not assumed to be the final high-concurrency enterprise storage architecture.

Evolution path:
- Preserve repository/service interfaces and migration discipline.
- Define and test the supported production database target before multi-instance deployment.
- Use durable queues and worker ownership for long-running jobs before relying on multi-process execution. The durable job state machine, lease, cancellation, recovery, idempotency, tenant isolation, and audit requirements are specified in [the execution-job lifecycle contract](docs/runtime/durable-execution-job-lifecycle.md). This job service remains separate from synchronous provider invocation.
- Keep tenant backup/restore inventories synchronized with every new tenant-owned table.
- Encrypt backups and define key custody, rotation, restore drills, and recovery objectives.
- Add structured logs, metrics, traces, audit events, health/readiness checks, and operational alerts.
- Avoid introducing a broker, graph database, analytical store, or microservice solely for architectural appearance.

## 10. Repository organization

Target organization (adapt to existing repository conventions without moving working code unnecessarily):

```text
AgentBox/
├── backend/                 # Python/FastAPI core and domain services
├── frontend/
│   ├── flutter/             # Flutter mobile and optional desktop apps
│   └── nextjs/              # Next.js web console
├── contracts/
│   ├── openapi/             # Versioned OpenAPI snapshots or generated source
│   ├── schemas/             # Shared JSON Schemas
│   └── events/              # Versioned event contracts
├── design-system/
│   └── tokens/              # Platform-neutral semantic design tokens
├── schemas/                 # Existing authoritative schemas; migrate only by explicit decision
├── examples/
├── docs/
│   ├── engines/
│   ├── security/
│   └── operations/
├── research/
├── requirements/
├── infrastructure/
└── .github/workflows/
```

The existing `schemas/` directory remains authoritative until a deliberate migration establishes `contracts/schemas/` as its replacement. Do not create competing copies of the same schema.

## 11. Quality engineering and CI

Backend and frontend pipelines are independently testable and jointly release-gated.

### Backend
- Ruff and static checks
- Unit and API tests
- Schema and migration tests
- Tenant-isolation and authorization negative tests
- Concurrency, idempotency, and recovery tests
- Provider-adapter and trusted-runner integration tests

### Next.js
- TypeScript type checking and lint
- Component and route tests
- API contract compatibility tests
- Accessibility checks
- Production build
- Browser end-to-end tests

### Flutter
- Dart formatting and analysis
- Unit and widget tests
- API contract compatibility tests
- Platform build checks for supported targets
- Accessibility and secure-storage tests
- Device/emulator end-to-end tests

### Cross-platform
- Shared contract fixtures
- Authentication and tenant-boundary scenarios
- Consistent permission-denial behavior
- Execution lifecycle and event-state consistency
- Release compatibility checks against the deployed backend API

A green CI workflow demonstrates only the checks that actually ran. It does not prove production security, live provider operation, deployment correctness, or operational recovery.

## 12. Implementation sequence

The frontend strategy is introduced without displacing backend and security work.

| Stage | Deliverable | Acceptance evidence |
|---|---|---|
| 1 | Canonical architecture and API contract inventory | Reviewed master architecture and endpoint/schema inventory |
| 2 | Frontend workspace foundations | Flutter and Next.js app skeletons, independent CI, documented local run |
| 3 | Authentication and tenant integration | OIDC login/session flows and negative tenant-isolation tests |
| 4 | Shared client generation | Reproducible Dart/TypeScript clients from the same OpenAPI contract |
| 5 | Next.js Agent Studio foundation | Agent list, details, version view, and authorized create/clone flow |
| 6 | Flutter operational foundation | Login, agent inventory, execution status, and notifications |
| 7 | Shared operational workflows | Consistent execution controls, approvals, and audit visibility |
| 8 | Advanced engineering surfaces | Workflow designer, evaluation explorer, candidate comparison |
| 9 | Release hardening | End-to-end, security, accessibility, deployment, and recovery evidence |

Backend runtime milestones (trusted provider, sandbox, experiment engine, autonomous controller, governed promotion) remain separate acceptance gates and must not be marked complete merely because a frontend can display their intended screens.

## 13. Production readiness and reporting

Every implementation iteration must distinguish:
- **Implemented:** code exists on a named branch/commit.
- **CI verified:** named workflow and checks passed on that commit.
- **Integration verified:** real services and clients were exercised together.
- **Operationally verified:** deployment, monitoring, backup/restore, security, and recovery have evidence.
- **Production ready:** all mandatory release gates have passed.

Report main-branch capability separately from open feature-branch work. Do not count an unmerged PR as deployed or available on main. Do not infer readiness percentages from documentation volume or green unit tests.

## 14. Architecture change control

- This file is the canonical master architecture.
- Requirements, domain specifications, implementation plans, and tests must trace back to this document.
- A lower-level document may refine a decision but must not silently contradict or replace a master decision.
- Any material architecture change must record its rationale, impact, migration path, security implications, and acceptance tests.
- Preserve source provenance for recovered concepts and code; normalize all shipped product, package, API, CLI, configuration, and internal identities to AgentBox.
- Do not remove useful existing functionality or rename established interfaces without explicit compatibility planning.

## 15. Current implementation reality (2026-11-14)

The repository currently has a bounded Python/FastAPI backend and meaningful registry, evaluation, execution-record, OIDC/tenant/authorization, encrypted backup, ECE, execution-experience, and bounded candidate-generation work across the main branch and stacked feature branches. The provider/runtime feature branch includes bounded OpenAI-compatible chat-completions integration, strict request/response structure and usage validation, finite JSON serialization, request/response size limits, timeout and pricing type checks, sanitized failures, and redirect-safe bearer credential handling. CI evidence is commit-specific: the provider branch had a fully green backend, Flutter, and Next.js run before the latest hardening; a later Ruff failure for boolean pricing validation was corrected, and CI is running again on the corrected head. This is branch-level CI evidence, not a production deployment.

Important limitations remain:
- The execution API retains a deterministic fake provider for tests and includes an optional environment-configured OpenAI-compatible chat-completions adapter on the unmerged provider feature branch. Adapter and worker integration tests use mocked HTTP only; no live credentials, live model call, provider billing, pricing verification, production latency, retry semantics, or production real-model operation is established. The provider adapter rejects malformed usage metrics and only reports cost when both explicit token rates are configured.
- The evaluation service scores submitted outputs; it does not execute benchmark workloads.
- Execution-experience linkage is caller-asserted and remains unverified.
- Candidate generation creates unverified immutable candidates; it does not execute, approve, or promote them.
- A gVisor-backed sandbox adapter and policy tests exist on an unmerged feature branch, but it is not wired into execution or deployed on a live worker. The SQLite-backed durable job service and FastAPI integration are implemented on stacked unmerged branches. A separate Python worker process now consumes allowlisted provider-invocation jobs, verifies tenant-scoped workload identity/hash/provider binding, delegates to the existing bounded provider adapter, heartbeats leases, and records completion or fail-closed errors. Sandbox workloads remain explicitly rejected by this worker. These worker changes are under review and CI evidence must be tied to the exact PR head. The worker is a single-instance SQLite process, not a distributed queue; live provider credentials, cancellation of in-flight synchronous calls, automated recovery scheduling, per-tenant/global concurrency limits, PostgreSQL storage, production queue operations, and live recovery/security tests remain incomplete. Authorization decisions/job events are not yet joined in one atomic audit transaction. The integrated production sandbox, durable autonomous controller, trusted same-workload experiment runner, and governed promotion/rollback are not complete.
- SQLite is the current persistence implementation; production multi-instance storage and operations are not established.
- Flutter and Next.js foundations, bearer-token API transports, route inventory, OpenAPI export, and provider-configurable client OIDC flows are implemented on stacked feature branches, not yet merged to main. No identity provider is selected or deployed. Native redirect registration, real token validation against a deployed issuer/JWKS, client-to-API end-to-end tests, and production session/revocation operations remain incomplete.

This status must be refreshed against the exact repository commit and CI evidence during each readiness assessment.


## CI execution policy

- GitHub Actions runs automatically on pushes to `main` and when a pull request is opened, reopened, or marked ready for review (subject to workflow path filters). It does not run on every PR synchronize/push event.
- Feature-branch pushes do not start CI automatically; use the workflow's manual `workflow_dispatch` action for consolidated latest-head validation (the working cadence is one run after each 10 implementation batches, and before merge).
- Run the repository's local backend, Next.js, and Flutter checks during implementation batches. Record which checks were actually run; local checks do not replace the required PR CI run.
- This policy reduces redundant per-commit CI while preserving integration-branch and pull-request validation.


## Synchronous execution crash recovery

The SQLite synchronous execution service now fences leftover `running` records as `interrupted` on exclusive process startup, using error code `execution_interrupted_ambiguous_outcome`. Same-key replay returns that terminal ambiguous record and never silently invokes a provider again. This avoids duplicate external calls/charges after a crash, but requires operator reconciliation and a new idempotency key for a deliberate retry. The recovery assumes one API process owns this SQLite store; multi-instance execution requires a database-backed lease/ownership design first.


## SQLite connection lifecycle

The synchronous execution store now uses a connection subclass that retains SQLite transaction commit/rollback behavior while closing each short-lived connection on context exit. The shared in-memory database keeper remains intentionally open for the service lifetime. This change reduces descriptor/connection leakage under repeated API calls; it does not alter the documented single-instance SQLite deployment boundary.


## Durable-job SQLite connection lifecycle

The durable execution-job store now closes each short-lived SQLite connection after its transaction context exits, while preserving commit/rollback semantics. Its shared in-memory database keeper remains open for the service lifetime. This is connection-resource hardening only; the durable queue remains single-instance SQLite and is not a distributed worker backend.


## Authorization-audit SQLite connection lifecycle

The append-only authorization audit store closes each short-lived SQLite connection after its transaction context exits, retaining commit/rollback semantics. Its shared in-memory keeper remains open for the store lifetime. Audit immutability and persistence semantics are unchanged; this hardening does not provide atomic coupling with other service transactions.


## Durable-job store shutdown lifecycle

The durable execution-job service exposes an idempotent `close()` operation. It releases the shared in-memory SQLite keeper and rejects subsequent connections after shutdown; callers owning the service must invoke it during application shutdown. File-backed stores also enter the closed state, preventing accidental reuse after lifecycle termination.


## Durable-job shutdown integration

The API registers the durable execution-job store's idempotent close operation with its FastAPI shutdown event. The standalone worker also closes the store in a `finally` block after polling stops or raises. This ensures the shared in-memory SQLite keeper is released by both supported process entry points; it does not close unrelated stores or alter the single-instance deployment constraint.


## Worker heartbeat shutdown ordering

A worker now waits for its heartbeat thread to exit before returning from a claimed job. This prevents the process shutdown path from closing the durable-job store while a heartbeat database operation is still in flight. The wait is intentionally bounded by the heartbeat operation's own SQLite busy timeout rather than a shorter arbitrary thread-join timeout.


## API-owned SQLite store shutdown

The API shutdown callback now closes all owned SQLite stores: durable jobs, synchronous executions, experience, enterprise context, evaluation, agent registry, tenant registry, and authorization audit. Each store exposes an idempotent close operation, releases its shared in-memory keeper when present, and rejects new connections after closure. The standalone worker invokes the same aggregate cleanup after its polling loop exits. This is process-resource cleanup, not a multi-process database ownership or coordination mechanism.


The lifecycle regression suite also constructs each store against a shared-cache in-memory SQLite database, verifies that repeated shutdown closes the keeper exactly once, and confirms that post-shutdown connection attempts fail closed.


Tenant backup restore opens the source with no-follow semantics where supported, verifies the opened descriptor is a regular file without blocking on special files, and enforces the 512 MiB limit while reading. This avoids the prior check-then-open symlink race and bounds the bytes parsed as an envelope.


The offline tenant administration CLI closes its `TenantRegistry` in a `finally` block after every command, including command failures. This releases its shared in-memory keeper and prevents repeated in-process CLI invocations from retaining SQLite resources.


Tenant CLI database preflight uses an explicit `try/finally` close for its read-only SQLite connection; connection context managers alone do not close SQLite handles. A regression test verifies cleanup even when the database is rejected as uninitialized.


Tenant backup restore validates exact integer version fields (excluding booleans), key identifier syntax, encoded-field types, and the complete payload top-level field set before applying data. This prevents Python's `True == 1` coercion from accepting malformed version markers.

Backup payload validation also restricts every table cell to SQLite-bindable scalar values, rejects non-finite floats, and bounds integers to SQLite's signed 64-bit range before opening the restore transaction.


## Cognitive context assembly

The cognitive runtime includes a deterministic context assembly service backed exclusively by the existing tenant-scoped Enterprise Context authority. The service produces a schema-validated, content-addressed snapshot, binds graph edges to exact selected entity versions, excludes expired entities and relationships, and defaults to observed/human-validated assertions. Inferred assertions require explicit opt-in; AI hypotheses are excluded. Raw attributes are not copied into the snapshot.

Only validated evidence can be included. Since the current context evidence API records evidence as unverified and has no authorized validation path, the assembled snapshot does not yet contain validated evidence. Context snapshots are bounded to 48 KiB and embedded in an append-only lifecycle event. The authenticated endpoint requires `cognition.context.assemble` and the existing tenant-context entity, relationship and evidence read grants; tenant identity remains server-derived. Snapshot references are tenant-bound.

This adds context packaging, not reasoning or retrieval-augmented generation. It does not attest sources, invoke capabilities, or execute an agent.


## PostgreSQL connector provenance attestation

The catalog ingestion path optionally verifies Ed25519 attestations against `AGENTBOX_POSTGRESQL_PROVENANCE_KEYS`, a server-owned mapping of key IDs to base64 raw public keys. The signature binds tenant identity from the authenticated principal, source locator, snapshot hash, discovery timestamp, key ID and signing time. Unknown keys, malformed signatures, altered snapshots, tenant/source mismatch and signatures older than 15 minutes fail closed. Private keys remain with the connector. This cryptographic layer is separate from human evidence review and does not assert source database correctness or replace source-role verification. See [PostgreSQL snapshot ingestion](docs/postgresql-discovery-context-ingestion.md).
