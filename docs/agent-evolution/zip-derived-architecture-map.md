# AgentBox — Consolidated ZIP-Derived Architecture Map

**Basis:** source-derived synthesis of the user's `chatgpt_22-26.zip`. See `research/zip-deep-scan.md` for the inventory and `research/extracted/` for detailed extracts.

This is an architecture map, not a claim that the source concepts have been implemented or independently validated.

## 1. Two distinct but connected evolution domains

The ZIP contains two related ideas that must not be conflated.

### A. Agent evolution (practical first layer)

An agent is a versioned resource whose DNA includes:
- Identity and description
- Model/provider configuration
- Prompt and behavior profile
- Perception, decision and action modules
- Tools and tool schemas
- Workflows
- Permissions and safety policies
- Memory and knowledge configuration
- Dependencies and deployment targets
- Tests, performance history and lineage

These assets can be cloned, forked, modified, evaluated, versioned, promoted and rolled back without modifying foundation-model weights.

### B. Model genetics (experimental second layer)

The AMGE source treats models as organisms with:
- Base architecture/model and parameter/adapter metadata
- Capabilities and behavioral profiles
- Memory/retrieval profiles
- Parents, children, species and generation
- Fitness, mutation and evaluation history
- Genome identity/checksum

It proposes twosome, threesome and N-parent reproduction, plus model merging, adapter inheritance and future neural crossover. This is a separate experimental layer because weight-level inheritance requires architecture compatibility and validated algorithms.

## 2. Three genome scopes

A practical decomposition inferred from the source material:

| Genome | What it describes | Initial operations |
|---|---|---|
| Agent genome | Prompt, module graph, tools, workflows, permissions, memory settings and model selection | Clone, fork, bounded mutation, compare, evaluate |
| Retrieval/knowledge genome | Semantic/ontology/graph/memory weights, retrieval depth and thresholds, query/reasoning strategy | Parameter mutation, bounded crossover, benchmark |
| Model genome | Base model, architecture metadata, weights/adapters, training/distillation lineage and capabilities | Registry and compatibility metadata first; experimental merge adapters later |

The first two can be evolved as configuration artifacts in the MVP. The third should not claim actual neural reproduction until the model-merging adapter is technically verified.

## 3. Proposed lifecycle

`Define → Validate → Version → Clone → Mutate → Test → Evaluate → Approve → Promote → Monitor → Retire/Rollback`

For each child/candidate, preserve:
- Parent version IDs
- Mutation operator and parameter values
- Random seed
- Exact model/provider version
- Tool and permission manifest
- Benchmark suite version
- Raw test results and fitness calculation
- Artifact checksum
- Approval identity and timestamp
- Promotion/rollback events

## 4. Parent selection and reproduction

The AMGE source lists tournament, roulette, rank, elite, top-K, random, diversity-aware, hybrid and adaptive selection.

For AgentBox MVP:
1. Select parents only from compatible, approved versions.
2. Require explicit capability/contract compatibility.
3. Create a child manifest with recorded inheritance.
4. Resolve conflicting tools and permissions conservatively.
5. Require human review for permission expansion or production-impacting changes.

For three-parent or multisome reproduction, record each parent's contribution by field/operator. Do not merge incompatible tool permissions by union; the result must pass policy review.

## 5. Mutation operators

Source-listed operators:
- Prompt mutation
- Capability mutation
- Tool mutation
- Workflow mutation
- Memory mutation
- Retrieval parameter mutation
- Architecture metadata mutation
- Adaptive/random/fitness-guided mutation

Initial AgentBox mutation should be bounded and schema-aware:
- Edit one field or module at a time.
- Enforce allowed ranges and JSON Schema.
- Preserve parent snapshot.
- Record before/after diff.
- Run regression tests.
- Reject any mutation that widens permissions without approval.

## 6. Evaluation and fitness

The ZIP proposes quality dimensions including coding, reasoning, planning, math, knowledge, tool use, consistency, latency, JSON validity, reliability, resource usage and hallucination estimates. The evolutionary retrieval source additionally mentions relevance, coverage, novelty, citation and latency.

AgentBox should retain raw metrics and use separate hard gates:
- Safety/policy gate: mandatory pass.
- Functional contract gate: mandatory pass.
- Regression gate: no unacceptable degradation.
- Quality score: weighted and versioned.
- Cost/latency constraints: explicit thresholds.

A high average score must never compensate for a critical safety or permission failure. Fitness weights and metric normalization must be versioned; the source's illustrative retrieval formula is not a validated universal score.

## 7. Orchestration and execution

The Agent Foundry source recommends an orchestrator coordinating specialist agents through shared task/workspace state. Reusable-agent material decomposes agents into perception, decision and action modules.

