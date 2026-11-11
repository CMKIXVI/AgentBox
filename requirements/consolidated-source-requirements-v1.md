# AgentBox — Consolidated Source-Derived Requirements Catalogue

Status: baseline v1.0  
Date: 2026-11-11  
Source basis: `chatgpt_22-26.zip`, 2,570 Markdown exports reviewed in batches 001–011.  
Repository: `CMKIXVI/AgentBox`

## 1. Purpose and evidence policy

This catalogue consolidates recurring and distinctive requirements from the 11 batch reviews into one traceable baseline for AgentBox. It is a synthesis of the user's source material, not a claim that every idea in the archive is a current product commitment.

Evidence labels:
- **Direct:** clearly requested in one or more source conversations.
- **Repeated:** independently appears across multiple source conversations/batches.
- **Synthesis:** a platform requirement inferred by combining direct source requests.
- **Research:** exploratory idea without sufficient evidence to make it a launch commitment.

Priority labels:
- **P0 — platform foundation:** required for a coherent, safe first usable platform.
- **P1 — first product expansion:** high-value capability after the foundation is stable.
- **P2 — later deployment/ecosystem:** useful but should not block the first release.
- **R — research/validation:** requires feasibility, standards or market validation before commitment.

Source traceability points to the batch review and names representative original archive files. The batch reviews preserve the more detailed source discussion and exact source paths.

## 2. Product definition

**AgentBox is a governed factory and operating platform for creating, composing, testing, evaluating, publishing, exporting, deploying and operating reusable capabilities, agents, workflows and applications.**

The platform supports multiple deployment profiles—cloud, self-hosted, hybrid and local/offline—while applying different trust, resource and network policies to each.

Core conceptual distinctions:
- **Capability:** a typed, permissioned unit of work; may be deterministic or model-backed.
- **Action/tool:** an executable operation exposed through a capability contract, connector or device adapter.
- **Agent:** a bounded reasoning/planning package that may select among permitted capabilities.
- **Workflow:** a versioned process graph defining steps, events, conditions, loops, approvals, retries and compensation.
- **Application:** a package combining capabilities, agents, workflows, data models and user experience.
- **UI component/widget:** a presentation unit that may invoke capabilities; it is not automatically an agent.
- **Platform:** trusted registry, identity, policy, execution, model/knowledge services, lifecycle, governance and commercial controls.

These concepts share contracts and lifecycle infrastructure but must not be flattened into one abstraction.

## 3. Consolidated functional requirements

### A. Package, capability and registry

| ID | Requirement | Priority | Evidence | Traceability |
|---|---|---:|---|---|
| ABX-FR-001 | Define a canonical, versioned package manifest for capabilities, actions, agents, workflows, UI components, model profiles, connectors and applications. | P0 | Repeated | B001–B011; Bot Functions, Built Components for AI, Agent Factory OS Concept |
| ABX-FR-002 | Each package declares typed inputs/outputs, purpose, dependencies, permissions, data access, runtime targets, resource needs, lifecycle and compatibility. | P0 | Repeated | B001–B011; Bot Functions, AI Integration in Enterprise, Agent Factory OS Concept |
| ABX-FR-003 | Maintain an immutable/versioned registry with validation, content hashes, provenance, lineage, retrieval and deprecation state. | P0 | Repeated | B002, B006, B009; Built Components for AI, Build common platform, Agent Factory OS Concept |
| ABX-FR-004 | Support package lifecycle: scaffold, validate, build, test, evaluate, sign, publish, install, export, deploy, update, rollback and retire. | P0 | Repeated | B008–B011; SaaS platform development, Agent Factory OS Concept, Google AI Agent Marketplace |
| ABX-FR-005 | Verify complete package file inventory, dependency closure, imports, build targets and declared entry points; fail on missing or unresolved files. | P0 | Repeated | B008–B011; SaaS platform development, System architecture design, Production-Grade Flutter Framework |
| ABX-FR-006 | Distinguish atomic deterministic utilities, skills/actions, agents, workflows, UI components and full applications in discovery and packaging. | P0 | Repeated | B008–B011; Utility Tools Suggestions, Agent vs Workflow Builders, OpenWidgets Reuse Discovery |

