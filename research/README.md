# AgentBox source extraction

This directory contains source-derived material extracted from the user's uploaded `chatgpt_22-26.zip`. OpenAgents and ASPIRE were not used as sources.

## Source documents

- `2026/Agent Factory OS Concept.md` — agent definition, tool schema, workflow and capability-oriented factory concepts.
- `2025/Build agentic platform.md` — Python task model, API, worker, executor and tool examples.
- `2024/Multi-Agent Systems Overview.md` — multi-agent coordination and parallel execution examples.
- `2025/Reusable Agents Overview.md` — reusable perception/decision/action composition.
- `2026/Agent Foundry AI.md` — orchestrator and specialist-agent pattern.
- `2026/Agentic Capability Center.md` — capability-centred architecture concepts.

## Extraction status

The files under `legacy-extracts/` preserve selected code blocks from the source Markdown. They are quarantined research artifacts, not production runtime modules.

## Known limitations in the source examples

- The sample executor invokes an LLM using the legacy OpenAI Completions API.
- The sample `safe_eval_tool` launches arbitrary Python code in a subprocess. A timeout is not a security sandbox.
- The sample task API/worker depends on Redis, RQ and SQLAlchemy and has incomplete lifecycle/error handling.
- The TypeScript agent definition references supporting types that are not defined in the extracted block.
- Some source examples are illustrative snippets rather than a complete, tested application.

Do not import these legacy extracts into production directly. AgentBox implementation should retain their useful concepts while adding validation, explicit tool permissions, deterministic tests and a real execution isolation boundary before supporting untrusted code.
