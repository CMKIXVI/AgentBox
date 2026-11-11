# Master Source-Lineage Register

**Register version:** 0.1  
**Purpose:** Prevent loss, accidental duplication, and unsafe consolidation of prior AgentBox-related work recovered from `Extracted_Code_Archive_Combined.zip`.  
**Rule:** A source match is not an accepted implementation. No item becomes reusable until its complete source context, provenance, dependencies, licence, security properties, tests, and compatibility have been reviewed.

## Evidence model

| Evidence level | Meaning |
|---|---|
| Archive-verified | Source document and indexed block counts/identifiers were observed in the supplied ZIP. |
| Syntax-screened | Isolated Python blocks passed AST parsing. This proves syntax only, not package completeness or runtime behaviour. |
| Specification-heavy | Architecture, schemas, or contracts exist, but a complete executable implementation has not been established. |
| Prior-work lead | Recalled from earlier project work but not traced to a specific source artifact in this ZIP pass. |
| Accepted / integrated | Reserved for a separately reviewed, tested, licensed, and merged implementation. No recovered family in this register currently has this status. |

The expanded deep-search package contains 6,489 candidate occurrences across 231 source documents: 1,783 classified code blocks and 4,706 unclassified blocks. All are candidates, not accepted code. An earlier PR discovery pass reported 4,269 candidates (1,157 classified and 3,112 unclassified); that historical result must remain attached to its own scan configuration and is not a correction to the expanded pass. The archive contains extraction indexes and extracted blocks, not the original standalone conversation documents; some surrounding discussion is therefore unavailable in this artifact.

## Source lineage register