### B. Execution, actions and orchestration

| ID | Requirement | Priority | Evidence | Traceability |
|---|---|---:|---|---|
| ABX-FR-007 | Execute one bounded agent invocation through a trusted runtime with persisted request/result, idempotency, token/resource limits and trace metadata. | P0 | Direct + implementation baseline | Existing Execution Runtime; B006–B009 |
| ABX-FR-008 | Enforce action permissions, tenant/user scope and policy before any external or side-effecting operation. | P0 | Repeated | B001, B006–B011; Business Logic Engine, AI Integration in Enterprise, DPDP Act AI Agent |
| ABX-FR-009 | Model actions with preconditions, side-effect classification, timeout, retry policy, idempotency, postcondition verification and compensation where possible. | P0 | Repeated | B007–B009, B011; Large Action Models Overview, IFTTT for AI Agents, GUI for Business Model |
| ABX-FR-010 | Separate agent reasoning/proposals from trusted runtime authorization and actual execution. | P0 | Repeated | B006–B011; Chatbots vs RAG vs Agentic, Agent Factory OS Concept, AI Gateway Providers |
| ABX-FR-011 | Support typed task delegation, specialist agents, scoped shared artifacts, deadlines, budgets and traceable aggregation. | P1 | Repeated | B003, B006, B009; Multi-Agent Systems Overview, Agent Foundry AI |
| ABX-FR-012 | Support durable long-running jobs with progress, checkpoint, cancellation, retry and resource budgets for suitable compute tasks. | P1 | Synthesis | B008–B010; System architecture design, Workflow Upgrade Architectures |
| ABX-FR-013 | Provide human approval gates and review/confirmation for consequential writes, financial operations and external spend. | P0 | Repeated | B006–B011; SAP Authorisations and Rules, UPI advancement ideas, Agentic Digital Marketing |

### C. Workflow and authoring

| ID | Requirement | Priority | Evidence | Traceability |
|---|---|---:|---|---|
| ABX-FR-014 | Define a canonical, versioned workflow schema independent of any one visual builder or execution vendor. | P0 | Repeated | B002, B004, B008–B010; BPMN Toolkit Overview, Workflow Upgrade Architectures |
| ABX-FR-015 | Workflow schema supports typed steps, events, conditions, branches, loops, parallelism, mappings, retries, timeouts, approvals and compensation. | P0 | Repeated | B002, B007–B010; BPMN Toolkit Overview, IFTTT for AI Agents |
| ABX-FR-016 | Provide prebuilt, versioned workflow templates with triggers, inputs, actions, outputs, approvals, exception paths and tests. | P1 | Repeated | B009–B010; Enterprise Workflow Library, Enterprise Super Workflow |
| ABX-FR-017 | Keep agent builder and workflow builder as distinct authoring modes over shared package/runtime contracts. | P1 | Direct | B009; Agent vs Workflow Builders, Agent Foundry AI |
| ABX-FR-018 | Provide visual authoring for capability/workflow/application composition; builder output must be inspectable and exportable. | P1 | Repeated | B001, B002, B008–B011; GUI for Business Model, UI Builder Code Request, UI5 TypeScript Drag-and-Drop Integration |
| ABX-FR-019 | Preserve intent/specification as a first-class artifact and map it to validated graphs, schemas, code and UI. | P1 | Direct + synthesis | B009–B011; Intent Programming Language, Intent OS Dynamic Rendering, GUI for Business Model |
| ABX-FR-020 | Import data/process models and generate candidate workflows/apps with assumptions exposed and human validation required. | P2 | Direct | B004, B010–B011; Data to Process Conversion, Automate Software Building Process |

### D. Model and knowledge services

