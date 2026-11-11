# Source Extraction — Reusable Agents, Orchestration and Cognitive Flow

## Sources

- `2025/Reusable Agents Overview.md`
- `2026/Agent Foundry AI.md`
- `2024/Multi-Agent Systems Overview.md`
- `2025/Agentic Logic with ChatGPT.md`
- `2026/Cognitive Brain Architecture.md`
- `2026/Agentic Capability Center.md`

## 1. Reusable agent modules

The Reusable Agents source says to break an agent into independent components that can be reused or replaced. Its concrete example uses:
- Perception module: processes input.
- Decision module: selects a decision.
- Action module: executes the decision.

The example class wires the three modules and exposes `perceive`, `decide`, `act` and `run`.

Other principles named in the source:
- Modularity
- Configurability without code changes
- Interoperability through APIs and messaging
- Extensibility for skills/tools/behaviors
- Reuse across projects and domains

For AgentBox, represent these as replaceable interfaces with explicit input/output contracts. Do not let module swaps bypass agent permissions or evaluation.

## 2. Orchestrator and specialist agents

The Agent Foundry source proposes one Orchestrator coordinating specialist agents rather than many independent agents communicating randomly.

The orchestrator:
- Is the user's primary interaction point.
- Selects and calls specialist agents.
- Decides which specialist runs next.
- Maintains a shared project workspace.
- Reads an agent registry.
- Coordinates outputs and workflow state.

The source explicitly proposes that specialists communicate through a shared orchestrator-controlled workspace rather than uncontrolled peer-to-peer communication in its enterprise example.

This is a useful default for the MVP: explicit orchestration, shared task state and traceable handoffs. It is not a universal rule that all future AgentBox deployments must forbid peer-to-peer communication.

## 3. Multi-agent fundamentals

The Multi-Agent Systems source covers:
- Agents as goal-directed entities that perceive, decide and act.
- Independent or semi-independent execution.
- Communication and coordination.
- Planning and internal environment models.
- Utility/goal-based action selection.
- Hybrid systems combining learned models and rule-based decision components.

The archive contains repeated copies of this document; repeated export copies should not be counted as independent evidence.

## 4. Cognitive flow

The Cognitive Brain Architecture source gives this sequence:

`perception → meaning → memory → reasoning → planning → decision → action → learning`

It also describes complementary capabilities such as perception intelligence, decision intelligence and action intelligence, with shared meaning, memory, goals and reasoning.

For AgentBox, this is a useful decomposition for an agent execution trace. It is not necessary to build a complete cognitive operating system in the first release.

## 5. Agent lifecycle and API surface

The Agentic Logic source mentions agents as first-class entities, an orchestrator and intent manager, and lifecycle operations such as start, pause and stop. The API Library source covers a reusable API client/SDK with versioning, authentication, error handling, retries, pagination, async support, webhooks, caching, filters, batch operations, validation, analytics and tests.

These are useful later platform capabilities. They should not distract from the initial registry/version/clone/evaluate lifecycle.

## 6. Organizational capability governance

The Agentic Capability Center source frames a central function responsible for designing, governing, deploying and scaling agents. It mentions workflow orchestration and evaluation frameworks. This is organizational operating-model context rather than a technical runtime specification.

## 7. AgentBox MVP translation

- One orchestrator owns the run state and selects the next module/agent.
- Specialists have declared input/output schemas and bounded capabilities.
- A shared workspace stores task context and artifacts.
- Every handoff is an event with agent/version/task IDs.
- Perception, decision and action modules are independently versioned.
- Permissions are checked at action time, not merely at agent creation.
- Evaluation captures each stage and the final outcome.
