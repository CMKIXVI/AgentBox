# Source Extraction — Evolutionary Knowledge, Retrieval and Memory

**Primary source:** `2026/Local RAG vs LLM Wiki.md` in `chatgpt_22-26.zip`.

Related source: `2026/AEON-RAG Platform Build.md`.

## 1. Layered knowledge model

The source combines:
- Taxonomy for navigation and classification.
- Semantic retrieval for similarity.
- Ontology for structured relationships and reasoning.
- A genetic/evolutionary layer for optimization.

The stated aim is an evolutionary knowledge system rather than a fixed retrieval pipeline.

## 2. What evolves

### Query evolution
The source proposes generating alternative formulations of an original query and retaining higher-performing variants. Its example expands a city water-shortage question into water security, urban resilience, groundwater restoration and desalination economics.

### Retrieval evolution
Different retrieval strategies compete. An example compares semantic-heavy weighting with graph/ontology-heavy weighting.

### Reasoning evolution
Multiple reasoning paths are generated for the same problem (the source illustrates alternatives such as desalination and groundwater) and evaluated.

### Memory evolution
The source describes tracking genome fitness, knowledge fitness, path fitness and agent fitness as part of a self-evolving memory loop.

## 3. Retrieval genome

A source code sketch defines a RetrievalGenome with fields such as:
- semantic weight
- ontology weight
- graph weight
- memory weight
- activation threshold
- graph depth

The source treats these parameters as mutable configuration genes for a retrieval strategy.

## 4. Fitness function example

The source gives this illustrative weighted score:

`fitness = relevance_score * 0.4 + coverage_score * 0.2 + novelty_score * 0.1 + citation_score * 0.2 + latency_score * 0.1`

This is an example from the source, not a validated formula. In a real implementation, latency must be normalized so that lower latency does not accidentally lower fitness; each metric's scale and direction must be explicit. Citation correctness and answer faithfulness need independent tests.

## 5. Mutation and crossover

The source sketches mutation of:
- graph depth
- activation threshold
- semantic weight

It then normalizes weights. It also sketches crossover between parent retrieval genomes by inheriting parameter values from multiple parents.

AgentBox can safely prototype this as parameter search over versioned retrieval configurations, with bounded ranges, normalization, seeds, and benchmark comparisons.

## 6. Suggested architecture implications

A future knowledge-evolution subsystem could maintain:
- Retrieval strategy genome
- Versioned query transformations
- Retrieval execution traces
- Reasoning-path identifiers
- Dataset and benchmark versions
- Fitness metrics and raw evidence
- Mutation/crossover provenance
- Knowledge and retrieval lineage

It should not silently rewrite source knowledge. Evolve retrieval strategies and candidate knowledge structures separately; preserve original documents and citations.

## 7. Boundary

This source is an exploratory design. It does not demonstrate that a RAG system autonomously improves factual accuracy over time. Any claimed improvement must be measured on held-out evaluation sets and checked for regression, citation quality, data leakage and latency/cost.