| ID | Requirement | Priority | Evidence | Traceability |
|---|---|---:|---|---|
| ABX-FR-021 | Provide multi-provider model abstraction with normalized request/response/error contracts and provider metadata. | P0 | Repeated | B006–B010; Build common platform, AI Gateway Providers, One2Shield AI Gateway |
| ABX-FR-022 | Support BYOK and platform-managed credentials with tenant isolation, secret references, rotation and redaction. | P1 | Repeated | B008–B010; SaaS platform development, AI Gateway Providers, One2Shield AI Gateway |
| ABX-FR-023 | Route models by capability, privacy, region, cost, latency, availability, context limits, evaluation and budget policy. | P1 | Repeated | B008–B010; MoA model overview, AI Gateway Providers, One2Shield AI Gateway |
| ABX-FR-024 | Provide source ingestion, extraction, indexing and RAG with provenance, freshness, permissions and citations. | P0 | Repeated | B002, B005, B006, B010; Build RAG System with LLM, Web Crawl AI Scraper, Local RAG vs LLM Wiki |
| ABX-FR-025 | Support local/offline knowledge stores and model inference as deployment profiles with explicit resource constraints. | P1 | Repeated | B006–B010; Offline AI Models PC, Offline Vector Databases, Ollama vs OpenRouter |
| ABX-FR-026 | Keep taxonomy, ontology, semantic facts, knowledge graph and deterministic expert rules as distinct typed structures with provenance. | P1 | Synthesis | B006, B010; Taxonomy Ontology Knowledge Graph, Meaning Model Exploration |
| ABX-FR-027 | Evaluate model routing, ensembles and MoA against single-model baselines for quality, latency and cost before adoption. | P2 | Research-backed | B007–B010; MoA model overview, Universal Model Fusion, Model Distillation Strategy |

### E. Identity, governance, privacy and tenancy

| ID | Requirement | Priority | Evidence | Traceability |
|---|---|---:|---|---|
| ABX-FR-028 | Provide users, organizations, workspaces, memberships, service identities and scoped authorization. | P0 | Repeated | B006, B008–B010; Build common platform, SaaS platform development, Unified Sign-In Solution |
| ABX-FR-029 | Enforce tenant isolation at server/data boundaries; cross-tenant sharing must be explicit, scoped and auditable. | P0 | Repeated | B006, B008–B009; ChatGPT ERP Development, SaaS platform development, ERP Multi-Tenant Network |
| ABX-FR-030 | Maintain audit records for identity, policy decisions, actions, approvals, package lifecycle and data access. | P0 | Repeated | B006–B010; ChatGPT as OS Concept, SaaS platform development, DPDP Act AI Agent |
| ABX-FR-031 | Apply data classification, purpose, destination, retention and policy checks before sending content to external providers. | P0 | Repeated | B006, B009–B010; AI Gateway Providers, DPDP Act AI Agent, One2Shield AI Gateway |
| ABX-FR-032 | Provide configurable privacy workflows for consent/preferences, data-subject requests, retention/deletion and processor/vendor evidence. | P1 | Direct | B009–B010; DPDP Act AI Agent, One2Shield AI Gateway |
| ABX-FR-033 | Use human/legal review and evidence for jurisdictional compliance claims; do not represent an AI model as a compliance certifier. | P0 | Synthesis | B009–B010; DPDP Act AI Agent |

### F. Developer platform, testing and quality

