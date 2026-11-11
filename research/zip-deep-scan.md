# AgentBox — Deep ZIP Research Inventory

## Scope and method

Source archive: `chatgpt_22-26.zip`, supplied by the user.

The archive contains 2,570 text-oriented files across the exported 2023–2026 conversation folders. A content scan identified 356 candidate documents using agent, orchestration, evolution, mutation, fitness, cognitive architecture, workflow, evaluation, model genetics and related terms. The strongest filename/content pass identified 56 matches; duplicate export variants reduce that set to approximately 50 distinct source documents.

This is a relevance inventory, not a claim that every hit is an AgentBox design requirement. Many documents are domain-specific or contain incidental keyword matches. The extracted documents in this repository preserve the relevant concepts and identify their source. No OpenAgents or ASPIRE material was used.

## Tier 1 — Direct AgentBox and agent-factory foundations

| ZIP source | Relevant material | Extraction / treatment |
|---|---|---|
| `2026/Agent Factory OS Concept.md` | Explicit AgentBox OS vision; Universal Agent Definition; Resource OS; resource graph; event bus; agent DNA; lifecycle/versioning/fork/branch/rollback; factory; runtime; compiler; model orchestration; governance; tests; deployment | Primary source. Extracted into `research/extracted/agent-factory-os.md`; earlier legacy code extracts remain separately quarantined |
| `2025/Build agentic platform.md` | Task model, FastAPI task API, worker, executor, tool wrappers, basic execution loop | Existing legacy extracts in `research/legacy-extracts/`; unsafe/outdated code flagged |
| `2024/Multi-Agent Systems Overview.md` | Agent fundamentals, coordination, perception/action, planning, multi-agent and hybrid-model patterns | Relevant patterns summarized in `research/extracted/multi-agent-and-cognitive-patterns.md`; archive contains duplicate export variants |
| `2025/Reusable Agents Overview.md` | Replaceable perception, decision and action modules; composability, configurability, interoperability | Extracted in `research/extracted/multi-agent-and-cognitive-patterns.md` |
| `2026/Agent Foundry AI.md` | Orchestrator-led specialist agents; shared workspace; registry; testing and dynamic orchestration | Extracted in `research/extracted/multi-agent-and-cognitive-patterns.md` |
| `2026/Agentic Capability Center.md` | Central governance, deployment, evaluation and scaling of agent capabilities | Included as organizational/governance context, not a runtime specification |
| `2025/Agentic Logic with ChatGPT.md` | Agent as first-class entity; orchestrator, intent manager, lifecycle and microservice integration | Adjacent architecture reference |
| `2025/API Library for Agents.md` | Agent API/SDK concepts: versioning, auth, retries, pagination, webhooks, async, filters, batch operations, testing | API design reference; duplicate export variant exists |
| `2025/AI Agents Course Outline.md` | Agent fundamentals, architectures and learning topics | Educational background only; duplicate export variant exists |
| `2025/Agentic AI App Design_1.md` | Agentic app structure and user-facing application design | Application-layer reference |
| `2025/Developing Agentic AI_1.md` | Foundational agent development notes | General background; not treated as implementation authority |

## Tier 2 — Model evolution, genetics and adaptive knowledge

