# AgentBox Agent Evolution Design

**Document status:** Design proposal v0.1  
**Source basis:** `chatgpt_22-26.zip`  
**Scope:** First minimal, independently testable agent-evolution mechanism  
**Explicit exclusions:** OpenAgents and ASPIRE are not sources for this design.

---

## 1. Design objective

AgentBox should let a user or authorized agent:

1. Define an agent as a versioned artifact.
2. Clone an existing version into an isolated candidate.
3. Propose a bounded mutation to that candidate.
4. Run the same evaluation suite against the parent and candidate.
5. Compare results and evidence.
6. Promote the candidate only when explicit acceptance gates pass.
7. Roll back by moving the active-version pointer to a previously approved version.

The first release should not attempt autonomous, unbounded self-modification. Evolution is a controlled proposal-and-evaluation loop.

## 2. ZIP-derived foundations

The following concepts are present in the supplied ZIP:

| Source document | Source concept | How AgentBox uses it |
|---|---|---|
| `2026/Agent Factory OS Concept.md` | Universal Agent Definition (UAD): model, tools, workflows, memory, permissions, knowledge bases and deployment targets | Versioned agent specification |
| Same document, lifecycle section | Versioning, forking, branching, promotion, rollback and agent packages | Candidate lifecycle |
| Same document, Self Evolution Platform section | Upgrade Agent, Refactoring Agent, Optimization Agent and Platform Evolution Agent | Later proposal generators; not required for MVP |
| Same document, mandatory rules | Requirements, architecture, contracts, database and tests first; unit, integration, security and performance tests | Phase gates |
| `2025/Reusable Agents Overview.md` | Separate, replaceable perception, decision and action modules | Mutation can target one declared component at a time |
| `2026/Agent Foundry AI.md` | Orchestrator coordinating specialist agents through shared project state | Optional later orchestration of proposal and review work |
| `2026/Aetheron and AI Evolution.md` | Dynamic topology, adaptive behavior and evaluation/testing concepts | Research-only future track; not part of MVP |

These are source-derived concepts. The data model, state machine, acceptance rules and MVP boundaries below are AgentBox design decisions synthesized from them.

## 3. Core lifecycle

```text
Approved Agent Version
        |
        v
      Clone
        |
        v
  Candidate Version
        |
        v
 Mutation Proposal
        |
        v
 Schema + Policy Validation
        |
        v
    Test Suite
        |
        v
 Parent / Candidate Evaluation
        |
        v
  Acceptance Gate
    /       \
  Pass      Fail
   |          |
   v          v
Promote    Reject / Revise
   |
   v
Active Version Pointer
   |
   +---- rollback to prior approved version when required
```

A candidate never becomes active merely because an agent generated it. Promotion is a distinct, auditable operation.

## 4. Minimal domain model

### 4.1 Agent

Represents the stable identity of an agent, independent of its versions.

Suggested fields:
- `id`
- `name`
- `description`
- `created_at`
- `owner_id`
- `active_version_id` (nullable until first promotion)

### 4.2 AgentVersion

An immutable snapshot of the complete agent specification.

Suggested fields:
- `id`
- `agent_id`
- `version_number`
- `parent_version_id` (nullable for the first version)
- `definition_json`
- `definition_hash`
- `status`: draft, candidate, evaluating, approved, rejected, archived
- `created_at`
- `created_by`
- `change_summary`

A version's definition must not be edited after it enters evaluation. A change creates a new version.

### 4.3 MutationProposal

Describes one proposed change to a candidate.

Suggested fields:
- `id`
- `candidate_version_id`
- `parent_version_id`
- `target_path` (the specific definition component to change)
- `change_type`: parameter, prompt, tool configuration, workflow, module reference
- `before_value`
- `proposed_value`
- `rationale`
- `proposer`
- `created_at`
- `status`: proposed, validated, rejected, applied

For the MVP, one proposal should change one declared target at a time. Do not permit arbitrary code mutation.

### 4.4 EvaluationRun

Stores a reproducible comparison.

