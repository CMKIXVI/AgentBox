# AgentBox — 85-source code-asset and safety triage

## Scope

This pass examines the 85 user-selected Markdown files inside `chatgpt_22-26.zip` only. It does not use web research or `yndra_final.txt`. All 85 paths were found in the archive.

Measured corpus:
- 10,456,025 characters across 85 files.
- 1,595 user-message and 1,616 assistant/ChatGPT-message export blocks.
- 14,935 fenced blocks. Detected labels: text 4,382; unlabeled 4,220; Python 666; YAML 382; Bash 238; JSON 188; JavaScript 112; Dart 27; ABAP 16; TypeScript 11; remaining labels smaller.
- Exact SHA-256 deduplication gives 79 distinct contents. Exact duplicate groups: the three 2024 Multi-Agent Systems Overview files; the two AI Agents Course Outline files; the two API Library for Agents files; the two Agentic AI Product Search files; and the two Intelligent Support Agent files.

## Code-asset priority

Largest fenced blocks in the selected corpus:
1. `2026/yndra os.md` — 30,953 characters (unlabeled).
2. `2026/Autonomous Offline Mind Map.md` — 20,680 characters (Python-labelled).
3. `2025/Aeons in LLM Landscape.md` — 20,604 characters (LaTeX).
4. `2026/Autonomous Offline Mind Map.md` — 20,126 characters (Python-labelled).
5. `2026/Autonomous Offline Mind Map.md` — 18,204 characters (Python-labelled).
6. `2026/Autonomous Offline Mind Map.md` — 15,887 characters (Python-labelled).
7. `2026/aeon studio.md` — 13,547 characters (text prompt).
8. `2026/yndra os.md` — 13,466 characters (unlabeled).
9. `2026/Autonomous Offline Mind Map.md` — 12,721 characters (Python-labelled).
10. `2026/yndra os.md` — 11,610 characters (unlabeled).

These are review priorities, not AgentBox dependencies. The YNDRA and AEON/Aetheron materials are historical source context only.

## Execution and security review flags

Keyword scans identified execution-related constructs in:
- `2025/Build agentic platform.md`: `subprocess`, `safe_eval`.
- `2024/Multi-Agent Systems Overview.md` and its two exact duplicates: `eval(`.
- `2026/AEON Project Setup.md`: `eval(`.
- `2026/Aeon Execution Strategy.md`: `eval(`.
- `2026/Autonomous Offline Mind Map.md`: `exec(`, `subprocess`, `shell=True`.

These are triage flags, not proof that every occurrence is reachable or exploitable. They require line-level review before any reuse. No archive code was executed.

### Confirmed unsafe example

In `2025/Build agentic platform.md`, the historical `safe_eval_tool` implementation calls:

```python
subprocess.run(["python", "-c", code], capture_output=True, text=True, timeout=5)
```

The source itself warns that this is not secure and recommends strict sandboxing, resource limits, no network and container/WASM isolation. The five-second timeout does not make arbitrary Python execution safe. AgentBox must not reuse this implementation or describe a plain subprocess as a sandbox.

## Reuse classification

| Asset class | Initial disposition |
|---|---|
| Agent definitions, role descriptions and prompt templates | Retain as declarative templates; add schemas, versioning and provenance before use. |
| Orchestrator/worker and blackboard patterns | Re-specify as explicit contracts; do not copy conversation-specific implementation assumptions. |
| API/tool examples | Review authentication, input validation, allowlists, timeouts, retries and data handling individually. |
| Legacy SDK calls and framework scaffolds | Historical reference only; verify current interfaces before adapting. |
| Monolithic cognitive/runtime code | Quarantine for static review; extract small independently testable concepts only. |
| `eval`, `exec`, shell and arbitrary-code execution | Reject from the trusted runtime; require a separately isolated execution service with enforceable policy. |
| Evolution and fitness formulas | Treat as hypotheses until normalized, benchmarked and tested on held-out tasks. |

## AgentBox implications

1. Keep agent package definitions, immutable versions, execution runs, tool grants and evaluation results as separate entities.
2. Orchestrators should delegate bounded work to workers; workers should not inherit ambient credentials or unrestricted host access.
3. Every tool call should be schema-validated, explicitly authorized, time-bounded and recorded.
4. Candidate mutations must not self-promote. Promotion requires policy checks, regression suites, held-out evaluation and a rollback target.
5. Keep agent-configuration evolution, retrieval-strategy evolution, model-weight genetics and neural-topology evolution as separate experimental domains.
6. Treat all imported prompts, generated code, model outputs and archive snippets as untrusted inputs.

## Validation completed and not completed

Completed programmatically: file existence, corpus byte counts, SHA-256 hashes, exact duplicate groups, fenced-block counts/language labels, largest-block ranking and keyword-based execution-risk flags.

Not completed: line-by-line review of all 14,935 blocks; static analysis; dependency resolution; compilation; unit/integration tests; sandbox escape tests; live model/provider tests; deployment validation. This document does not establish AgentBox production readiness.

## Next concrete extraction step

Build a line-anchored code asset register for every executable-looking block: source path, message/heading anchor, language, purpose, imports/dependencies, entry point, side effects, secrets/network/filesystem access, unsafe primitives, tests present, and reuse decision. Near-duplicate code versions should be grouped while preserving each original source path.
