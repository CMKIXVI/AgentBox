# AgentBox Master Architecture

**Document status:** Canonical architecture authority  
**Version:** 1.2  
**Updated:** 2026-11-13  
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

The existing AgentBox OIDC and authorization foundations remain authoritative. The backend verifier validates issuer, audience, signature, time claims, and the configured tenant claim. The Next.js and Flutter session ports and UI gates are provider-neutral adapters only; they fail closed for missing or expired sessions and recheck at the 30-second expiry safety boundary, but do not implement login or authorization. Next.js includes a standalone root-relative return-target validator and tested BFF cookie/CSRF policy helpers for future authentication integration; none is wired to a callback or route handler. A maintained OIDC SDK or reviewed BFF must own Authorization Code + PKCE, callback validation, refresh, logout, and secure credential storage. See [the OIDC client/session contract](docs/security/oidc-client-session-contract.md).

Requirements:
- OIDC authentication and validated server-side principals
- Explicit active-tenant lifecycle and server-owned tenant context
- Exact-match, deny-by-default authorization
- Resource-level checks on every protected operation
- Tenant-scoped persistence and tenant-composite identity constraints
- Auditable administrative and privileged actions
- Short-lived access credentials and secure refresh/session handling
- No secrets embedded in frontend bundles, mobile binaries, source maps, or local configuration committed to source control

Web sessions must use secure browser session practices, preferably HttpOnly, Secure, appropriately SameSite cookies where the chosen OIDC flow supports them. Flutter must use platform-protected secure storage for credentials. Neither client may trust a tenant ID supplied by the user interface as proof of tenant membership.

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

## 9. Data, persistence, and operations

The current SQLite persistence layer remains the initial implementation. Its limitations must be acknowledged: it is suitable for the bounded single-instance stage, not assumed to be the final high-concurrency enterprise storage architecture.

Evolution path:
- Preserve repository/service interfaces and migration discipline.
- Define and test the supported production database target before multi-instance deployment.
- Use durable queues and worker ownership for long-running jobs before relying on multi-process execution.
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

## 15. Current implementation reality (2026-11-13)

The repository currently has a bounded Python/FastAPI backend and meaningful registry, evaluation, execution-record, OIDC/tenant/authorization, encrypted backup, ECE, execution-experience, and bounded candidate-generation work across the main branch and stacked feature branches.

Important limitations remain:
- The current execution API registers a deterministic fake provider; no production real-model provider is established.
- The evaluation service scores submitted outputs; it does not execute benchmark workloads.
- Execution-experience linkage is caller-asserted and remains unverified.
- Candidate generation creates unverified immutable candidates; it does not execute, approve, or promote them.
- A genuine code-execution sandbox, durable autonomous controller, trusted same-workload experiment runner, and governed promotion/rollback are not complete.
- SQLite is the current persistence implementation; production multi-instance storage and operations are not established.
- Flutter and Next.js application shells, shared API transports, and provider-neutral session-reader ports are implemented on feature branches. The ports are not live OIDC login implementations; no provider, callback, token refresh, Next.js BFF, or native secure-storage adapter is configured.

This status must be refreshed against the exact repository commit and CI evidence during each readiness assessment.