Suggested fields:
- `id`
- `parent_version_id`
- `candidate_version_id`
- `suite_version`
- `environment_fingerprint`
- `model_identifier`
- `tool_versions_json`
- `started_at`
- `finished_at`
- `status`
- `summary_json`

### 4.5 EvaluationCaseResult

Stores the evidence for an individual case.

Suggested fields:
- `id`
- `evaluation_run_id`
- `case_id`
- `version_id`
- `passed`
- `score` (nullable)
- `latency_ms`
- `estimated_cost` (nullable)
- `failure_category` (nullable)
- `evidence_json`

### 4.6 PromotionEvent

Records an approved transition of the active version.

Suggested fields:
- `id`
- `agent_id`
- `from_version_id`
- `to_version_id`
- `evaluation_run_id`
- `approved_by`
- `approval_reason`
- `created_at`

Rollback should create another recorded promotion event pointing back to a prior approved version. Do not delete history.

## 5. State transitions

Allowed version transitions:

| From | To | Condition |
|---|---|---|
| draft | candidate | Definition passes schema validation |
| candidate | evaluating | Evaluation run is created |
| evaluating | approved | All mandatory gates pass |
| evaluating | rejected | A mandatory gate fails or evaluation is invalid |
| rejected | candidate | New candidate version is created from a revised proposal |
| approved | archived | No longer active or retained as historical version |

An approved version is immutable. Revisions always produce a new version.

## 6. Evaluation model

Evaluation must compare the parent and candidate using the same test-suite version and equivalent environment settings.

### Mandatory gates

A candidate cannot be promoted if any mandatory gate fails:

1. **Definition validity:** schema and required fields are valid.
2. **Permission validity:** requested tools and permissions are within the agent's authorized policy.
3. **Functional correctness:** required test cases pass.
4. **Regression protection:** previously passing critical cases do not regress.
5. **Security:** no prohibited tool access, policy bypass or unsafe execution path is detected.
6. **Operational limits:** configured timeout, step and resource limits are respected.

### Comparative measures

Record these separately; do not hide trade-offs inside one opaque score:

- Task success rate
- Output quality / rubric score
- Regression count
- Latency
- Estimated model/tool cost
- Reliability across repeated runs
- Policy and security findings

A weighted aggregate score may be displayed later, but it must never override a failed mandatory gate. Initial acceptance thresholds should be defined per agent/test suite rather than guessed as universal constants.

### Evaluation integrity

Persist:
- Parent and candidate version hashes
- Test-suite version and case identifiers
- Model identifier and relevant model configuration
- Tool versions and permission profile
- Runtime/environment fingerprint
- Run timestamps, outputs and failure evidence

Where model behavior is nondeterministic, repeat selected cases and report variance. Do not claim exact reproducibility where the provider does not guarantee it.

## 7. Mutation strategy for MVP

Start with constrained mutations only:

1. Prompt or instruction text.
2. Declared numeric or categorical configuration parameters.
3. Selection among already registered, authorized tools.
4. Composition of already registered reusable modules.
5. Workflow graph changes that pass graph validation.

Do not initially allow:
- Arbitrary source-code generation and execution
- Self-modification of AgentBox's own runtime
- Permission escalation
- Automatic production promotion
- Mutation of evaluation criteria by the candidate being evaluated
- Unreviewed changes to secrets, credentials or external integrations

A mutation generator can be manual at first. Later, an Upgrade Agent, Refactoring Agent or Optimization Agent from the ZIP's Self Evolution Platform concept may propose changes. The evaluator must remain independent of the proposal generator.

## 8. Security and governance boundaries

- Treat agent definitions, prompts, tool outputs and generated proposals as untrusted input.
- Validate every definition and mutation against a strict schema.
- Enforce tool permissions at execution time, not only in the UI or prompt.
- Keep credentials outside versioned agent definitions; store references to managed secrets only.
- Require explicit approval for production promotion in the first release.
- Do not execute arbitrary generated code in the application process or rely on subprocess timeouts as isolation.
- Record who proposed, evaluated, approved and promoted each version.
- Make evaluation and promotion events append-only from the application's perspective.

## 9. Minimal API surface

