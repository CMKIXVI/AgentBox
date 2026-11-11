# Model Genetics Engine (MGE)

**Priority:** experimental third engine  
**Status:** research specification and registry boundary only; no neural reproduction implementation claimed  
**Primary ZIP source:** `2026/AI Model Reproduction.md`

## 1. Responsibility

Track model ancestry, capabilities, adapter/training artifacts, experiments and compatibility. The source proposes a model population with genome, parents, children, species, fitness, mutation history and reproduction.

This engine is deliberately separated from Agent Evolution. An agent manifest can be cloned and mutated without changing neural weights. Model reproduction is a harder, research-grade problem and must not be represented as ordinary configuration merging.

## 2. Model genome manifest

The registry may record:

- Genome ID and immutable hash.
- Base model identifier, revision and architecture family.
- Weight artifact references and checksums.
- Tokenizer and configuration references.
- Adapter/LoRA references and compatibility metadata.
- Training, fine-tuning and distillation lineage.
- Capability/evaluation profile.
- Memory and retrieval profile references.
- Safety and licensing metadata.
- Parent genome IDs, generation and species.
- Fitness and benchmark history.
- Reproduction operator and experiment seed.

The manifest describes provenance and compatibility; it does not itself implement a genetic operation.

## 3. Population and lineage

Source-proposed population operations:
- Register birth/offspring.
- Track parents, children and generations.
- Assign species using a declared similarity method.
- Record selection and retirement.
- Preserve checkpoints and population snapshots.
- Export lineage graphs.

No model is automatically retired or deployed based only on a composite score.

## 4. Reproduction modes

The ZIP names:
- Twosome: two parents.
- Threesome: three parents.
- N-parent / multisome: multiple parents.

For each reproduction experiment, record:
- Parent model IDs and immutable revisions.
- Compatibility report.
- Inheritance policy and per-component contribution.
- Operator and implementation version.
- Seed and configuration.
- Produced artifact hashes.
- Evaluation and acceptance decision.

Initial supported operation is metadata-level lineage and compatible adapter/configuration inheritance only where the adapter implementation explicitly supports it.

## 5. Experimental adapters

The source lists linear merge, SLERP, TIES, DARE, task arithmetic, weighted merge, LoRA/adapter merge and distillation. Each must be a separate adapter with:
- Supported architecture/model families.
- Input tensor and tokenizer compatibility checks.
- License and provenance checks.
- Resource requirements.
- Deterministic/reproducible execution settings.
- Independent benchmark suite.
- Failure and rollback behavior.

Do not imply that arbitrary models can be merged. Do not attempt cross-architecture weight crossover without a defined algorithm and validation evidence.

## 6. Selection and fitness

Source-listed selection approaches:
- Tournament.
- Roulette.
- Rank.
- Elite.
- Top-K.
- Random.
- Diversity-aware.
- Hybrid and adaptive.

Potential evaluation dimensions:
- Task quality by domain.
- Reasoning and planning.
- Coding/math where applicable.
- Tool/function calling.
- Instruction following.
- Reliability and consistency.
- Safety and policy compliance.
- Latency, memory and compute cost.

Keep raw benchmark results. Safety, licensing and compatibility are hard gates, not score dimensions that can be averaged away.

## 7. Interfaces

Conceptual operations:

- `register_model_genome(manifest)`
- `inspect_compatibility(parent_ids, operator_id)`
- `create_reproduction_experiment(parent_ids, operator_id, config, seed)`
- `execute_reproduction(experiment_id)`
- `evaluate_offspring(model_genome_id, benchmark_version)`
- `record_lineage(experiment_id, offspring_id)`
- `checkpoint_population(population_id)`

All reproduction operations must be explicitly feature-gated and isolated from production model routing until approved.

## 8. Persistence and reproducibility

Persist model artifact references, genome manifests, population snapshots, RNG state, experiment configuration, logs, metrics, checkpoints and reports. The ZIP's Google Drive/Colab workflow is one research storage example, not a required AgentBox production dependency.

## 9. MVP boundary

Implement only:
- Model genome manifest schema.
- Registry and immutable artifact references.
- Parent/child lineage graph.
- Architecture and adapter compatibility declarations.
- Experiment metadata and benchmark record schema.
- Feature-flagged adapter interface with no default weight-merging execution.

Do not claim model evolution is functional until at least one adapter is implemented, reproducibly tested on supported models and independently evaluated.