| ID | Requirement | Priority | Evidence | Traceability |
|---|---|---:|---|---|
| ABX-FR-034 | Provide reproducible build/test/package pipeline with pinned dependencies, lockfiles and explicit runtime compatibility. | P0 | Repeated | B005, B008–B011; Unified AI Framework Proposal, System architecture design, SDK Constraint Fix |
| ABX-FR-035 | Run formatting, lint, static analysis, unit tests, contract/integration tests and package installation/round-trip checks. | P0 | Repeated | B005, B008–B011; BharatOps quality principles, Production Readiness Assessment, LaTeX File Correction |
| ABX-FR-036 | Report readiness by evidence tier: implemented, unit-tested, contract-tested, sandbox-integrated, externally verified and operationally monitored. | P0 | Repeated | B006, B008–B011; Production Readiness Assessment, Project Metadata Extraction |
| ABX-FR-037 | Autonomous coding loops must be bounded, diff-reviewable, regression-tested and rollback-capable; never report success from generation alone. | P0 | Repeated | B008–B010; Autonomous Code Planning, Code Hardening Review |
| ABX-FR-038 | Preserve source-to-requirement-to-design-to-code-to-test traceability and record assumptions/decisions. | P1 | Repeated | B005, B008–B011; Project Metadata Extraction, Autonomous Code Planning |
| ABX-FR-039 | Support resumable development phases with durable checkpoints, artifacts, blockers and reproducible next actions. | P1 | Direct + synthesis | B009–B010; Autonomous Code Planning, KnowledgeVault Phase 1 Plan |

### G. Experience, marketplace and integrations

| ID | Requirement | Priority | Evidence | Traceability |
|---|---|---:|---|---|
| ABX-FR-040 | Expose common capabilities through API/chat/voice and channel-specific UI adapters without moving business authority into the client. | P1 | Repeated | B001, B006, B009–B011; Voice based Small Business ERP, AI Integration in Enterprise, GUI for Business Model |
| ABX-FR-041 | Provide reusable UI component/template contracts and a framework-independent presentation model. | P1 | Repeated | B001, B008, B010–B011; Flutter + UI5 Integration, Production-Grade Flutter Framework, Openui5 Code Templates |
| ABX-FR-042 | Provide enterprise connector packages (MCP/API) with schema, permissions, local/on-prem deployment and transaction evidence. | P1 | Repeated | B007–B010; SAP Joule Integration, MCP Server for SAP PS, M365 agent sources |
| ABX-FR-043 | Provide package publishing/listing, publisher identity, permissions, evaluation evidence, signing, revocation and update controls. | P1 | Repeated | B008–B009; SaaS platform development, Google AI Agent Marketplace |
| ABX-FR-044 | Support plan/entitlement/usage metering and subscription bundles as a commercial layer separate from execution authority. | P2 | Repeated | B008–B009; Subscription Service Bundles, Tokenized Agent Platform MVP |
| ABX-FR-045 | Any usage-credit or payment ledger must be auditable, idempotent and reconciled; blockchain is not assumed. | P2 | Synthesis | B008–B009; Tokenized Agent Platform MVP, Agent Factory OS Concept |

### H. Deployment and domain package ecosystem

| ID | Requirement | Priority | Evidence | Traceability |
|---|---|---:|---|---|
| ABX-FR-046 | Support connected cloud/self-hosted deployment first, with explicit profiles for local/offline and hybrid execution. | P1 | Repeated | B006–B010; Offline AI Models PC, Hosting 1000+ Apps Offline, Local RAG vs LLM Wiki |
| ABX-FR-047 | A true disconnected profile must enforce network egress denial and define import/export/update boundaries. | P2 | Direct | B007–B008; Hosting 1000+ Apps Offline |
| ABX-FR-048 | Optional edge workers require enrollment, identity, resource advertisement, secure dispatch, telemetry, update and revocation. | P2 | Repeated | B007, B010–B011; Smart Node Design Overview, Mobile Cluster OS References, Linux Kernel Distributed Components |
| ABX-FR-049 | Support domain packages (ERP/SCM, finance, education, legal, commerce, marketing, OCR, industrial, sustainability, robotics/IoT) without absorbing them into the kernel. | P1 | Repeated | B001–B011; domain sources across reviews |
| ABX-FR-050 | Safety-critical vehicle/robot/device actions require dedicated constraints, verification and fail-safe boundaries; general agents cannot directly own safety control. | P2 | Synthesis | B007, B010–B011; Vehicle OS explanation, Hardware for AMR Devices, V2X sources |

## 4. Priority interpretation

