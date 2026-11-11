# Agent Evolution Engine (AEE)

**Priority:** first implementation engine  
**Status:** architecture specification; no runtime implementation claimed  
**Primary ZIP source:** `2026/Agent Factory OS Concept.md`  
**Supporting sources:** `2025/Reusable Agents Overview.md`, `2026/Agent Foundry AI.md`, `2025/Build agentic platform.md`

## 1. Responsibility

Evolve an agent as a versioned, declarative resource. The engine changes agent configuration and composition; it does not mutate foundation-model weights.

## 2. Agent genome

The initial genome is a validated manifest containing:

- Stable agent ID and semantic version.
- Parent version references and artifact hash.
- Purpose, description and behavior contract.
- Model/provider reference and model parameters.
- Prompt/template references.
- Perception, decision and action module references.
- Tool declarations with input/output schemas.
- Workflow graph and capability references.
- Memory and knowledge configuration.
- Permissions and policy references.
- Dependencies and runtime compatibility.
- Test-suite and evaluation-profile references.

Secrets are never stored in the genome. Store secret references and resolve them at runtime through a secret manager.

## 3. Candidate lifecycle

1. Select an approved parent version.
2. Clone its immutable manifest into a new candidate.
3. Validate schema and dependency compatibility.
4. Generate a mutation proposal.
5. Apply bounded changes to the candidate only.
6. Record a structured diff, operator, parameters and seed.
7. Run static validation and deterministic tests.
8. Run evaluation against a versioned benchmark suite.
9. Apply mandatory safety, permission and regression gates.
10. Request human approval where required.
11. Promote the candidate or reject it.
12. Preserve lineage and evidence; rollback by reactivating a prior approved version.

## 4. Initial mutation operators

- Prompt wording/structure mutation within an approved template boundary.
- Model routing/parameter mutation within configured limits.
- Perception/decision/action module replacement from an allowlisted registry.
- Tool selection mutation without permission expansion.
- Workflow ordering or branching mutation under schema validation.
- Memory/retrieval configuration mutation.
- Description and metadata mutation.

Permission expansion, new external side effects, secret access and deployment-target changes require explicit policy approval and must not be silently inherited.

## 5. Evaluation gates

Hard gates:
- Manifest and schema valid.
- Required tests pass.
- No prohibited tool or permission use.
- No critical safety/security regression.
- Dependency and model compatibility verified.
- Required human approvals recorded.

Measured dimensions:
- Task success and contract adherence.
- Reliability and repeatability.
- Tool-call correctness.
- Output validity.
- Latency and token/resource cost.
- Regression against parent version.
- Robustness to adversarial and malformed inputs.

Keep raw measurements. Fitness is a versioned report, not a single unqualified truth score.

## 6. Interfaces

Conceptual operations:

- `create_candidate(parent_version_id, requested_changes)`
- `validate_candidate(candidate_id)`
- `mutate_candidate(candidate_id, mutation_plan, seed)`
- `run_tests(candidate_id, test_suite_version)`
- `evaluate_candidate(candidate_id, benchmark_version)`
- `request_promotion(candidate_id, approval_policy)`
- `promote(candidate_id, approval_record)`
- `rollback(agent_id, approved_version_id)`

Every operation must be idempotent where practical and emit an audit event.

## 7. Data records

- AgentManifest
- AgentVersion
- MutationProposal
- MutationRecord
- TestRun
- EvaluationRun
- ApprovalRecord
- PromotionRecord
- LineageEdge
- RollbackRecord

All records reference immutable artifact hashes and exact runtime/model/tool versions.

## 8. Safety constraints

- Never execute arbitrary generated code on the host.
- Never mutate an active production artifact in place.
- Execute candidate agents in an isolated runtime with explicit resource limits.
- Enforce tool permissions outside the model prompt.
- Treat model output, retrieved content and tool output as untrusted input.
- Keep candidate and production credentials separated.
- Require explicit approval for production promotion and permission expansion.

## 9. MVP acceptance criteria

- Create and validate an agent manifest.
- Store immutable version snapshots.
- Clone a version and preserve parent lineage.
- Apply at least one bounded, deterministic mutation.
- Produce a human-readable diff.
- Run a repeatable test suite against parent and child.
- Store raw results and a comparison report.
- Reject candidates that fail mandatory gates.
- Promote only with an approval record.
- Roll back to a prior approved version without rewriting history.

No percentage production-readiness claim is made until these criteria are implemented and tested.