| ZIP source | Relevant material | Extraction / treatment |
|---|---|---|
| `2026/AI Model Reproduction.md` | Artificial Model Genetics Engine (AMGE); model organisms; genome; multi-parent reproduction; mutation; selection; species; lineage; fitness; checkpoints and experiments | Primary evolutionary research source. Extracted in `research/extracted/artificial-model-genetics-engine.md` |
| `2026/Local RAG vs LLM Wiki.md` | Evolutionary ontology/RAG; query, retrieval and reasoning evolution; retrieval genome; fitness; mutation/crossover; self-evolving memory | Extracted in `research/extracted/evolutionary-knowledge.md` |
| `2026/AEON-RAG Platform Build.md` | Genetic evolution engine and evaluation/benchmarking as additive platform phases | Related RAG research; not copied as a production dependency |
| `2026/Aetheron and AI Evolution.md` | Learning loop, sparse processing, dynamic topology, structural plasticity and validation | Optional research track only; distinct project lineage |
| `2026/Aetheron Summary.md` | Cognitive layers, learning, memory, dynamic topology and architecture | Contextual reference only |
| `2026/Aetheron Architecture Reconstruction.md` | Cognitive model specifications, lifecycle, interfaces, quality gates and acceptance criteria | Reference for specification discipline; do not import Aetheron as a dependency |
| `2026/Aetheron Kernel Overview.md` | Semantic memory, event runtime, persistence and kernel abstractions | Optional research reference; separate system |
| `2026/Autonomous Offline Mind Map.md` | Offline cognitive runtime, memory, model and execution components | Optional architecture reference; validate before reuse |

## Tier 3 — Cognitive architecture, orchestration and operating-system concepts

| ZIP source | Relevant material | Extraction / treatment |
|---|---|---|
| `2026/Cognitive Architecture Analysis.md` | Goal engine, tool registry, cognition/orchestration, evaluation and phased forensic architecture work | Research reference; not direct AgentBox implementation |
| `2026/Cognitive Brain Architecture.md` | Perception → meaning → memory → reasoning → planning → decision → action → learning; module boundaries and checkpoints | Included in cognitive pattern summary |
| `2026/Autonomous OS Architecture.md` | Autonomous OS runtime, perception, planning, decision and simulation/validation components | Broad systems research; not all subsystems belong in AgentBox |
| `2026/Autonomous Code Planning.md` | Autonomous planning, goal/action structures, capability graphs and evaluation | Very large mixed export; only relevant planning/agent passages should be used |
| `2026/AI-native OS Language.md` | Language/runtime concepts including lexer, AST, parser, VM and capabilities | Adjacent execution-language research; not required for the first AgentBox runtime |
| `2026/Next After Agentic AI.md` | Cognitive routing, persistent memory, AI operating systems and coordination economies | Strategic context, not an implementation specification |
| `2025/ChatGPT as OS Concept.md` | OS-level agents, services and embeddable agent applications | Adjacent platform concept |
| `2026/AI Replacing Traditional OS.md` | AI-native operating-system and agent execution concepts | Adjacent conceptual reference |
| `2026/Intent OS Dynamic Rendering.md` | Intent-driven UI/rendering and workflow/agent interaction | UI-layer reference only |
| `2026/ChatGPT Apps SDK Overview.md` | App/agent interaction and workflow integration | Integration context; not an AgentBox dependency |
| `2026/AI Platform Comparison.md` | Platform capability comparisons and agent/model/workflow landscape | Context only |
| `2026/AI Gateway Providers.md` | Model gateway, routing and provider concepts | Model-routing context; validate separately |
| `2026/Branch · AI Gateway Providers.md` | Gateway/observability architecture and provider patterns | Branch export; overlapping source material |
| `2026/OpenRouter Model Hosting.md` | Hosted/local model access and routing | Provider integration reference only |
| `2026/Universal Model Fusion.md` | Model fusion/combination concepts | Research context; not proof that arbitrary models can be merged |
| `2026/Building Weights with Existing Models.md` | Existing model weight construction/combination | Research context; inspect technical validity before implementation |
| `2026/Workflow Automation Platforms.md` | Workflow orchestration concepts | Integration context, not core AgentBox identity |

## Tier 4 — Domain-specific agent examples and marketplace context

These documents demonstrate potential applications or platform surfaces. They are not universal runtime requirements.

