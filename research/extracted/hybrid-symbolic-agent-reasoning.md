# Source Extraction — Hybrid Symbolic and Agent Reasoning

**Primary source:** `2025/Expert systems vs RAG.md`  
**Supporting sources:** `2024/Multi-Agent Systems Overview.md`, `2025/Agentic Logic with ChatGPT.md`

**Classification:** relevant reasoning architecture and optional specialist-agent pattern.

## 1. Hybrid architecture

The source proposes combining:
- Expert-system rules and deterministic inference.
- Retrieval-augmented generation.
- LLM reasoning and language interface.
- Multi-agent coordination.

The described flow assigns distinct responsibilities to expert-system, retriever, LLM and synthesizer agents.

## 2. Why this matters for AgentBox

AgentBox should not assume every task must be solved by an LLM agent. A task can be delegated to:
- A deterministic rule engine.
- A retrieval agent.
- A planning/reasoning agent.
- A tool-execution agent.
- A verification/synthesis agent.

The orchestrator chooses a capability based on the task contract and policy.

## 3. Suggested typed capability contract

Each specialist should declare:
- Capability ID and version.
- Input/output schema.
- Preconditions and postconditions.
- Required tools and permissions.
- Determinism/repeatability expectations.
- Failure modes and retry policy.
- Evidence/provenance requirements.
- Evaluation suite.

## 4. Coordination

The multi-agent source discusses communication and coordination. The Agent Foundry source recommends orchestrator-controlled shared workspace rather than uncontrolled peer-to-peer communication. AgentBox should use explicit task handoffs and shared artifacts, with each decision and output traceable to an agent version.

## 5. Safety and evaluation

- Rules are versioned and tested like code.
- Retrieved content is evidence, not executable instruction.
- LLM outputs are untrusted until validated against schemas and task contracts.
- Specialist agents receive least-privilege permissions.
- The synthesizer must preserve citations and surface unresolved conflicts.
- Evaluation should distinguish factual correctness, rule correctness, retrieval quality and tool execution correctness.

## 6. Boundary

This source supports a hybrid capability architecture. It does not establish that any particular expert-system rulebase or multi-agent implementation is already implemented in AgentBox.
