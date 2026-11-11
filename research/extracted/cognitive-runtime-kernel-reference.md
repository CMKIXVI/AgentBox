# Source Extraction — Cognitive Runtime and Kernel Reference

**Sources in the ZIP:**
- `2026/Aeon Execution Strategy.md`
- `2026/Aetheron Kernel Overview.md`
- `2026/AGI Project Consolidation.md`
- `2026/Cognitive Brain Architecture.md`

**Classification:** adjacent AEON/Aetheron runtime research. These are reusable architecture patterns and source inventories, not AgentBox-owned production modules and not dependencies.

## 1. AEON execution strategy source inventory

The exported conversation contains 569 unique `# File:` source paths and repeated implementation updates. Relevant subsystems include:

- Goals: goal models, store and engine.
- Perception: observation models and perception engine.
- Cognition: cognition models and engine.
- Query bus: query models, engine and package API.
- Orchestration: orchestrator models, engine and orchestrator.
- Tools: tool models, base contract, registry and runtime.
- Context: context models, store and manager.
- Retrieval: retrieval models and engine.
- Memory: working, episodic, semantic, temporal and procedural memory models/stores/engines.
- Planning: planner, planning engine and models.
- Event store: event models and event engine.
- Dependency injection: interfaces, lifetimes, descriptors and container.
- Operational services: health, vault, quarantine, certificate, security, vulnerability, business continuity, load balancing, credentials, encryption, incident and service mesh managers.

This is a valuable source map for runtime hardening, but the exported conversation contains iterative patches and repeated file versions. It must not be treated as a clean, buildable repository without reconstructing and testing each file.

## 2. Aetheron kernel source inventory

The exported `2026/Aetheron Kernel Overview.md` contains approximately 149 unique source file paths, including:

- Meaning and representation: Artha, Pada, Vakya, Bodha, meaning engine, meaning graph, parser, encoder and resolver.
- Cognition: context, reasoning, causality, search planner, goal search, plan executor, graph reasoning and reflection.
- Memory: sensory, working, episodic, semantic memory, experience buffer, consolidation, replay scheduler and sleep cycle.
- Knowledge: knowledge graph, ontology, search, retrieval, inference and evolution engine.
- Neural mechanisms: neuron, synapse, membrane, oscillation, topology, plasticity, learning, Hebbian learning, homeostasis, energy and surrogate learning.
- Intention/action: intention manager, scheduler, action registry, dispatcher, runtime, monitor and feedback.
- Kernel/engine: event clock, router, scheduler, dynamics, metrics, session, state, pipeline and serialization.
- Tests: unit, integration and pipeline tests.

This shows a much wider cognitive runtime design than a simple agent loop.

## 3. Persistent cognitive state

The AGI consolidation source separates memory into:
- Working memory.
- Episodic memory.
- Semantic memory.
- Procedural memory.
- Reflective memory.

It also proposes a persistent cognitive state graph and a world model. The cognitive lifecycle is expressed as perception/representation/meaning, memory/context, reasoning, planning, decision, action and learning.

AgentBox can use these as optional agent runtime capabilities, but should not force every agent to instantiate every cognitive subsystem.

## 4. Runtime architecture implications

Potential shared runtime services:
- Goal and task state.
- Perception/input normalization.
- Context assembly.
- Reasoning/planning interface.
- Tool registry and controlled dispatcher.
- Scoped memory adapters.
- Event log and replay.
- Checkpoint and recovery.
- Health/metrics and execution supervision.

Keep each service behind a small interface. The first AgentBox runtime should not recreate a large cognitive OS.

## 5. Reconstruction warnings

- The AEON execution strategy file is an exported conversation with 569 unique source-file headings, not a verified Git repository snapshot.
- Some sections are incremental patches or replacement instructions, not complete files.
- The Aetheron kernel source is a separate project lineage.
- Names and concepts overlap, but code must not be mixed across the two systems without dependency and license review.
- No runtime tests or compatibility checks are implied by this inventory.

## 6. AgentBox placement

Use these sources to design optional cognitive-runtime adapters and future memory/planning capabilities. Keep AgentBox's initial agent lifecycle and evolution core independent from the full AEON/Aetheron cognitive architecture.
