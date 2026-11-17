# AgentBox enterprise context architecture map

## Purpose and compatibility rule

This document maps the Enterprise Context Engine (ECE) directive onto the **existing AgentBox implementation**. ECE is an additive native capability. It does not replace the agent runtime, API composition, persistence layer, identity, authorization, tenant lifecycle, evaluation or CI.

The implementation branch is based on the current open security stack. No existing PR is merged or rewritten. The first delivery keeps the existing Python/FastAPI application and shared SQLite database. PostgreSQL, graph databases, event brokers, analytical stores and new services are not introduced in this phase.

## Verified existing foundation

Repository inspected at `security/tenant-encrypted-backup-restore-10-batches`, head `1cdcc4b0b4c5bd7b8842aa71169881b688cafacd` (PR #14, open):

- **API composition:** `backend/app/main.py` creates the FastAPI app and composes the existing services.
- **Agent identity and versions:** `backend/app/registry.py` stores immutable tenant-scoped agent manifest versions, content hashes and parent lineage.
- **Execution:** `backend/app/execution.py` provides one bounded provider invocation, tenant-scoped idempotency and persisted execution records. The API currently registers only a deterministic fake provider; this is not a general autonomous orchestrator.
- **Evaluation:** `backend/app/evaluation.py` stores immutable evaluation profiles and runs and deterministically scores submitted outputs. It does not itself run a model.
- **Workflow contract:** `backend/app/workflow_contract.py` validates workflow graphs; it is not a workflow interpreter or durable workflow engine.
- **Capability contract:** `backend/app/capability_contract.py` validates capability declarations; it does not invoke tools or grant permissions.
- **Identity and authorization:** `backend/app/authentication.py`, `principal.py`, `authorization.py`, `authorization_policy.py` and `authorization_audit.py` provide OIDC verification, principals and deny-by-default exact-match policies.
- **Tenant authority:** `backend/app/tenant.py` and `tenant_registry.py` provide server-owned tenant lifecycle and audit.
- **Backup:** `backend/app/tenant_backup.py` provides encrypted tenant logical backup/restore for its enumerated tables. New tenant-owned ECE tables must be added to that inventory before they are considered covered by backup.
- **Validation and packaging:** `backend/app/validation.py`, `schemas/`, and `examples/` provide the current JSON Schema pattern.
- **Quality gate:** `.github/workflows/backend-ci.yml` runs Ruff and pytest.

## Capability mapping

| Required domain | Existing capability to reuse | Required additive implementation | Dependencies / gate |
|---|---|---|---|
| Agent Runtime and Agent Factory | Immutable manifest registry, clone/lineage, execution and evaluation | Register ECE specialists as ordinary AgentBox agents only when their contracts and tests exist | Keep generated-agent lifecycle governed; no self-granted permissions |
| Agent Orchestration and Coordination | Workflow graph contract and bounded execution service | Future orchestration/delegation runtime, typed agent task envelopes, scoped shared artifacts | Workflow contract is not execution; durable queue, cancellation and loop controls first |
| Enterprise Context Engine | Tenant registry, OIDC principal, policy evaluator, SQLite services | New tenant-scoped context entities, relationships, evidence, events and deterministic query API | Existing active-tenant gate + exact authorization for every operation |
| Enterprise Discovery | Read-only PostgreSQL catalog adapter plus bounded snapshot-to-ECE ingestion | Operator connector identity, secret resolution, live connection verification and durable discovery jobs | Current ingestion accepts externally produced metadata snapshots; no live API-managed connection or source attestation |
| System Intelligence | Agent registry and source research only | Repository/config/API inventory, dependency and change-impact analysis | Evidence-backed extraction; no source execution |
| Process Intelligence | Evaluation and workflow contracts only | Event ingestion, case-centric and object-centric process records, variants, conformance and KPI services | Explicit event schemas, time semantics, data minimization |
| Transformation Intelligence | Versioned artifacts and evaluation gates | Current/target models, fit-gap, migration dependency and validation records | Provenance and human approval before publication |
| Decision and Optimisation | Deterministic evaluation/scoring | Evidence-backed recommendations and constrained optimisation | Separate observed facts from inference and hypotheses |
| Workflow and Action Engine | Workflow/capability contracts, authorization | Later workflow interpreter and governed action gateway | Tool execution remains disabled until secrets, sandboxing, approval and postconditions |
| Security and Governance | OIDC, exact-match policies, tenant lifecycle, audit, encrypted backup | Context classification, evidence access controls, action approvals and connector scopes | No new bypass around existing authorization |
| Observability and Evaluation | Evaluation records and CI | Context quality metrics, connector health, provenance coverage and E2E tests | Do not confuse submitted-result evaluation with live execution evidence |
| Enterprise User Workspace | No frontend in verified tree | Future UI/API consumers over the same context API | No frontend stack introduced in ECE foundation |

## Enterprise context ontology v1

The first schema vocabulary is deliberately extensible and uses stable string identifiers rather than database-specific graph primitives.

- **Technology assets:** application, server, infrastructure, cloud_environment, database, api, microservice, repository, configuration, deployment_asset.
- **Business assets:** organization, department, employee, role, customer, supplier, product, material, financial_object, business_transaction.
- **Process assets:** business_process, activity, event, workflow, approval, business_rule, policy, exception, kpi.
- **Relationships:** typed directed edges with source and target entity-version references, attributes, confidence, assertion class and temporal validity.
- **Evidence:** source kind, source locator, source hash, observation time, validation state and collector identity. Raw source payloads and credentials are not copied into the context store.
- **Temporal history:** immutable entity and relationship versions, observed/recorded timestamps, and append-only context events.
- **Epistemic state:** observed_fact, inferred, ai_hypothesis and human_validated. Authorization decisions and actions remain separate security/runtime records; they are not treated as facts.

## Storage and integration decisions

1. Reuse the existing SQLite database path and tenant registry. ECE records are tenant-owned and keyed with tenant ID in every primary key and query.
2. Keep the logical context API independent of storage. A later PostgreSQL migration can preserve these contracts if concurrency, query or deployment requirements justify it.
3. Do not force all enterprise knowledge into a graph database. Relationships are represented as tenant-scoped typed records in the initial relational store.
4. Do not add a new service, event broker, vector database or analytics engine in this phase.
5. Do not make external connections or execute discovered code during metadata discovery.
6. Add ECE tables to the encrypted tenant backup inventory and test restore before declaring ECE data recoverable.
7. Keep the existing OIDC and active-tenant dependency and call the existing exact-match authorization evaluator for each ECE API action.

## Implementation sequence

### Foundation batch (this PR)
1. Verify and record the existing architecture and reuse boundaries.
2. Define the extensible enterprise entity ontology schema.
3. Define the relationship contract with confidence and temporal validity.
4. Define evidence/provenance metadata without copying source payloads.
5. Define change-event contract and epistemic classifications.
6. Implement tenant-scoped immutable entity versions in the existing SQLite store.
7. Implement typed tenant-scoped relationships with same-tenant endpoint/version enforcement.
8. Implement evidence attachment and append-only change events.
9. Implement bounded deterministic context queries and relationship traversal.
10. Expose the context API through existing OIDC, active-tenant and exact policy enforcement; include ECE data in tenant backup.

### Subsequent batches
- Discovery connector contract and read-only PostgreSQL metadata adapter.
- Semantic candidate extraction and evidence validation.
- Technical and business dependency maps.
- Process event ingestion and object-centric process model.
- Transformation current/target model and fit-gap records.
- Enterprise query/reasoning agents.
- Governed workflow execution, approval and action gateway.
- Self-maintaining discovery and proposed context updates.

## First end-to-end demonstration

The first live demonstration should connect to an explicitly configured read-only PostgreSQL source, discover schemas/tables/columns/indexes/foreign keys, produce evidence-backed candidate entities and relationships, validate them, and publish a proposed context snapshot for approval. It must not write to the source database. The current foundation establishes the target context contracts and tenant boundary; the PostgreSQL connector is a later implementation batch.

## Acceptance and readiness rules

Every batch adds unit and integration tests, tenant isolation tests, policy-denial tests, provenance tests and CI verification. A green Ruff/pytest run is not evidence of a live PostgreSQL connector, a running autonomous agent, a secure action sandbox or production deployment.

Readiness must be reported separately as implemented, unit tested, integration tested, end-to-end tested, security validated, production deployed and production observed. No production-ready claim is made by this architecture map.


## Execution experience and autonomous improvement integration

The first runtime slice now persists tenant-scoped execution experience records and proposed lessons, and provides evidence-aware fitness selection for an exact evaluation profile version. These records are minimized, included in encrypted tenant backup/restore, and remain marked caller-asserted/unverified until a trusted runner can attest the workload-to-execution-to-evaluation chain. Fitness selection is not promotion authority.

## Autonomous improvement integration

The reviewed self-evolving capability platform is adopted as an **AgentBox Autonomous Improvement Controller**, not as a separate product, service namespace or Go runtime. It extends the Agent Evolution Engine and shared evolution contracts.

- Agent identity, immutable versions and lineage remain owned by the existing AgentBox registry.
- Execution and evaluation remain owned by the existing AgentBox services. The future improvement service must pin one benchmark and run parent and candidate versions against the same workload.
- Execution experience and derived lessons are tenant-scoped evidence. Lessons can inform a proposal but cannot directly mutate an agent.
- Candidate generation is bounded to allowlisted manifest/configuration fields and registered materializers. Parent artifacts remain immutable.
- Independent hard gates precede promotion. The registry's active-version pointer changes only after authorization and required approval; rollback reactivates a prior immutable version.
- A cancellable controller selects eligible work from the existing agent portfolio. Missing-capability acquisition is a distinct fallback and must reject duplicate identities.
- Optional model assistance may propose lessons or configuration changes, but cannot evaluate, approve, grant permissions, access secrets or promote.
- No new database, broker, graph store, microservice or runtime is introduced by this design.

The current execution API's deterministic fake provider and submitted-output evaluation service do not yet constitute live autonomous improvement. The controller remains a future implementation until durable experience/experiment storage, repeatable parent/candidate execution, bounded mutation, hard gates, approval, rollback, durable scheduling, isolation and end-to-end tests are present.

See [Autonomous Improvement Controller](engines/autonomous-improvement-controller.md) for the source-derived design and ten-batch implementation sequence.
