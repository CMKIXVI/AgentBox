# Retrieval Evolution Engine (REE)

**Priority:** second implementation engine, after Agent Evolution foundations  
**Status:** architecture specification; no runtime implementation claimed  
**Primary ZIP source:** `2026/Local RAG vs LLM Wiki.md`  
**Supporting source:** `2026/AEON-RAG Platform Build.md`

## 1. Responsibility

Optimize retrieval and evidence-selection strategies as versioned configuration artifacts. The engine may evolve query transformations, retrieval weighting, graph depth, thresholds, reranking and reasoning-path selection. It must not silently rewrite source documents or fabricate knowledge.

## 2. Retrieval genome

Initial schema:

- Genome ID, version and parent genome IDs.
- Semantic retrieval weight.
- Ontology/structured-query weight.
- Graph retrieval weight.
- Memory retrieval weight.
- Activation/relevance thresholds.
- Graph traversal depth.
- Query transformation strategy.
- Candidate count and reranking configuration.
- Citation/evidence requirements.
- Model and embedding references.
- Dataset and benchmark suite references.
- Configuration hash and mutation history.

Weights must be bounded and normalized where the selected retrieval strategy requires it. The exact constraints belong to a versioned strategy schema.

## 3. Evolution loop

1. Receive a fixed evaluation query set.
2. Generate candidate query/retrieval strategies.
3. Execute candidates against the same indexed corpus snapshot.
4. Record retrieved documents, ranks, scores, citations and latency.
5. Evaluate relevance, coverage, evidence support and cost.
6. Mutate or recombine configuration parameters within safe bounds.
7. Compare candidates with the parent and baseline.
8. Retain candidates that pass all hard gates and improve the declared objective.
9. Preserve experiment seed, corpus/index version and full lineage.

## 4. Mutation and crossover

Source-derived examples include changing semantic/ontology/graph weights, graph depth and activation thresholds, and combining parameter values from parent retrieval genomes.

Initial operators:
- Bounded numeric perturbation.
- Weight redistribution with normalization.
- Threshold adjustment.
- Graph-depth adjustment within configured limits.
- Query rewrite-template selection from an allowlist.
- Reranker configuration selection.
- Multi-parent parameter inheritance with explicit per-field provenance.

Do not allow arbitrary code mutation in this engine.

## 5. Fitness and evaluation

The ZIP gives an illustrative score:

`0.4 × relevance + 0.2 × coverage + 0.1 × novelty + 0.2 × citation + 0.1 × latency`

This formula is not validated. In particular, metric direction, normalization and scale must be defined; lower latency should not accidentally reduce fitness.

The engine must store raw values and independently enforce:
- Evidence relevance threshold.
- Citation correctness and traceability.
- No unsupported-answer increase beyond tolerance.
- No data leakage between tuning and held-out evaluation.
- Latency and cost budgets.
- Corpus/index compatibility.

Quality dimensions:
- Recall@k / precision@k where labels exist.
- Evidence coverage.
- Citation precision and citation completeness.
- Answer faithfulness to retrieved evidence.
- Query robustness.
- Latency and cost.
- Diversity/novelty where useful.

The benchmark definition, weights and thresholds must be versioned. Use held-out evaluation data for final comparisons.

## 6. Interfaces

Conceptual operations:

- `create_retrieval_genome(corpus_snapshot, strategy_config)`
- `generate_candidates(parent_genome_ids, mutation_plan, seed)`
- `execute_retrieval(genome_id, query_set_version)`
- `evaluate_retrieval(run_id, benchmark_version)`
- `compare_genomes(candidate_ids, baseline_id)`
- `promote_retrieval_genome(genome_id, approval_record)`
- `rollback_retrieval(corpus_scope, approved_genome_id)`

## 7. Data records

- RetrievalGenome
- QuerySetVersion
- CorpusSnapshot
- IndexVersion
- RetrievalTrace
- EvidenceRecord
- RetrievalExperiment
- RetrievalEvaluation
- MutationRecord
- PromotionRecord

Every trace references the exact corpus, index, embedding model, reranker, query set and genome version.

## 8. Safety and integrity

- Preserve source documents as immutable inputs.
- Never treat retrieved text as executable instructions.
- Keep retrieval configuration evolution separate from source-knowledge editing.
- Prevent test-set leakage.
- Preserve citations to original evidence.
- Require review before deploying a strategy that changes data access boundaries.

## 9. MVP acceptance criteria

- Define and validate a retrieval genome.
- Run two or more strategies on the same corpus and query set.
- Capture ranked evidence and traceable citations.
- Compute versioned evaluation metrics.
- Apply bounded mutations with reproducible seeds.
- Compare candidate against baseline on held-out data.
- Reject regressions in citation correctness or evidence support.
- Promote and roll back immutable strategy versions.
