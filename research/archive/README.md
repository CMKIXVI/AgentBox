# AgentBox source recovery catalogue — discovery pass 01

This directory documents the provenance-preserving candidate catalogue generated from
`Extracted_Code_Archive_Combined.zip` by
`backend/tools/build_recovery_catalogue.py`.

## Archive inventory and discovery results

- ZIP entries: 59,813.
- Uncompressed archive size: 96,639,389 bytes.
- Indexed extraction rows: 59,809.
- Unique code-like fenced blocks: 30,862.
- Other fenced blocks preserved as unclassified: 28,947.
- Exact duplicate-content groups: 10,263.
- Discovery pass candidate rows: 4,464 (1,217 classified code blocks; 3,247 unclassified blocks).
- SHA-256 mismatches encountered: 0.
- Every discovery row remains `Candidate` / `Not started`.

The candidate count is deliberately broad. It is not a count of relevant, reviewed, accepted,
or integrated code. Metadata and full artifact text are scored with a transparent vocabulary;
all source paths, block numbers and verified SHA-256 values are retained. Unclassified blocks
are included because some may contain useful schemas or logic. A keyword match is not semantic
validation.

## Rebuild

From the repository root, with the ZIP available locally:

```bash
python backend/tools/build_recovery_catalogue.py Extracted_Code_Archive_Combined.zip \
  --output-dir research/archive
```

This writes:
- `agentbox-recovery-candidates.csv`
- `agentbox-recovery-candidates.json`
- `agentbox-recovery-catalogue-summary.json`

Optional `--limit N` caps output after relevance sorting. The script uses only the Python
standard library and never executes recovered code.

## Lineage boundaries

The discovery vocabulary keeps these lineages distinguishable:
`agent_factory_os`, `amge`, `cognition`, `meta_cognition_sakshi`, `artha`,
`aetheron`, `yndra`, and `agentbox`. A provisional subsystem is a routing hint only.
No architecture lineage is merged by this generator.

## Acceptance and naming

Before changing any row to Reviewed or Accepted, inspect the complete code block, source
conversation context, duplicate provenance, imports/dependencies, license and execution risk.
Compare against the current AgentBox API and tests. Keep original names and hashes. Normalised
filename/symbol/module fields remain blank until a reviewed migration establishes the mapping.
Do not run recovered agent-generated code on the host. Tool execution remains denied until
principal-aware authorization and isolation are implemented.

The first batch adds a repeatable discovery utility and tests for provenance retention and
hash-mismatch rejection. It does not claim that the 4,464 candidates have been semantically
reviewed or integrated into the runtime.
