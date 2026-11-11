# Source Extraction — Artificial Model Genetics Engine (AMGE)

**Primary source:** `2026/AI Model Reproduction.md` in `chatgpt_22-26.zip`.

This source explores an ecosystem of AI models treated as computational organisms. It is a research concept and coding-model specification, not evidence that general multi-parent neural-weight reproduction is currently solved.

## 1. Model organism / genome

The source proposes that each organism records:
- Genome and genome checksum
- Parents, children, grandparents and family tree
- Generation and species
- Architecture and base model
- Weights/adapters metadata, including LoRA
- Capabilities
- Prompt, reasoning, planning, coding, math, vision and language profiles
- Tool profile
- Safety profile
- Retrieval, memory and embedding profiles
- Knowledge domains
- Fitness, mutation and evaluation histories
- Version, status and timestamps

This is a broad genome schema. AgentBox should separate fields that can be safely inherited as metadata/configuration from model parameters that require compatible architectures and specialized algorithms.

## 2. Population manager

The source specifies:
- Birth, death, replacement and retirement
- Migration and species assignment
- Population statistics
- Dynamic population growth and pruning
- Checkpoint recovery

The population is a managed collection of versioned candidates, not an uncontrolled set of live production agents.

## 3. Reproduction operators

The source explicitly requests:
- Twosome reproduction (two parents)
- Threesome reproduction (three parents)
- N-parent / multisome reproduction
- Configurable inheritance ratios
- Capability, prompt, metadata, adapter, retrieval, tool and memory-policy inheritance
- Child genome creation and lineage updates

A separate earlier discussion distinguishes:
- Natural birth: compatible parent models voluntarily combine.
- Forced birth: a controller chooses parent capabilities for a target task.
- Evolutionary birth: population evaluation, selection, reproduction, mutation and survival.

The source also mentions weight crossover as a future extension. Do not assume model weights from unrelated architectures can be directly combined. A practical MVP can perform multi-parent inheritance over manifests, prompts, tool configurations and evaluation profiles, while treating weight-level merging as a separate experimental adapter.

## 4. Mutation engine

The source lists:
- Random mutation
- Adaptive mutation
- Fitness-guided mutation
- Capability mutation
- Prompt mutation
- Tool mutation
- Memory mutation
- Parameter mutation
- Architecture mutation metadata
- Mutation probability scheduling
- Mutation intensity
- Mutation history

Every mutation should be represented as an explicit, reviewable change with parent version, operator, parameters, random seed and resulting artifact hash.

## 5. Parent selection and species

Selection strategies named:
- Tournament
- Roulette
- Rank
- Elite
- Top-K
- Random
- Diversity-aware
- Hybrid
- Adaptive

Species can be based on configurable similarity measures across genome, capability, fitness, prompt and knowledge characteristics. The source proposes tracking species statistics and their evolution.

## 6. Fitness and benchmark engine

The source proposes a composite fitness score using:
- Coding
- Reasoning
- Planning
- Mathematics
- Knowledge
- Tool use
- Consistency
- Latency
- JSON validity
- Hallucination estimate
- Resource usage
- Reliability

Child evaluation categories additionally include memory, long context, instruction following and function calling.

These dimensions are a proposed metric inventory. The source does not provide validated universal scoring definitions or calibrated weights. AgentBox must version the benchmark suite and fitness formula, record raw measurements, and avoid collapsing safety-critical failures into a high average score.

## 7. Evolution lifecycle

The source's repeated lifecycle is:

1. Evaluate the population.
2. Rank candidates.
3. Select parents.
4. Reproduce.
5. Mutate.
6. Benchmark offspring.
7. Accept or reject offspring.
8. Update lineage.
9. Checkpoint.
10. Repeat.

A separate MVP discussion describes a task-driven cycle: task appears → choose specialists → create child → mutate → evaluate → deploy → learn. Deployment should remain conditional on explicit approval and policy gates.

## 8. Lineage and experiment management

The source asks for a complete genealogy with genome, parents, children, fitness, generation, species, mutation count and benchmark history. It proposes JSON, GraphML, NetworkX, PNG and interactive HTML exports.

Each experiment should retain:
- UUID and timestamp
- Configuration snapshot
- Random seed
- Population snapshot
- Results
- Reports and plots
- Checkpoint / recovery point

This supports reproducibility and auditability.

## 9. Persistence and Colab recovery

The source targets Google Colab with Google Drive persistence and recovery after runtime resets. It names SQLite, JSON, CSV, Parquet, GraphML, PNG and Markdown as storage/export formats.

The later monolithic prompt emphasizes checkpointing after child creation, mutation, benchmark, reproduction, evaluation and generation updates. It asks to persist population, generation, genomes, lineage, configuration, RNG state, experiments, benchmarks, reports, statistics and task queue.

For AgentBox's server runtime, the underlying principle is portable: persist state outside process memory, use atomic checkpoint commits, store run state and RNG state, validate recovery snapshots and resume idempotently. Google Drive itself is specific to the Colab research workflow, not a mandatory production dependency.

## 10. Model merging and distillation extensions

The source lists future model-merging adapters:
- Linear merge
- SLERP
- TIES
- DARE
- Task arithmetic
- LoRA / adapter merge
- Weighted merge
- Genome merge

It also proposes teacher, multi-teacher and student metadata for distillation experiments, plus model registry integration for Transformers, PEFT, GGUF, MergeKit, Ollama and vLLM.

These are extension points in the source. Compatibility, licensing, architecture constraints, evaluation and reproducibility must be established per adapter before execution.

## 11. Future research hooks listed in the source

- Self-evolving genomes
- Weight, attention-head, layer and neuron crossover
- Sparse inheritance
- Evolutionary LoRA
- Neural chromosome representation
- Genetic attention routing
- Dynamic architecture growth
- Neural organ transplantation
- Cross-foundation-model inheritance
- Evolutionary RAG
- Evolutionary agent swarms
- Self-designed offspring
- Autonomous parent discovery
- Genome compression
- Epigenetic memory inheritance
- Neural speciation
- Genome-aware safety inheritance

These are research directions, not MVP commitments.

## AgentBox boundary

The immediate implementation should focus on agent-level genomes and reproducible evolution of configuration artifacts. Neural model reproduction remains a separately versioned experimental subsystem with explicit compatibility checks and no automatic production deployment.
