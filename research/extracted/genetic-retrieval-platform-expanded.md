# Source Extraction — Expanded Genetic Retrieval Architecture

**Primary source:** `2026/AEON-RAG Platform Build.md`  
**Supporting source:** `2026/Local RAG vs LLM Wiki.md`

**Classification:** retrieval evolution design. It is related to AgentBox's Retrieval Evolution Engine, but remains an experimental design.

## 1. Genetic evolution subsystem inventory

The AEON-RAG source contains a dedicated Genetic Evolution Engine with modules grouped around:

- Population management and initialization.
- Species.
- Mutation engine, strategies, gene mutation, parameter mutation, adaptive mutation and mutation metrics.
- Crossover engine, strategies, uniform crossover, single-point crossover, multi-point crossover and crossover metrics.
- Selection: tournament, roulette, rank, elitist, parent selection and selection metrics.
- Elitism engine, elite archive, champion tracker and metrics.
- Diversity management.
- Fitness engine and fitness functions.
- Retrieval, latency, precision, recall and cost fitness.
- Hall of fame, champion store and champion ranking.
- Optimizer and evolution orchestration.

The source also includes a broader platform tree with hybrid retrieval, temporal memory, LLM reasoning, benchmarking, frontend, operations/deployment and SDK extensions.

## 2. Retrieval genome

The Local RAG source defines mutable retrieval parameters:
- Semantic weight.
- Ontology weight.
- Graph weight.
- Memory weight.
- Activation threshold.
- Graph depth.

These should be schema-validated, bounded and normalized according to the selected retrieval strategy.

## 3. Search/evolution cycle

The combined sources imply this experiment loop:

1. Initialize a population of retrieval genomes.
2. Execute each genome against the same corpus/index and query set.
3. Capture retrieval traces and evidence rankings.
4. Compute raw relevance, coverage, citation, latency and cost measurements.
5. Select parents using a declared selection strategy.
6. Apply bounded mutation/crossover.
7. Preserve elite candidates and diversity.
8. Evaluate offspring on held-out queries.
9. Archive champions and full lineage.
10. Promote only after policy and regression checks.

## 4. Important algorithmic components

- **Population:** current candidate strategy set.
- **Species:** clusters of sufficiently different retrieval strategies.
- **Mutation:** bounded parameter or strategy changes.
- **Crossover:** combine compatible parameter sets with per-field provenance.
- **Selection:** tournament, roulette, rank or elitist selection.
- **Elitism:** retain best known candidates to avoid losing them.
- **Diversity:** prevent premature convergence to one retrieval configuration.
- **Hall of fame:** preserve historically strong candidates.
- **Fitness:** compare retrieval quality, evidence quality and resource cost.
- **Optimizer:** coordinate generations and stopping criteria.

## 5. Fitness integrity

The Local RAG source's illustrative formula is not a validated standard. AgentBox should:
- Define direction and scale for every metric.
- Normalize latency/cost so lower values are rewarded.
- Retain raw metrics.
- Separate hard gates from weighted scores.
- Use a held-out query set.
- Measure citation correctness and evidence faithfulness independently.
- Version fitness formulas and benchmark datasets.

## 6. AgentBox implementation boundary

The existing Retrieval Evolution Engine specification should be expanded with population, species, selection, elitism, diversity, hall of fame and optimizer interfaces. Initially implement these over retrieval configuration artifacts, not arbitrary executable code or changing source documents.