Suggested initial endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/agents` | Create agent identity and first draft |
| GET | `/agents/{agent_id}` | Read agent and active version |
| POST | `/agents/{agent_id}/versions` | Create a version or clone a parent |
| GET | `/agents/{agent_id}/versions` | List version history |
| POST | `/versions/{version_id}/mutations` | Propose/apply a constrained mutation to a candidate |
| POST | `/evaluations` | Evaluate parent and candidate against a suite |
| GET | `/evaluations/{evaluation_id}` | Read results and evidence |
| POST | `/agents/{agent_id}/promotions` | Promote an approved version with authorization |
| POST | `/agents/{agent_id}/rollback` | Restore a prior approved version |

These are proposed contracts, not implemented endpoints.

## 10. First implementation sequence

### Iteration 1 — Agent artifact and versioning
- Define and validate a minimal AgentDefinition schema.
- Create agent identity and immutable version snapshots.
- Clone a version into a candidate.
- Add definition hashing and parent lineage.
- Tests: schema validation, clone fidelity, immutability and lineage.

### Iteration 2 — Constrained mutation
- Support one targeted mutation per proposal.
- Validate before/after values against the definition schema and policy.
- Preserve mutation rationale and provenance.
- Tests: valid changes, invalid changes, forbidden paths and permission escalation rejection.

### Iteration 3 — Evaluation harness
- Define versioned test suites and cases.
- Run parent and candidate against the same suite.
- Store per-case results and evidence.
- Tests: pass/fail behavior, regression detection, repeat runs, timeouts and incomplete runs.

### Iteration 4 — Promotion and rollback
- Implement mandatory acceptance gates.
- Add explicit authorized approval.
- Change active-version pointer transactionally.
- Add rollback as a new auditable event.
- Tests: failed-gate promotion rejection, unauthorized promotion rejection, concurrent promotion protection and rollback correctness.

### Iteration 5 — Evolution proposals
- Add a simple proposal generator that suggests bounded changes.
- Keep proposal generation separate from evaluation and approval.
- Compare candidates and retain rejected experiments for analysis.
- Only after this phase should automated optimization be considered.

Each iteration must include unit, integration and security tests, documentation and a Definition of Done. Performance tests should be added where the iteration introduces measurable runtime behavior.

## 11. MVP Definition of Done

The first useful AgentBox evolution loop is complete when a user can:

1. Create an agent definition.
2. Save an immutable version.
3. Clone it into a candidate.
4. Apply a constrained, auditable mutation.
5. Run the same versioned test suite against parent and candidate.
6. Inspect a transparent comparison and failed-case evidence.
7. Promote only after all mandatory gates pass and approval is authorized.
8. Roll back to a prior approved version without deleting history.

## 12. Explicit non-goals for the first release

- Millions of agents or distributed fleet orchestration.
- Agent marketplace, billing or creator payouts.
- Kubernetes/cloud deployment compiler.
- Multi-provider compiler targets.
- Autonomous self-rewriting platform.
- Dynamic neural/topology evolution.
- General-purpose code execution sandbox.
- Enterprise multi-region availability.

These appear as broader ambitions or adjacent ideas in the ZIP, but are not prerequisites for proving the core evolution loop.

---

## 13. Source traceability

Source references are ZIP paths and section labels, not external references:

- `2026/Agent Factory OS Concept.md`
  - “Universal Agent Definition (UAD)”
  - “Agent Compiler”
  - “Tool Registry”
  - “Workflow Engine”
  - “Lifecycle Platform” (versioning, forking, branching, promotion, rollback)
  - “Self Evolution Platform”
  - “MANDATORY RULES” (phase gates and tests)
  - “POLICY ENGINE”
  - “AGENT CERTIFICATION”
- `2025/Reusable Agents Overview.md`
  - Reusable perception, decision and action modules
- `2026/Agent Foundry AI.md`
  - Orchestrator and specialist-agent coordination
  - Versioning and test-plan sections
- `2026/Aetheron and AI Evolution.md`
  - Dynamic topology evolution and validation/testing concepts; research track only

## 14. Readiness statement

This document is a design proposal. No implementation, runtime execution, security audit or production-readiness test is claimed by this document. The first milestone is Iteration 1, not a production deployment.
