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

- [Full archive concept discovery — pass 01](research/full-archive-concept-discovery-pass-01.md) — full-corpus structural discovery and candidate concept families.
- [Batch 001 review](research/batch-reviews/batch-001-review.md) — business-process generation, interoperability, edge/distributed computing, voice/multilingual interaction and authoring.
- [Batch 002 review](research/batch-reviews/batch-002-review.md) — skills, BPMN/rules, RAG, code/app builder, artifact export and enterprise data transformation.
- [Batch 003 review](research/batch-reviews/batch-003-review.md) — multi-agent orchestration, code intelligence, multi-cloud, edge workers and packaged vertical applications.
- [Batch 004 review](research/batch-reviews/batch-004-review.md) — cloud-as-code, hybrid local/server execution, community knowledge, semantic perception, accessibility and collaboration.
- [Batch 005 review](research/batch-reviews/batch-005-review.md) — unified AI capability infrastructure, crawling/knowledge ingestion, artifact provenance, constrained-device channels and quality gates.
- [Batch 006 review](research/batch-reviews/batch-006-review.md) — shared capability fabric, chat-native apps, local inference/data, AI accountability and enterprise governance.
- [Batch 007 review](research/batch-reviews/batch-007-review.md) — digital action agents, offline/local runtime, cryptographic agility, model ensembles, financial automation and developer agents.
- [Batch 008 review](research/batch-reviews/batch-008-review.md) — digital actions, offline app hosting, model ensembles, SaaS control plane, entitlements, solver jobs and package completeness.
- [Batch 009 review](research/batch-reviews/batch-009-review.md) — AgentBox as an agent factory, typed capability graph, intent compiler, autonomous coding, multi-provider gateway, privacy, workflows and marketplace.
- [Batch 010 review](research/batch-reviews/batch-010-review.md) — enterprise skill/MCP integration, versioned workflows and AWML research, privacy gateway, local RAG, semantic knowledge, UI packages and production evidence.


- [Source decision review — pass 01](research/source-decision-review-pass-01.md) — user-stated product intent, source line anchors, scope boundaries and initial requirement-to-source traceability.
- [85-source semantic extraction dossier](research/85-source-semantic-extraction-dossier.md) — complete source register, duplicate groups, source clusters, high-value observations, normalized requirements and review boundaries.
- [85-file knowledge reconstruction](research/agentbox-85-file-knowledge-reconstruction.md) — complete user-supplied agent-related Markdown source register, research clusters, capability map, safeguards and implementation sequence.
- [85-source code asset and safety triage](research/85-source-code-asset-triage.md) — measured code-block inventory, exact duplicate groups, execution-risk flags and reuse disposition.
- [Executable source block inventory](research/executable-source-block-inventory.md) — 1,693 code/config blocks indexed by source, with line-anchored execution-risk findings and reuse guidance.

A deeper scan of the uploaded ZIP has been committed:

- [Full archive concept discovery — pass 01](research/full-archive-concept-discovery-pass-01.md) — expanded source coverage to all 2,570 Markdown files, broad concept families, initial architecture implications and explicit limits of this first discovery pass.

- [Deep scan inventory v1](research/zip-deep-scan.md) — initial focused scan.
- [Deep scan inventory v2](research/zip-deep-scan-v2.md) — expanded literal-keyword scan across 2,570 files; 717 broad candidate entries, manually classified source families.
- [Agent Factory OS extraction](research/extracted/agent-factory-os.md) — AgentBox resource model, agent DNA, lifecycle/versioning, governance and deployment concepts.
- [Artificial Model Genetics Engine extraction](research/extracted/artificial-model-genetics-engine.md) — twosome/threesome/multi-parent reproduction, genomes, mutation, selection, fitness, species and lineage.
- [Evolutionary knowledge extraction](research/extracted/evolutionary-knowledge.md) — evolutionary retrieval, retrieval genomes, mutation/crossover and memory fitness.
- [Multi-agent and cognitive patterns](research/extracted/multi-agent-and-cognitive-patterns.md) — reusable modules, orchestrator/specialist coordination and cognitive flow.
- [Consolidated architecture map](docs/agent-evolution/zip-derived-architecture-map.md) — how the source ideas map into a staged AgentBox design.

The extracted research is attributed to ZIP paths. It is not a production implementation, and adjacent Aetheron/AEON research remains separate.

## Current engineering assessment
- [Repository gap analysis — 2026-11-11](docs/repository-gap-analysis-2026-11-11.md) — verified repository inventory, legacy-code risks, implementation gaps, phase gates and readiness statement.


## Backend implementation

- [Backend setup and API](backend/README.md) — Python 3.11+, FastAPI, SQLite registry and endpoint reference.
- Backend code and tests live in `backend/`; GitHub Actions runs Ruff and pytest on backend/schema changes.
- Agent registry supports schema validation, immutable versions, retrieval, listing and derived cloning.
- Evaluation v1 supports immutable evaluation profiles, deterministic assertions, weighted correctness/latency/cost scoring, pass/fail gates and persisted evaluation records.
- Evaluation currently scores outputs and measurements submitted by a caller; it does not execute agents or call models. Passing an evaluation does not yet publish or deploy an agent.

## Evaluation profile v1
- [Evaluation profile schema](schemas/evaluation-profile-v1.schema.json) — versioned cases, assertion types, score weights and promotion gates.
- [Valid evaluation profile](examples/evaluation-profile-v1.json) — reference profile.
- [Evaluation API and execution boundary](backend/README.md#evaluation-api) — endpoints, supported assertions and what is not yet executed.

## Agent manifest v1
- [Agent manifest schema](schemas/agent-manifest-v1.schema.json) — initial declarative agent definition contract.
- [Valid example manifest](examples/agent-manifest-v1.json) — reference instance.
- [Manifest v1 specification](docs/agent-manifest-v1.md) — field semantics, validation rules and security boundaries.

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
