# AgentBox Shared Evolution Platform Contracts

**Status:** architecture contract proposal  
**Applies to:** Agent Evolution Engine, Retrieval Evolution Engine and Model Genetics Engine.

## 1. Core rule

All engines evolve immutable candidate artifacts through shared platform services. An engine may define its own genome and operators, but it must not bypass registry, lineage, experiment, evaluation, policy or promotion controls.

## 2. Common artifact envelope

Every evolvable artifact must expose:

- `artifact_id`
- `artifact_type`
- `version`
- `content_hash`
- `created_at`
- `created_by`
- `source_provenance`
- `parent_artifact_ids[]`
- `schema_version`
- `dependency_refs[]`
- `lifecycle_status`

Engine-specific payloads are validated by their own versioned schemas.

## 3. Lineage contract

Lineage is a directed acyclic graph of immutable artifacts. Each edge records:
- Parent and child artifact IDs.
- Engine and operation type.
- Contribution details by field/component where applicable.
- Operator implementation version.
- Seed and configuration hash.
- Timestamp and actor/automation identity.

Cycles are rejected. Parent artifacts remain immutable.

## 4. Mutation/reproduction proposal

A proposal must include:
- Target artifact type and parent IDs.
- Proposed operator.
- Explicit field/component scope.
- Parameter bounds.
- Random seed or deterministic configuration.
- Expected changes.
- Permission impact.
- Required test/evaluation suites.
- Risk classification.

A proposal is not executable until schema, policy and compatibility validation pass.

## 5. Experiment contract

An experiment records:
- Experiment ID and status.
- Candidate artifact IDs.
- Exact parent hashes.
- Engine/operator version.
- Configuration snapshot and seed.
- Runtime/model/tool versions.
- Dataset/corpus/benchmark versions.
- Start/end times and execution logs.
- Raw metrics, reports and artifacts.
- Checkpoint references and failure details.

Experiments must be reproducible to the extent supported by the underlying model/provider. Record nondeterministic dependencies explicitly.

## 6. Evaluation contract

Evaluation consists of independent layers:

1. **Schema and compatibility:** mandatory.
2. **Security and policy:** mandatory.
3. **Functional correctness:** mandatory for declared contracts.
4. **Regression:** compare with parent/baseline.
5. **Quality metrics:** engine-specific, versioned and reported raw.
6. **Cost/performance:** explicit budgets.
7. **Human review:** required by policy/risk level.

No weighted aggregate may override a failed mandatory gate.

## 7. Promotion contract

Promotion requires:
- Candidate artifact hash.
- Passing evaluation record.
- Policy decision.
- Required approval record.
- Target environment/scope.
- Rollback target.
- Promotion event.

Promotion changes an active-version pointer; it does not overwrite artifact contents.

## 8. Rollback contract

Rollback reactivates a previously approved immutable artifact. It must create an audit event and retain the failed candidate and its evaluation history.

## 9. Event vocabulary

Initial event names:
- `ArtifactRegistered`
- `CandidateCreated`
- `MutationProposed`
- `MutationApplied`
- `CompatibilityValidated`
- `ExperimentStarted`
- `ExperimentCompleted`
- `EvaluationPassed`
- `EvaluationFailed`
- `ApprovalRequested`
- `ApprovalGranted`
- `ApprovalRejected`
- `ArtifactPromoted`
- `ArtifactRolledBack`
- `ArtifactRetired`

Events are append-only. Corrections are represented by new events, not silent edits.

## 10. Security boundaries

- No arbitrary host execution of generated code.
- Separate candidate and production credentials.
- Enforce permissions in runtime services, not only prompts.
- Sandbox tool execution and model-generated code.
- Treat user, model, tool and retrieved content as untrusted.
- Restrict network, filesystem, CPU, memory and time.
- Audit all external side effects.
- Require approval for permission expansion and production promotion.

## 11. Shared MVP acceptance criteria

- Immutable artifact snapshots and hashes.
- Versioned schema validation.
- Parent/child lineage.
- Reproducible experiment metadata.
- Versioned benchmark/evaluation records.
- Hard policy gates.
- Approval-controlled promotion.
- Rollback without history rewrite.
- Audit event stream.
