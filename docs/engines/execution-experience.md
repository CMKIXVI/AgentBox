# AgentBox execution experience and learning records

**Status:** implemented first runtime slice; source linkage remains caller-asserted and unverified.  
**Scope:** tenant-scoped experience records, proposed lessons and profile-pinned fitness selection.

## Data flow

1. An AgentBox execution record and evaluation run already exist for the same tenant, agent ID and immutable agent version.
2. A caller submits their identifiers plus a workload reference and SHA-256 workload digest.
3. AgentBox verifies that both records exist in the active tenant, are completed, match the same agent/version, and reference existing immutable agent and evaluation-profile versions.
4. AgentBox records only identifiers, content hashes, profile/workload provenance, aggregate evaluation metrics and token usage. Raw prompts, inputs and outputs are not copied.
5. A lesson can be recorded against an experience. Every lesson must cite its source experience and remains in `proposed` status.
6. Fitness selection groups only records for the exact tenant, evaluation profile ID/version and profile content hash. It requires a configurable minimum sample count and reports mean score, pass rate, latency, cost, sample count and a transparent sample-confidence heuristic.

## API

- `POST /v1/agent-experiences` — create an immutable experience record.
- `GET /v1/agents/{agent_id}/experiences` — list tenant-scoped records; optional profile ID/version filters must be supplied together.
- `POST /v1/agent-experiences/{experience_id}/lessons` — add an idempotent proposed lesson.
- `GET /v1/agent-experiences/{experience_id}/lessons` — list proposed lessons.
- `GET /v1/fitness/selection?profile_id=...&profile_version=...&min_samples=3` — rank sufficiently sampled agent versions for one exact evaluation profile.

All routes require the active tenant principal and exact-match AgentBox authorization grants.

## Trust and measurement limits

- `linkage_status=caller_asserted` means the API verified record identities and matching agent/version, but cannot prove the evaluation outputs were produced by the referenced execution or that the caller's workload reference/hash represents a trusted benchmark.
- `evidence_status=unverified` is retained. These records are not authenticated source facts and must not independently authorize production promotion.
- Evaluation runs currently score submitted outputs and measurements; the API is not yet a trusted runner that executes the full evaluation profile.
- Fitness selection is a triage signal, not a promotion decision. It compares only identical profile versions and requires minimum samples. The sample confidence is (n/(n+3)); the improvement priority is ((1-mean\ score)\times confidence). These are transparent heuristics, not calibrated statistical confidence intervals.
- Lessons are proposals. No lesson is automatically applied to an agent manifest, and no model-generated lesson is treated as ground truth.
- No automated lesson extraction, candidate generation, parent/candidate execution, controller scheduling or promotion is implemented by this slice.

## Persistence and recovery

The two new tenant-owned tables, `agent_experiences` and `learning_lessons`, use the existing SQLite database. They are included in encrypted tenant backup/restore. Restore order places lessons after their referenced experience records. Earlier base and pre-experience backup snapshots remain accepted and missing new tables restore as empty.

## Verification required before unattended evolution

A trusted runner must bind exact workload snapshots to executions and evaluation cases, retain raw evidence under approved data policies, and attest provider/runtime versions. Candidate execution must then be isolated, repeatable and budgeted. Promotion still requires separate mandatory gates, policy authorization, approval and rollback.
