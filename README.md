# AgentBox

A standalone environment for creating, cloning, testing, evaluating, versioning and evolving AI agents.

## Current repository status

The initial content is a **research extraction** from the user's uploaded `chatgpt_22-26.zip`. It is not yet a working agent runtime.

- `research/legacy-extracts/` contains selected historical code examples.
- `research/README.md` describes the extraction and known limitations.
- `research/source-map.md` maps repository files and candidate concepts to their ZIP source documents.

## Working principles

1. Use the uploaded ZIP as the source basis for this extraction phase.
2. Do not use OpenAgents or ASPIRE as implementation sources.
3. Preserve provenance and distinguish source examples from new implementation.
4. Keep the first prototype small and independently testable.
5. Do not execute untrusted agent-generated code without a genuine isolation boundary.

## Next design target

Map the source concepts into a minimal AgentBox lifecycle:

`define → version → clone/mutate → test → evaluate → promote or rollback`

No production readiness or end-to-end runtime validation is claimed at this stage.


## ZIP research corpus
- [Source decision review — pass 01](research/source-decision-review-pass-01.md) — user-stated product intent, source line anchors, scope boundaries and initial requirement-to-source traceability.
- [85-source semantic extraction dossier](research/85-source-semantic-extraction-dossier.md) — complete source register, duplicate groups, source clusters, high-value observations, normalized requirements and review boundaries.
- [85-file knowledge reconstruction](research/agentbox-85-file-knowledge-reconstruction.md) — complete user-supplied agent-related Markdown source register, research clusters, capability map, safeguards and implementation sequence.
- [85-source code asset and safety triage](research/85-source-code-asset-triage.md) — measured code-block inventory, exact duplicate groups, execution-risk flags and reuse disposition.
- [Executable source block inventory](research/executable-source-block-inventory.md) — 1,693 code/config blocks indexed by source, with line-anchored execution-risk findings and reuse guidance.

A deeper scan of the uploaded ZIP has been committed:

- [Deep scan inventory v1](research/zip-deep-scan.md) — initial focused scan.
- [Deep scan inventory v2](research/zip-deep-scan-v2.md) — expanded literal-keyword scan across 2,570 files; 717 broad candidate entries, manually classified source families.
- [Agent Factory OS extraction](research/extracted/agent-factory-os.md) — AgentBox resource model, agent DNA, lifecycle/versioning, governance and deployment concepts.
- [Artificial Model Genetics Engine extraction](research/extracted/artificial-model-genetics-engine.md) — twosome/threesome/multi-parent reproduction, genomes, mutation, selection, fitness, species and lineage.
- [Evolutionary knowledge extraction](research/extracted/evolutionary-knowledge.md) — evolutionary retrieval, retrieval genomes, mutation/crossover and memory fitness.
- [Multi-agent and cognitive patterns](research/extracted/multi-agent-and-cognitive-patterns.md) — reusable modules, orchestrator/specialist coordination and cognitive flow.
- [Consolidated architecture map](docs/agent-evolution/zip-derived-architecture-map.md) — how the source ideas map into a staged AgentBox design.

The extracted research is attributed to ZIP paths. It is not a production implementation, and adjacent Aetheron/AEON research remains separate.

## Evolution architecture

- [Evolution engines overview](docs/engines/README.md)
- [Agent Evolution Engine](docs/engines/agent-evolution-engine.md)
- [Retrieval Evolution Engine](docs/engines/retrieval-evolution-engine.md)
- [Model Genetics Engine](docs/engines/model-genetics-engine.md)
- [Shared evolution platform contracts](docs/evolution-platform-contracts.md)
- [ZIP-derived architecture map](docs/agent-evolution/zip-derived-architecture-map.md)

### Additional ZIP-derived research

- [Cognitive enterprise agent runtime](research/extracted/cognitive-enterprise-agent-runtime.md)
- [Cognitive runtime and kernel reference](research/extracted/cognitive-runtime-kernel-reference.md)
- [Expanded genetic retrieval architecture](research/extracted/genetic-retrieval-platform-expanded.md)
- [Neuroevolution and SNN research](research/extracted/neuroevolution-and-snn-research.md)
- [Agent runtime language and governance](research/extracted/agent-runtime-language-and-governance.md)
- [Hybrid symbolic agent reasoning](research/extracted/hybrid-symbolic-agent-reasoning.md)
- [Autonomous world models and embodied agents](research/extracted/autonomous-world-model-and-embodied-agents.md)