| ID | Lineage / family | Primary source document(s) | Observed artifacts | Evidence and current assessment | Boundary / next action |
|---|---|---|---|---|---|
| L-001 | Agent Factory OS / UAD / Agent DNA | `2026/Agent Factory OS Concept.md` | UAD interfaces blocks 40, 165; Tool Registry 42, 168; compiler adapter 167; workflow node types 169; DNA concepts 65–67; `.agentpkg` package 150–151; lifecycle/versioning block 137 | Archive-verified; mixed code and specification. Two UAD revisions exist and must be diffed. | Compare both UAD revisions, Tool Registry and compiler contracts with AgentBox manifest/registry/API. Preserve both revisions until ancestry is proven. |
| L-002 | Aetheron cognitive runtime | `2026/Hostinger_Aetheron_4.md` | Cognitive-cycle blocks 483–510; CLI/observability/demo blocks 528–547; goals, agenda, world model, memory and reflection | Archive-verified; selected Python fragments syntax-screened. Several snippets are interfaces or fragments. | Reconstruct file boundaries/import graph and compare memory, goal and execution contracts with AgentBox. |
| L-003 | AEON v12 / neuromorphic evolution | `2026/Biologically Plausible SNN Issues.md` | Monolith parts and subsystem blocks including v12 evolution block 5; genome, fitness, population, mutation, crossover, selection, speciation, runtime, memory, STDP and swarm | Archive-verified; 169 isolated Python blocks AST-parseable; not a coherent package. | Reconstruct part/version boundaries; keep neural-weight evolution distinct from agent-configuration evolution. |
| L-004 | AEON neural package | `2026/AEON Project Setup.md` | `aeon` package, pyproject, CI, tests, neuron/spike/STDP/network/runtime/checkpoint/metrics/training modules | Archive-verified; 126 isolated Python blocks AST-parseable. pyproject declares **Proprietary**. | Quarantine from reuse pending ownership and licence verification. Do not copy into AgentBox by default. |
| L-005 | AEON sparse/event-driven network | `2026/AEONs Reducing GPU Dependence.md` | Spike/state/membrane/threshold/activation/energy modules; event queue/router/scheduler; microcolumns and network layers | Archive-verified; 130 isolated Python blocks AST-parseable. Distinct package/dependency set; no explicit licence declaration observed. | Compare against L-003/L-004 for overlap and ancestry. Resolve rights and package completeness before reuse. |
| L-006 | AEON Core v2–v5 | `2026/Autonomous Offline Mind Map.md` | V2, V3, V4, V5 monoliths; offline queue, checkpoint/recovery, routing, memory, NKS, sandbox, evolution and swarm | Archive-verified; several isolated Python blocks syntax-screened; monolithic prototypes. | Preserve each version independently; map features and tests before extracting modules. |
| L-007 | AETHER Runtime / language | `2026/AI-native OS Language.md` | Lexer/parser/compiler/AST/IR, event kernel/bus, memory, routing, manager, scheduler, consensus, sandbox, swarm, replication, self-healing; version markers v0.2–v19.0 | Archive-verified; 38 isolated Python blocks AST-parseable. Version labels do not establish linear ancestry. | Build version/symbol similarity map and dependency graph before selecting a baseline. Keep separate from Agent Factory OS and YNDRA. |
| L-008 | AEON-RAG retrieval genetics | `2026/Local RAG vs LLM Wiki.md` | RetrievalGenome, KnowledgeGene/KnowledgeGenome, mutation/crossover/selection/fitness, retrieval units/router; blocks 167–177 are file-like sequence | Archive-verified; 55 isolated Python blocks AST-parseable. | Classify as retrieval-configuration evolution, not agent DNA or neural-weight evolution. Compare with AgentBox knowledge/memory APIs. |
| L-009 | AEON-RAG foundation | `2026/AEON-RAG Platform Build.md` | FastAPI, PostgreSQL/SQLAlchemy, Qdrant, Neo4j, Ollama, Redis references and selected scaffold/configuration | Archive-verified; mostly architecture/scaffold; only 6 isolated Python blocks AST-parseable. | Treat as a separate RAG platform specification until complete source and runnable tests are recovered. |
| L-010 | ARTHA Compliance Foundation Model | `2026/ARTHA Engine Applications.md` | `artha-cfm` package; org/user/auth, roles, policies, consent, privacy, frameworks, evidence, risk, workflows, knowledge, AI execution, audit and metrics; optimizer architecture names AMGE files | Archive-verified; 116 isolated Python blocks AST-parseable; package metadata says Apache-2.0. AMGE is named in architecture, but a complete standalone AMGE implementation was not established in this pass. | Review licence and each file's provenance/dependencies. Evaluate policy/evidence/audit subsystems as a governance candidate. Do not claim AMGE is integrated. |
| L-011 | Cognier enterprise platform | `2026/Cognitive Enterprise Design.md` | 2,300 indexed blocks; 24+ referenced file paths and specifications for agents, model, runtime, Forge, execution, reasoning, learning, workflows, security, memory, knowledge, events, orchestration and governance | Archive-verified; specification-heavy, not established as an executable repository. | Preserve as its own architecture corpus. Extract canonical contracts and trace implementation blocks without conflating it with CogniEngine. |
| L-012 | CogniBlock / CogniEngine Rust platform | `2026/AI Integration in Enterprise.md` | Rust workspace/crates: cogniblock, cognigraph, cogniengine, cognipolicy, cognidata, cognimodel, cogniconnect, cognimemory, cognievent, cogniaction, cogniprovenance, cognitrust, cogniobservability, cognilifecycle, cogniapi; server/CLI/UI | Archive-verified; multi-iteration Rust/TS/JSON/YAML workspace fragments. Not yet compiled as a complete workspace. | Reassemble crate manifests and source paths; compare typed ports, graph, policy, runtime and provenance contracts with AgentBox before porting. |
| L-013 | Meta-Cognition / Sakshi | `2026/Autonomous Code Planning.md` | 5,868 indexed blocks; observer, reflection, contradiction/drift detection, witness memory, grounding, governance, Agent Society and collective intelligence | Archive-verified; 617 classified blocks plus extensive unclassified specification text. Not 5,868 executable modules. | Build concept-to-artifact map. Keep observer/governance layer distinct from base cognition and execution runtime. |
| L-014 | YNDRA OS / microkernel | `2026/yndra os.md` | AArch64 boot, MMU, scheduler, context switch, syscalls, capabilities, IPC, userspace, services, distributed runtime and hardware validation | Archive-verified; primarily Bash/YAML and architecture/build-validation artifacts. | Keep kernel/OS lineage separate. Reuse only independently reviewed portable distributed-orchestration concepts. |
| L-015 | Cognitive Kernel / COGNITIVE-OS | `2026/AI Replacing Traditional OS.md` | Kernel service model for identity, authorization, tenancy, policy, cognition, planner, workflow, orchestrator, runtime, memory, providers, capabilities, verification, governance and observability | Archive-verified; architecture trees/service concepts and a small number of Rust blocks. | Treat as service-boundary reference, not an existing AgentBox implementation. Map overlaps to current API before proposing changes. |
| L-016 | A3OPN neural predecessor | `2024/A3OPN Overview and Applications.md`; `2025/Perceptron and Neural Networks.md`; `2025/AA-A3OPN Breakthrough Potential.md` | Asymmetric Asynchronous Adaptive Output Polynode Neuron concepts, Python library structure, neuron/layer/network examples and AEON paper references | Archive-verified as source lineage leads. A3OPN → Aetheron → AEON is a lineage hypothesis supported by names/artifacts, not a proven code ancestry graph. | Preserve original source versions and hashes. Compare symbols and code similarity before declaring derivation. |
| L-017 | AgentBox current implementation | Live repository baseline and recovery branch | Existing manifest/schema registry, cloning/lineage, versioned evaluation, deterministic scoring, bounded execution API and fake provider; tool execution remains restricted | Repository baseline previously inspected; recovery PR adds catalogue discovery tooling only. | Keep current production code authoritative. Integrate recovered modules only through compatibility tests and focused PRs. |