| ZIP source | Relevance |
|---|---|
| `2026/Agentic Digital Marketing.md` | Domain-specific multi-agent marketing workflow |
| `2026/Autonomous Marketing Tools.md` | Marketing automation/tool ecosystem |
| `2026/Autonomous Marketing Chats.md` | Marketing agent use cases |
| `2026/MedTech Agentic Platform.md` | Regulated-domain agent platform example; additional safety/compliance requirements |
| `2026/DPDP Act AI Agent.md` | Privacy/compliance-oriented agent use case |
| `2026/AI Meeting-to-Task Agent.md` | Narrow task-agent example |
| `2026/Joule Agent Setup Guide.md` | Enterprise agent configuration example |
| `2026/VPS Autonomous Agents.md` | Hosted autonomous-agent deployment example |
| `2026/Google AI Agent Marketplace.md` | Agent marketplace context |
| `2025/Tokenized Agent Platform MVP.md` | Tokenized agent platform idea; optional commercial concept |
| `2025/Agentic AI startups India.md` | Market/ecosystem context, not architecture |
| `2025/Personal AI agent framework.md` | Personal productivity-agent examples |
| `2025/Building agents with ChatGPT.md` | Agent setup, memory, tools and iteration background |
| `2025/Automating with agents.md` | Automation use cases and safety considerations |
| `2025/IFTTT for AI Agents.md` | Trigger/action workflow patterns |
| `2025/Chatbots vs RAG vs Agentic.md` | Distinction between chatbot, retrieval and agentic workflows |
| `2025/Agentic AI Product Search.md` | Product-search agent use case; duplicate export variant exists |
| `2025/Intelligent Support Agent.md` | Support-agent application; duplicate export variant exists |
| `2025/MFE MS AI Agents.md` | Enterprise agent application context |
| `2026/SAP Autonomous Enterprise Articles.md` | Enterprise agent examples and autonomous enterprise framing |
| `2026/Cognitive Liquidity Routing System.md` | Specialized routing/decision system |
| `2026/Cognitive ERP Adoption Guide.md` | ERP adoption and agent context |
| `2026/AI Office Tool Evolution.md` | Office productivity and AI tool evolution |
| `2026/Linkedin Post - The Cognitive Enterprise Experience.md` | Cognitive-enterprise framing |
| `2026/entamilnadu.ai_enta os.md` | Separate domain/OS concept; only generic reusable agent patterns are relevant |
| `2026/AI-Commerce Integration Architecture.md` | Commerce agents, workflows and integrations |
| `2026/AI-Commerce Integration Architecture (2).md` | Expanded/branch export with commerce-agent concepts |

## Duplicate and export handling

The archive contains repeated export variants, including:
- `2024/Multi-Agent Systems Overview.md`, `_1.md`, `_2.md`
- `2025/AI Agents Course Outline.md`, `_1.md`
- `2025/API Library for Agents.md`, `_1.md`
- `2025/Agentic AI Product Search.md`, `_1.md`
- `2025/Intelligent Support Agent.md`, `_1.md`

Do not treat these as independent designs unless a content diff proves a meaningful change.

## Extraction boundaries

- Direct AgentBox requirements are sourced primarily from `2026/Agent Factory OS Concept.md`.
- Evolutionary model population/genetics ideas come from `2026/AI Model Reproduction.md`.
- Evolutionary knowledge/retrieval ideas come from `2026/Local RAG vs LLM Wiki.md`.
- Reusable agent modules and orchestrator patterns come from the named reusable-agent and Agent Foundry documents.
- Aetheron/AEON materials are not silently merged into AgentBox. They remain optional, separately attributed research.
- Domain-specific agent examples are use cases, not requirements for the core platform.
- The ZIP consists of exported conversations. Some content is illustrative assistant-generated material. Inclusion is not evidence of correctness, novelty, legal ownership, or production readiness.

## Recommended next research actions

1. Finish source-to-requirement traceability for the direct AgentBox source.
2. Extract all agent lifecycle/versioning/package/registry details into a canonical specification.
3. Define the agent genome separately from model-weight genetics.
4. Implement a safe MVP for metadata/prompt/tool-policy mutation and deterministic evaluation.
5. Keep weight-level crossover, architecture evolution and multi-parent model reproduction behind experimental interfaces until scientifically validated.
