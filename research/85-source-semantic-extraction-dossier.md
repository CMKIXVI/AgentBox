# AgentBox — 85-source semantic extraction dossier (phase 1)

> **Source boundary:** This dossier is derived only from the 85 user-selected Markdown files in `chatgpt_22-26.zip`. It records source structure and line-anchored evidence. Category labels and AgentBox relevance are analytical classifications, not claims made by the source authors. No source code was executed.

## Corpus accounting
- Selected paths: **85**.
- Unique normalized file contents: **79** (six duplicate-path copies across five duplicate groups).
- Text size: **10,456,025 characters**; **653,082 lines**.
- Fenced code/config blocks: **14,935**.
- This phase is a structured semantic map, not yet a full sentence-by-sentence review or compatibility audit.

## Exact duplicate groups
- `2024/Multi-Agent Systems Overview.md` = `2024/Multi-Agent Systems Overview_1.md` = `2024/Multi-Agent Systems Overview_2.md` (identical after whitespace normalization).
- `2025/AI Agents Course Outline.md` = `2025/AI Agents Course Outline_1.md` (identical after whitespace normalization).
- `2025/API Library for Agents.md` = `2025/API Library for Agents_1.md` (identical after whitespace normalization).
- `2025/Agentic AI Product Search.md` = `2025/Agentic AI Product Search_1.md` (identical after whitespace normalization).
- `2025/Intelligent Support Agent.md` = `2025/Intelligent Support Agent_1.md` (identical after whitespace normalization).

## Per-source evidence register

### `2024/Hosting Yndra.io Concept.md`
- **Classification:** Adjacent background / product, education or domain context.
- **Size:** 1,044 lines; 18,926 characters; 17 fenced code/config blocks.
- **Document structure:** Hosting Yndra.io Concept; User; ChatGPT; Additional Exported Nodes; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT.
- **Source evidence (short excerpts; original line numbers):**
  - L: Hosting Yndra.io Concept
  - L: Hosting Yndra.io Concept

### `2024/Multi-Agent Systems Overview.md`
- **Classification:** Agent platform, reusable components and orchestration.
- **Size:** 1,172 lines; 26,412 characters; 32 fenced code/config blocks.
- **Duplicate relation:** identical to `2024/Multi-Agent Systems Overview_1.md`, `2024/Multi-Agent Systems Overview_2.md`.
- **Document structure:** Multi-Agent Systems Overview; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT.
- **Source evidence (short excerpts; original line numbers):**
  - L: Multi-Agent Systems Overview
  - L: Multi-Agent Systems Overview

### `2024/Multi-Agent Systems Overview_1.md`
- **Classification:** Agent platform, reusable components and orchestration.
- **Size:** 1,172 lines; 26,412 characters; 32 fenced code/config blocks.
- **Duplicate relation:** identical to `2024/Multi-Agent Systems Overview.md`, `2024/Multi-Agent Systems Overview_2.md`.
- **Document structure:** Multi-Agent Systems Overview; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT.
- **Source evidence (short excerpts; original line numbers):**
  - L: Multi-Agent Systems Overview
  - L: Multi-Agent Systems Overview

### `2024/Multi-Agent Systems Overview_2.md`
- **Classification:** Agent platform, reusable components and orchestration.
- **Size:** 1,172 lines; 26,412 characters; 32 fenced code/config blocks.
- **Duplicate relation:** identical to `2024/Multi-Agent Systems Overview.md`, `2024/Multi-Agent Systems Overview_1.md`.
- **Document structure:** Multi-Agent Systems Overview; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT; User; ChatGPT.
- **Source evidence (short excerpts; original line numbers):**
  - L: Multi-Agent Systems Overview
  - L: Multi-Agent Systems Overview

## Cross-source synthesis — AgentBox-relevant requirements
The following are **synthesis hypotheses grounded in recurring source patterns**, not verbatim specifications. They require validation against the complete source conversations and the existing repository before implementation.