For AgentBox:
- Orchestrator owns the task and candidate lifecycle.
- Specialists have explicit contracts.
- Shared workspace carries artifacts and task context.
- Each handoff is traceable.
- Tools are invoked only after permission checks.
- Execution results are attached to the exact agent version.

## 8. Registry, packaging and lifecycle

The Agent Factory source proposes a centralized registry for agents, workflows, tools, knowledge packs, deployment packages and templates. It specifies semantic versioning and an `.agentpkg` portable package containing manifests, workflow/tool/permission/knowledge metadata, tests and docs.

The MVP should implement:
- Immutable version records
- Content hashes
- Parent/child references
- Status (draft, tested, approved, promoted, retired)
- Dependency manifest
- Exportable package metadata
- Rollback to a prior approved version

Full branching, rebase, marketplace, billing and enterprise deployment topologies can follow.

## 9. Persistence and reproducibility

The AMGE source strongly emphasizes persistent state and runtime recovery:
- Population and generation
- Genome registry and lineage
- Configuration and random state
- Experiment and benchmark records
- Mutation history
- Checkpoints and reports

AgentBox should use durable storage and atomic checkpoints. The Google Drive/Colab mechanism is specific to the source's Colab research program; the product runtime should use its own storage adapter and must not depend on notebook RAM.

## 10. Research tracks to keep isolated

- Neural weight crossover and multi-parent model reproduction.
- Attention/layer/neuron crossover and dynamic architecture growth.
- Model distillation and model fusion.
- Cognitive/topology evolution inspired by Aetheron materials.
- Evolutionary RAG and knowledge graph optimization.
- Offline/air-gapped and broad agent-OS deployment.
- Marketplace and economic layer.

These tracks need separate technical feasibility reviews, benchmarks and safety gates. Aetheron source material is not a dependency of AgentBox.

## 11. Implementation sequence

1. Agent Definition schema and validator.
2. Immutable registry/version store.
3. Clone/fork and parent-child lineage.
4. Mutation proposal format and bounded metadata/prompt mutations.
5. Deterministic test harness.
6. Versioned evaluation and comparison reports.
7. Approval, promotion and rollback.
8. Retrieval genome and bounded retrieval evolution.
9. Orchestrated multi-agent execution.
10. Experimental model-genetics adapters behind explicit feature flags.

## 12. Non-negotiable source and safety boundaries

- Preserve the ZIP source path and distinguish source-derived ideas from new design decisions.
- The exported conversations are not a verified software codebase.
- The old executor's subprocess code execution is not a sandbox.
- The legacy OpenAI Completions sample is outdated.
- Never run arbitrary generated code on the host.
- Never promote a candidate solely because its composite fitness increased.
- Never let an agent silently modify its live production version.
- Never claim weight-level model reproduction without a compatible algorithm, reproducible experiment and independent validation.


## 13. Additional source-derived platform layers

The expanded scan found further reusable platform architecture in Cognitive Enterprise Design:

- Agent Registry
- Agent Runtime
- Agent Orchestrator
- Agent Communication
- Agent Memory
- Agent Governance
- Capability Graph
- Cognitive Services
- Connector/Plugin Fabric
- Event Bus and Observability

These should become shared runtime services around the three evolution engines, not duplicated inside each engine.

## 14. Cognitive runtime capabilities

AEON/Aetheron source inventories add optional capabilities:
- Goal management and task state.
- Perception and context assembly.
- Reasoning, planning and intention.
- Tool registry and dispatcher.
- Working, episodic, semantic, procedural and reflective memory.
- Retrieval, knowledge graph and ontology.
- Event store, replay, checkpoint and recovery.
- Health, diagnostics, security, quarantine and credential services.

Keep these as modular runtime adapters. The first AgentBox release should not recreate the entire cognitive OS.

## 15. Expanded evolutionary algorithms

The AEON-RAG source adds population, species, mutation, crossover, selection, elitism, diversity management, fitness, hall of fame and optimizer components to retrieval evolution.

The SNN research adds a distinct neural evolution family: genome, mutation, crossover, selection, speciation, growth, pruning, reproduction, STDP, reward learning, eligibility traces, homeostasis and structural plasticity. These belong to experimental model/neural evolution, not the first agent-level MVP.

## 16. Runtime governance and hybrid reasoning

The AI-native OS Language source suggests capability declarations, resource budgets, runtime mutation guards, journaling, replay and recovery supervision. Its local-file sandbox example is not secure isolation.

The Expert Systems vs RAG source supports a hybrid capability architecture: deterministic rules, retrieval, LLM reasoning, specialist agents and synthesis. AgentBox should select among typed capabilities rather than force every task through an LLM.

## 17. Optional embodied/world-model track

Autonomous OS Architecture and AGI Project Consolidation describe persistent world models, simulation, dynamic replanning, embodied memory, VLA and physical execution. Keep this as a future track with its own simulator, safety envelope and hardware-in-the-loop validation.