## Prior-work leads not yet traced to this ZIP

These are important completeness checks, not archive-verified facts in this pass:

- 133 expanded agent identifiers.
- 165-agent and 160-agent catalogues.
- 140 workflows.
- Agent Society and Agent Protocol.
- Agent Graph and Agent Teams.
- Agent lifecycle, branching, forking, rollback and promotion.
- Earlier named AMGE engine components and AEON Core V1–V200 catalogues.

**Action:** trace each lead to its original conversation/source document or repository commit before marking it recovered. The current ZIP lacks standalone original conversation documents, so the extraction index alone may not contain enough surrounding context.

## AMGE separation rules

Do not collapse these into one generic “genetics” implementation:

1. **Agent/configuration genetics:** mutate, reproduce, select, evaluate, speciate and version agent manifests, workflows, tools, prompts, policies or capability configurations.
2. **Retrieval genetics:** evolve retrieval strategies, knowledge genes, corpus selection, ranking and retrieval configurations (L-008).
3. **Neural-weight / neuromorphic evolution:** evolve neuron/network parameters, topology, weights, STDP rules or populations (L-003/L-004/L-005).

Shared abstractions may be considered only after each domain has explicit typed genomes, fitness functions, safety constraints, lineage and reproducible evaluation semantics.

## Acceptance gate for every recovered artifact

Before a candidate is marked Reviewed or Accepted:

1. Recover the complete block and its surrounding source context where available.
2. Verify source path, block number, archive member and SHA-256 against the index.
3. Identify duplicate groups and version ancestry; do not discard variants based on matching names.
4. Record original filename/symbol/module and proposed normalized mapping separately.
5. Inspect imports, dependency versions, build system, licence, provenance and security risks.
6. Compare behaviour and contracts with the current AgentBox implementation.
7. Add unit, integration, compatibility and negative/security tests as appropriate.
8. Run lint, type checks, package build and tests; distinguish offline tests from live end-to-end execution.
9. Integrate through a focused branch and PR. Never execute recovered code on the host as part of discovery.
10. Preserve a decision record for rejected, superseded, deferred and accepted artifacts.

## Immediate implementation sequence

1. Compare Agent Factory OS UAD revisions, Tool Registry, compiler adapter and `.agentpkg` against AgentBox manifests and registry.
2. Reconstruct CogniBlock/CogniEngine workspace contracts and test whether its typed graph/policy/runtime model complements AgentBox.
3. Reconstruct Aetheron cognitive-cycle, goal and memory interfaces.
4. Assess ARTHA governance/evidence/audit modules with licence checks.
5. Trace prior-work catalogues and the named AMGE components to source evidence.
6. Only then select small, testable integration candidates.

**Current recovery status:** catalogue discovery exists; this register is a source map. No recovered lineage is represented as production-integrated by this document.