### P0 — foundation required before claiming a useful governed platform
- Package/manifest and registry contracts.
- One bounded agent execution path.
- Deterministic capability/action contracts and trusted policy enforcement.
- Tenant-aware identity/authorization and audit.
- Canonical workflow schema foundations.
- Provider abstraction and source-grounded knowledge retrieval.
- Reproducible build/test and evidence-based readiness.

### P1 — first meaningful platform expansion
- Specialist multi-agent orchestration and workflow templates.
- Visual authoring and intent-driven application generation.
- BYOK and policy-aware model routing.
- Local/offline knowledge and inference profiles.
- Enterprise connectors and on-prem execution.
- Marketplace/publishing and reusable UI/channel SDKs.

### P2 — later expansion
- Fully disconnected multi-app host.
- Distributed/mobile/mesh workers.
- Usage-credit economy and broad subscription marketplace.
- Safety-bounded device/robot/vehicle packages.

### Research
- AWML as a new language/standard.
- New foundation model or model swarm/MoA as a default strategy.
- Universal agent export across arbitrary runtimes.
- Custom OS/kernel, decentralized storage/compute network.
- Genetic RAG or other optimizer-based retrieval claims.

## 5. Source tensions and resolution

| Tension in source material | Consolidated resolution |
|---|---|
| “Everything is an agent” vs separate workflow, widget and app builders | Preserve distinct package types and contracts; agents are one package category. |
| Agent-generated action vs trusted system execution | Agent proposes; runtime policy authorizes, executes and verifies. |
| One visual builder vs platform-agnostic/exportable apps | Canonical schemas/contracts first; multiple builders and runtime adapters may target them. |
| AWML/new intent language vs immediate product delivery | Start with versioned JSON schema/workflow representation; research a textual DSL separately. |
| Cloud automation vs full offline/disconnected host | Shared package contract, distinct deployment/security profiles; implement offline after core. |
| Model swarm/MoA vs practical cost/latency | Establish provider abstraction and baselines first; ensembles are opt-in and evidence-gated. |
| Build all vertical apps vs platform factory | Build a small reference package; keep domain applications outside the kernel. |
| Distributed OS/kernel vs agent runtime | Use user-space worker agents first; kernel/mesh work is a separate research programme. |
| AI compliance agent vs legal/accountable compliance | AI assists; deterministic policy and accountable human review remain authoritative. |

## 6. Current implementation baseline and gap assessment

This section uses the repository implementation facts already established in the project review. It is not a fresh full-code audit and must be revalidated against the current repository HEAD before implementation planning is finalized.

| Area | Existing evidence | Gap against catalogue |
|---|---|---|
| Manifest registry | Immutable SQLite agent manifest registry; schema validation; create/list/retrieve/clone; SHA-256; idempotency; lineage | Generalized package types, signing, dependency graph, lifecycle/publishing and compatibility |
| Evaluation | Immutable evaluation profiles/runs; weighted correctness/latency/cost gates; accepts submitted outputs | Does not itself execute agent workloads; broader task-specific evaluators and reproducible baselines |
| Execution | Provider adapter/request/response; deterministic fake provider; persisted execution; idempotency; token bounds; one provider call | Real provider adapters/secret resolution, durable queue, cancellation, policy/principal model, tenant isolation and tool execution |
| Tool/action execution | Tool-declaring manifests are rejected because principal-aware authorization is absent | Typed action registry, permission model, sandbox, approvals, postcondition verification and compensation |
| Orchestration | Source requirements and conceptual architecture only | Specialist delegation, shared scoped state, workflow runtime and long-running task orchestration |
| Workflow | Prior BPMN/workflow source research | Canonical versioned workflow schema, interpreter, migrations and tests |
| Identity/tenancy | Not established in current implementation baseline | Users/orgs/workspaces, RBAC/ABAC, tenant data isolation, service identities |
| Knowledge/RAG | Prior architecture/source research only | Ingestion, indexing, retrieval, provenance, permissions, citations and local stores |
| Model gateway | Fake provider adapter only in known baseline | Real providers, BYOK, routing, local model adapter, usage/cost and policy |
| Developer quality | CI and tests exist; evaluation milestone previously had 25 green tests | Need current CI revalidation, broader integration/security/contract tests and package completeness checks |
| Marketplace/deployment | Source requirements only | Package signing, publishing, install/export, entitlements, deployment profiles and revocation |

