# AgentBox ZIP source map

Basis: the user's uploaded `chatgpt_22-26.zip` only. No OpenAgents or ASPIRE material is used.

## Extracted code currently in this repository

| Repository file | ZIP source | What was retained | Current status |
|---|---|---|---|
| `research/legacy-extracts/agent_definition.ts` | `2026/Agent Factory OS Concept.md` | AgentDefinition interface: model, tools, workflows, permissions, memory, knowledge bases, deployment, billing and metadata | Partial interface; supporting types are not included |
| `research/legacy-extracts/task_model.py` | `2025/Build agentic platform.md` | SQLAlchemy Task persistence model | Legacy reference |
| `research/legacy-extracts/agent_executor.py` | `2025/Build agentic platform.md` | Step-based LLM/tool execution loop | Legacy reference; depends on tools.py |
| `research/legacy-extracts/tools.py` | `2025/Build agentic platform.md` | LLM call, HTTP GET and subprocess code examples | Unsafe/outdated; do not execute untrusted code |
| `research/legacy-extracts/task_api.py` | `2025/Build agentic platform.md` | FastAPI task creation and status endpoints | Incomplete package/import and lifecycle assumptions |
| `research/legacy-extracts/worker.py` | `2025/Build agentic platform.md` | RQ worker task lifecycle example | Incomplete package/import and lifecycle assumptions |

## Relevant source documents reviewed, not yet extracted as standalone code

| ZIP source | Reusable idea | Treatment |
|---|---|---|
| `2024/Multi-Agent Systems Overview.md` | Multi-agent coordination and parallel execution | Select only relevant patterns; source contains many unrelated examples |
| `2025/Reusable Agents Overview.md` | Reusable perception, decision and action modules | Candidate for a small composable-agent abstraction |
| `2026/Agent Foundry AI.md` | Orchestrator delegating to specialist agents | Candidate for orchestration design |
| `2026/Agentic Capability Center.md` | Capability-centred agent architecture | Candidate for capability registry design |
| `2026/Agent Factory OS Concept.md` | Agent factory, node types, workflow composition and compiler adapters | Primary conceptual source for AgentBox |
| `2026/Aetheron and AI Evolution.md` | Adaptive/evolutionary architecture concepts | Optional research track; not assumed to be part of the initial product |

## Important integrity and safety notes

- These are selected extracts from exported Markdown conversations, not a complete upstream software repository.
- The examples may be assistant-generated illustrative code; extraction does not establish authorship, novelty, correctness or production suitability.
- The task API and worker refer to `.models`, while the extracted model file is named `task_model.py`. This is a source-layout mismatch, not a verified runnable package.
- The sample LLM call uses a legacy OpenAI Completions interface.
- The function named `safe_eval_tool` runs arbitrary Python in a subprocess. A timeout is not a sandbox.
- No live runtime, integration, security or end-to-end tests are claimed for these extracts.

## Scope boundary

The next implementation step should be a source-to-design mapping for a minimal AgentBox prototype: agent definition, versioned agent artifact, isolated evaluation, test results and promotion/rollback. Do not import unrelated material wholesale or treat the legacy execution snippets as production code.
