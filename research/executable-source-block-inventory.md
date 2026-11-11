# AgentBox — executable-looking source block inventory

## Scope and extraction rule

This register is based only on the 85 selected Markdown files in `chatgpt_22-26.zip`. It indexes fenced blocks longer than 100 characters whose language labels indicate source code, structured configuration, markup, or build files. It is a triage inventory, not a code-quality verdict.

- 1,693 blocks matched the rule.
- Counts by label: Python 1,129; YAML 298; JavaScript 106; JSON 66; Dart 26; Bash 25; XML 10; JSX 5; LaTeX 5; Dockerfile 5; TypeScript 5; HTML 4; TOML 4; CSS 2; SQL 1; ABAP 1; C# 1.
- Export labels are inconsistent: some blocks contain prompt text under `text`, and some source blocks are unlabeled. Therefore this is a lower-bound index of code/config assets, not the complete set of code-like material.

## Source distribution

| Source path | Blocks |
|---|---:|
| `2026/Aeon Execution Strategy.md` | 729 |
| `2026/Cognitive Enterprise Design.md` | 277 |
| `2026/AEON Project Setup.md` | 122 |
| `2026/AEONs Reducing GPU Dependence.md` | 86 |
| `2026/Autonomous Code Planning.md` | 50 |
| `2024/Multi-Agent Systems Overview.md` and its two exact duplicates | 37 each |
| `2025/API Library for Agents.md` and its exact duplicate | 27 each |
| `2025/Agentic AI Product Search.md` and its exact duplicate | 27 each |
| `2026/Agentic Digital Marketing.md` | 20 |
| `2025/Intelligent Support Agent.md` and its exact duplicate | 18 each |
| `2026/Autonomous Offline Mind Map.md` | 12 |
| `2025/Agentic AI App Design_1.md` | 10 |
| `2025/Building AI Agent Steps.md`; `2026/yndra os.md` | 9 each |
| `2024/Hosting Yndra.io Concept.md`; `2025/Build agentic platform.md`; `2025/Building agents with ChatGPT.md`; `2025/Flutter AI Agent Integration_1.md`; `2025/Personal AI agent framework.md` | 8 each |
| `2026/Aeon and Sanskrit.md`; `2026/Agent Foundry AI.md`; `2026/Cognitive Brain Architecture.md`; `2026/SAP Autonomous Enterprise Articles.md` | 6 each |
| `2026/Agent Factory OS Concept.md`; `2026/Joule Agent Setup Guide.md` | 5 each |
| `2026/AEON-RAG Platform Build.md`; `2026/Next After Agentic AI.md` | 4 each |
| `2025/Agentic Logic with ChatGPT.md`; `2026/Cognitive Liquidity Routing System.md`; `2026/M365 Copilot Agent Excel.md` | 3 each |
| `2025/AI Agents Overview.md`; `2025/Aeons in LLM Landscape.md`; `2025/Chatbots vs RAG vs Agentic.md`; `2025/Developing Agentic AI_1.md`; `2025/MFE MS AI Agents.md`; `2026/AI Meeting-to-Task Agent.md`; `2026/DPDP Act AI Agent.md`; `2026/MedTech Agentic Platform.md`; `2026/VPS Autonomous Agents.md` | 2 each |
| `2025/Crypto Agents for Notion.md`; `2025/Reusable Agents Overview.md`; `2026/Google AI Agent Marketplace.md`; `2026/M365 Jira Agent Integration.md`; `2026/aeon studio.md` | 1 each |

The three Multi-Agent Systems Overview copies and the other duplicate pairs above are byte-identical; do not count them as independent implementations.

## High-risk block locations

Line numbers refer to the original Markdown file in the ZIP. The scan found the following blocks containing execution primitives or suspicious patterns:

| Source | Block | Start line | Label | Finding |
|---|---:|---:|---|---|
| `2024/Multi-Agent Systems Overview.md` (and two exact copies) | 12 | 1001 | Python | Uses built-in `eval(...decode())` on cached model output. Replace with strict JSON parsing/schema validation; never evaluate cache bytes as Python. |
| `2025/Build agentic platform.md` | 7 | 336 | Python | Uses `subprocess` for arbitrary Python execution. The adjacent `safe_eval_tool` is explicitly acknowledged by its source as unsafe; a timeout is not a sandbox. |
| `2026/Autonomous Offline Mind Map.md` | 1 | 36 | Python | Contains `subprocess` and `shell=True`; quarantine pending full review. |
| `2026/Autonomous Offline Mind Map.md` | 2 | 802 | Python | Contains `subprocess` and `shell=True`; quarantine pending full review. |
| `2026/Autonomous Offline Mind Map.md` | 4 | 2247 | Python | Contains `exec`, `subprocess` and `shell=True`; quarantine pending full review. |
| `2026/Autonomous Offline Mind Map.md` | 21 | 3168 | Python | Contains `subprocess` and `shell=True`; quarantine pending full review. |
| `2026/Autonomous Offline Mind Map.md` | 22 | 4085 | Python | Contains `subprocess` and `shell=True`; quarantine pending full review. |

The broad string scan also found `.eval()` in model evaluation/training snippets in `2026/AEON Project Setup.md` and a test function named `test_retrieval()` in `2026/Aeon Execution Strategy.md`. These are not Python built-in `eval` calls and should not be treated as arbitrary-code execution vulnerabilities.

## Common dependency signals

Across the indexed blocks, frequently seen imports include `__future__` (450), relative `.models` (332), `datetime` (200), `dataclasses` (199), `typing` (195), `uuid` (138), `enum` (132), relative `.engine` (121), `torch` (69), and `pytest` (63). These are lexical counts across blocks; repeated snippets and incomplete imports inflate totals. They do not establish a coherent installable dependency graph.

Other observed integration signals include React, requests, FastAPI, SQLite, Redis, provider API keys, and AEON-specific internal module paths. Each must be validated against actual repository code before adoption.

## AgentBox disposition

- Prioritize the 729-block `Aeon Execution Strategy.md` and 277-block `Cognitive Enterprise Design.md` as *review queues*, not as trusted modules. Their size and iteration density make deduplication and provenance especially important.
- The 2024 multi-agent code that deserializes cached output with `eval` must be rewritten using JSON and schema validation.
- Do not port the arbitrary-code runner in `Build agentic platform.md`. Design a separate execution boundary with OS/container isolation, resource quotas, network/filesystem policy, secret separation and auditable lifecycle.
- Treat AEON/YNDRA code as adjacent historical research. AgentBox should extract generic concepts and independently implement its own runtime.
- Build dependency manifests only after selecting a specific block and tracing all required modules; do not merge the archive's aggregate import counts into one requirements file.

## Validation limits

The block counts and line starts are mechanically extracted from the ZIP. No code in this corpus was executed, compiled, type-checked, linted, dependency-resolved or security-tested. Some code blocks may be incomplete fragments or illustrative prompts. This register does not establish functional correctness or production readiness.
