# Source Extraction — Neuroevolution and Spiking Neural Network Research

**Sources:**
- `2026/Biologically Plausible SNN Issues.md`
- `2026/Human Intelligence Breakdown.md`
- `2026/Aetheron and AI Evolution.md`
- `2026/AEONs Reducing GPU Dependence.md`

**Classification:** experimental neural evolution research. This is not the same as agent-manifest evolution or retrieval-configuration evolution.

## 1. Explicit evolutionary engine material

The Biologically Plausible SNN source contains a named Evolution Engine with:
- Genome.
- Mutation.
- Selection.
- Speciation.
- Growth.
- Pruning.
- Reproduction.

It includes code sketches for:
- Evolution configuration.
- EvolutionGenome with genome ID, parent ID, generation and genes.
- EvolutionPopulation.
- Genome factory.
- Mutation engine.
- Crossover engine.
- Selection engine, including top-K selection.
- Unified evolution runtime.

This is concrete source material, but its presence in an exported conversation does not establish correctness, completeness or scientific validity.

## 2. Neural adaptation mechanisms

Across the SNN and human-intelligence discussions, the source explores:
- Synaptic plasticity and local learning.
- Spike-timing-dependent plasticity (STDP).
- Reward learning and eligibility traces.
- Homeostatic adaptation.
- Metaplasticity.
- Structural plasticity.
- Topology evolution.
- Neuron/synapse growth and pruning.
- Dendritic integration and compartmentalized computation.
- Sparse/event-driven processing.
- Energy-aware adaptation.

These are candidate mechanisms for a neural substrate research track. They should not be conflated with prompt mutation or agent tool configuration changes.

## 3. Distinct adaptation levels

The source differentiates:
- **Intrinsic plasticity:** neuron-level operating parameters such as thresholds.
- **Synaptic/computational plasticity:** connection strengths and computational parameters.
- **Structural plasticity:** topology and connectivity changes.
- **Evolutionary adaptation:** population/genome selection across generations.

This distinction is useful for AgentBox's future Model Genetics Engine taxonomy.

## 4. Potential experimental interfaces

A future neural evolution adapter could expose:
- Genome schema and checksum.
- Parent/child lineage.
- Population snapshot.
- Mutation and crossover operators.
- Selection strategy.
- Speciation method.
- Growth/pruning policy.
- Training/evaluation dataset versions.
- Hardware/runtime profile.
- Checkpoint and recovery state.
- Reproducible experiment seed.

## 5. Validation requirements

Before any SNN or neural-evolution component is considered usable:
- Verify the equations and learning rules.
- Define exact update semantics and numerical stability constraints.
- Run deterministic unit tests for isolated operators.
- Compare against non-evolving baselines.
- Test on held-out datasets.
- Report accuracy, convergence, stability, energy, latency and memory.
- Reproduce results across seeds and supported hardware.
- Check that topology growth/pruning does not silently violate constraints.

## 6. AgentBox boundary

Keep this as a research adapter under Model Genetics. Do not make it a prerequisite for the first AgentBox release. Do not claim general neural reproduction or biological plausibility from conceptual code alone.