### Known execution safety limitations (must remain explicit until resolved)
- Tool-capable manifests are rejected rather than executed.
- Only deterministic fake provider is known to be registered in the established baseline.
- No principal-aware authorization/tenant boundary was established in that baseline.
- Runtime was synchronous and had no durable queue/cancellation in that baseline.
- SQLite was the development persistence store in that baseline.
- Do not claim real provider execution, tool execution, multi-agent orchestration or production multi-tenancy until tests and external evidence prove them.

## 7. Recommended implementation sequence

1. **Revalidate repository and CI:** current branch/HEAD, working tree, test suite, workflow status, API surface and persistence model.
2. **Close runtime trust boundary:** principal/context model, authorization policy, tenant scope, secret references and audit decision records. Keep tools disabled until this passes.
3. **Generalize package contracts:** package type, version, dependency/runtime compatibility, permissions, resource limits, signature-ready content hashes and lifecycle state.
4. **Introduce canonical workflow schema:** versioned JSON schema and deterministic interpreter for sequential steps, conditions, approvals, retries and timeouts; add migration compatibility tests.
5. **Add deterministic capability/action registry:** schema validation, side-effect declarations, idempotency, pre/postconditions and fake/test adapters.
6. **Add real model provider integration:** one provider at a time, secret isolation, timeouts, retries, cost/usage capture, contract tests and explicit opt-in.
7. **Add knowledge/RAG vertical slice:** source ingestion → extraction → chunk/index → permission-aware retrieval → citations → evaluation.
8. **Add durable orchestration:** task state, checkpoint, cancellation, bounded delegation and observability after the core action contract is stable.
9. **Add developer factory pipeline:** scaffold/build/test/package/sign/export with complete inventory and evidence.
10. **Add one reference application:** choose a small, source-grounded use case (e.g. meeting-to-task or conversational inventory/billing) to prove end-to-end composition.
11. **Only then expand:** visual builder, marketplace, offline/local profile, enterprise connector packs and domain packages.

## 8. Acceptance principles

- No empty files, placeholder-only code, TODO-only implementation or fake-success paths.
- Every external action requires explicit authorization and records an auditable decision.
- Every side-effecting operation is idempotent or has a documented duplicate/recovery strategy.
- Agent output is untrusted until schema-validated and checked by deterministic runtime logic.
- Every package has complete dependency/file inventory and reproducible build/test evidence.
- Readiness distinguishes offline unit tests, mocks/contracts, sandbox integration and real external end-to-end execution.
- A green unit-test suite is not evidence of external provider, payment, SAP or marketplace integration.
- Data privacy, tenant isolation and network boundaries are enforced by backend/runtime controls, not prompts or UI settings.
- Research features are not promoted to core product scope without measured evidence.

## 9. Traceability and next artefacts

The 11 batch reviews remain the detailed source evidence:
- `research/batch-reviews/batch-001-review.md` through `batch-011-review.md`.

Recommended next artefacts:
1. `requirements/traceability-matrix.csv`: requirement ID → exact archive path → source excerpt/location → design component → code path → test ID → evidence state.
2. `architecture/target-architecture.md`: bounded contexts, trust boundaries, interfaces and data ownership.
3. `architecture/decision-log.md`: explicit decisions for runtime, workflow schema, provider secrets, tenancy, storage and offline profiles.
4. `roadmap/implementation-gates.md`: milestone, acceptance criteria, tests, blockers and evidence.
5. A repository-backed gap report generated from current HEAD, not from this historical implementation summary.

## 10. Catalogue status

This is a consolidated **source-derived requirements baseline**, not an approved final product specification. Requirements marked synthesis need user/architecture validation. Research items are intentionally not promoted to delivery commitments. Implementation status must be refreshed against current GitHub source and CI before assigning production-readiness percentages.
