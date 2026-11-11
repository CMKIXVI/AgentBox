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

A deeper scan of the uploaded ZIP has been committed:

- [Deep scan inventory](research/zip-deep-scan.md) — 2,570-file scan, 356 candidate hits, prioritized source catalog and duplicate handling.
- [Agent Factory OS extraction](research/extracted/agent-factory-os.md) — AgentBox resource model, agent DNA, lifecycle/versioning, governance and deployment concepts.
- [Artificial Model Genetics Engine extraction](research/extracted/artificial-model-genetics-engine.md) — twosome/threesome/multi-parent reproduction, genomes, mutation, selection, fitness, species and lineage.
- [Evolutionary knowledge extraction](research/extracted/evolutionary-knowledge.md) — evolutionary retrieval, retrieval genomes, mutation/crossover and memory fitness.
- [Multi-agent and cognitive patterns](research/extracted/multi-agent-and-cognitive-patterns.md) — reusable modules, orchestrator/specialist coordination and cognitive flow.
- [Consolidated architecture map](docs/agent-evolution/zip-derived-architecture-map.md) — how the source ideas map into a staged AgentBox design.

The extracted research is attributed to ZIP paths. It is not a production implementation, and adjacent Aetheron/AEON research remains separate.
