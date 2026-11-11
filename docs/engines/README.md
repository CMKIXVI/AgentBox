# AgentBox Evolution Engines

AgentBox contains three distinct evolution engines under one platform. They share identity, immutable artifact versioning, lineage, experiments, evaluation evidence, policy enforcement and approval records. They do not share one undifferentiated genome.

## Engine boundaries

| Engine | Evolves | First implementation | Deferred |
|---|---|---|---|
| Agent Evolution Engine | Agent manifests, prompts, module composition, tool declarations, workflow and memory configuration | Clone, bounded mutation, tests, evaluation, promotion and rollback | Autonomous production self-modification |
| Retrieval Evolution Engine | Query transformations, retrieval configuration, ranking weights, graph depth and reasoning-path selection | Bounded configuration search against versioned retrieval benchmarks | Unsupervised rewriting of source knowledge |
| Model Genetics Engine | Model lineage, base-model/architecture metadata, adapters, training and distillation artifacts | Registry, genome manifest, compatibility checks and experiment records | General arbitrary neural-weight crossover and autonomous reproduction |

## Shared platform services

- Artifact Registry: immutable versions, hashes, ownership and dependency manifests.
- Lineage Service: parent/child relationships and multi-parent contribution records.
- Experiment Service: configuration snapshots, seeds, execution logs and checkpoints.
- Evaluation Service: versioned datasets, benchmark suites, raw metrics and reports.
- Policy Service: tool permissions, safety gates, approval and deployment controls.
- Promotion Service: controlled activation and rollback to a previously approved version.
- Event Log: append-only record of lifecycle transitions and decisions.

## Shared lifecycle

`propose → validate → snapshot → execute → evaluate → approve → promote | reject`

A candidate is never allowed to overwrite its parent. A production version is changed only through an explicit promotion operation.

## Implementation order

1. Shared artifact/version/lineage contracts.
2. Agent Evolution Engine.
3. Retrieval Evolution Engine.
4. Model Genetics Engine metadata and compatibility registry.
5. Experimental model merge adapters only after algorithm-specific validation.

## Source basis

- `2026/Agent Factory OS Concept.md`
- `2026/AI Model Reproduction.md`
- `2026/Local RAG vs LLM Wiki.md`
- `2025/Reusable Agents Overview.md`
- `2026/Agent Foundry AI.md`

See `research/extracted/` for source-derived summaries and `docs/agent-evolution/zip-derived-architecture-map.md` for the consolidated map.