- **ABX-R01 — Agent as a versioned resource:** Define agents as portable, addressable resources with explicit identity, metadata, configuration and lifecycle. Evidence: Agent Factory OS resource philosophy and resource graph; reusable-agent component/module discussion.
- **ABX-R02 — Composable agent building blocks:** Represent agents as compositions of reusable roles, tools, knowledge sources, model/provider bindings and policies; avoid hard-wiring one agent topology. Evidence: Reusable Agents Overview; Agent Foundry AI dynamic specialist creation.
- **ABX-R03 — Orchestrated multi-agent execution:** Support an orchestrator that decomposes goals, delegates to specialist agents, tracks shared state and consolidates results. Evidence: Agent Foundry AI architecture and staged software-factory flow.
- **ABX-R04 — Explicit agent communication contract:** Define typed messages, task handoff, shared context boundaries, completion/failure signals and traceable inter-agent communication. Evidence: Agent Factory OS communication protocol section; multi-agent source family.
- **ABX-R05 — Durable execution state and resumability:** Persist task state, step history, current actor, outputs and checkpoints so interrupted work can resume. Evidence: Agent Foundry AI Agent Memory example; Build agentic platform task/status/log data model.
- **ABX-R06 — Tool registry and permissioned invocation:** Use declared tool schemas and per-agent allowed-tool policies; validate arguments and authorize each call. Evidence: Agent Factory OS tool platform/MCP sections; Build agentic platform allowed_tools and agent loop.
- **ABX-R07 — Provider/model abstraction:** Separate agent definitions from model providers and credentials; support configurable provider routing and BYOK without embedding secrets in packages. Evidence: Agent Factory OS Universal AI Gateway, BYOK and Model Orchestration sections.
- **ABX-R08 — Knowledge and retrieval as a managed capability:** Make knowledge sources, retrieval configuration, indexing and provenance explicit, versioned dependencies. Evidence: Agent Factory OS Knowledge Platform; AEON-RAG and enterprise knowledge documents (adjacent sources).
- **ABX-R09 — Agent package portability:** Package agent definitions and dependencies for import/export, cloning and deployment; define compatibility and manifest validation. Evidence: Agent Factory OS package/resource philosophy and reusable-agent modularity. Package format specifics need design validation.
- **ABX-R10 — Evolution with controlled mutation:** Separate parent/child lineage, mutation proposals, candidate evaluation and promotion; preserve reproducibility. Evidence: Agent Factory OS lifecycle concepts and separate model/retrieval evolution source families already extracted.
- **ABX-R11 — Evaluation before promotion:** Evaluate candidates against fixed tasks, test suites and explicit metrics before promotion; preserve baselines and prevent train/evaluation leakage. Evidence: source testing/evaluation themes and evolution research docs; exact scoring formula remains unvalidated.
- **ABX-R12 — Version lineage and rollback:** Retain immutable versions, parent relationships, diffs and rollback targets; distinguish configuration evolution from model-weight changes. Evidence: Agent Factory OS versioning and evolution engine source clusters.
- **ABX-R13 — Policy, audit and governance:** Centralize policy decisions, record actor/tool/model actions and provide traceable audit history. Evidence: Agent Factory OS Policy Engine and resource governance; DPDP source contains compliance/policy agent patterns but is not legal validation.
- **ABX-R14 — Isolation boundary for untrusted execution:** Treat generated code and third-party tools as untrusted; use a real sandbox boundary rather than a subprocess-only wrapper. Evidence: Build agentic platform unsafe run-code example; this requirement is a safety conclusion from code inspection.
- **ABX-R15 — Human approval gates:** Support approval checkpoints for high-impact or irreversible actions and policy exceptions. Evidence: governance/policy sections and enterprise agent workflows; detailed approval semantics need further extraction.
- **ABX-R16 — Observability and operational controls:** Capture execution traces, step logs, latency, token/provider usage, failures and cancellation/limits. Evidence: Build agentic platform task logs/status/cancel endpoints; Agent Factory OS event bus/resource model.
- **ABX-R17 — Marketplace/distribution readiness:** Model publishing, discovery, install/enablement, ownership and commercial entitlements as later platform capabilities, not prerequisites for the core runtime. Evidence: Reusable Agents Overview marketplace discussion; Tokenized Agent Platform MVP.
- **ABX-R18 — Domain-specific agents as examples, not core coupling:** Treat SAP, M365, marketing, support, compliance and robotics scenarios as test fixtures/use cases; keep their connectors and policies outside the universal runtime core. Evidence: 2025–2026 applied-agent documents and robotics/autonomous-system documents.

## Explicit separations to preserve
- Agent-definition/config evolution is distinct from retrieval strategy evolution.
- Retrieval evolution is distinct from model-weight genetics.
- Model-weight merges are experimental and require architecture/parameter compatibility; they are not ordinary agent cloning.
- Neural topology/neuroevolution and embodied robotics are research-adjacent domains, not part of the initial general-purpose AgentBox runtime.
- Provider adapters, tools, knowledge connectors and specialist agents should remain replaceable dependencies rather than fused into a single monolith.

## Limitations and next review gates
1. The excerpts are selected by a deterministic keyword/length heuristic. They are evidence pointers, not exhaustive semantic summaries.
2. Conversation exports contain iterative prompts, assistant proposals, user corrections and superseded designs. A full decision-history pass must distinguish accepted decisions from brainstorms and generated suggestions.
3. The source set includes adjacent AEON/Aetheron, SAP, robotics and product material. Inclusion in this register does not authorize importing those systems or dependencies into AgentBox.
4. Historical code has not been dependency-resolved, type-checked, tested, threat-modeled or executed.
5. The next engineering pass should build a requirement-to-repository traceability matrix, review the 10–15 highest-value source documents message-by-message, and then implement the smallest secure lifecycle vertical slice.
