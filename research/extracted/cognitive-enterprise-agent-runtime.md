# Source Extraction — Cognitive Enterprise Agent Runtime

**Primary source:** `2026/Cognitive Enterprise Design.md` in `chatgpt_22-26.zip`.  
**Classification:** adjacent platform architecture; relevant to AgentBox's shared runtime and governance layers, not a direct AgentBox implementation specification.

## 1. Agent framework layer

The source explicitly groups these platform components:

- Agent Registry
- Agent Runtime
- Agent Orchestrator
- Agent Communication
- Agent Memory
- Agent Governance

This is a stronger platform decomposition than treating the agent as a prompt plus a model call. It implies independent lifecycle, execution, coordination, memory and policy services.

## 2. Cognitive services and execution stack

The source's broader cognitive enterprise architecture places reasoning, decision intelligence, a directed capability graph, execution engine and connector fabric in a layered stack. Its sequence includes:

1. Reasoning Engine
2. Decision Intelligence Fabric
3. Directed Capability Graph
4. Execution Engine
5. Universal Connector Fabric
6. Enterprise Systems

The source also names a cognition layer, knowledge engine, memory engine, workflow engine, analytics and agent runtime as cooperating services.

## 3. AgentBox implications

AgentBox should make the following service boundaries explicit:

- **Registry:** discover immutable agent definitions and versions.
- **Runtime:** execute an approved agent version under resource and permission limits.
- **Orchestrator:** decompose goals, choose agents and sequence execution.
- **Communication:** typed messages and task handoffs, not uncontrolled peer-to-peer chat.
- **Memory:** scoped, versioned memory resources with provenance.
- **Governance:** policy checks, approval, certification and audit.
- **Capability graph:** discover which agents/tools can satisfy a task and their dependencies.
- **Connector fabric:** controlled access to external APIs and systems.

The capability graph should be declarative and queryable. It should not become an unrestricted permission graph: capability discovery and authorization remain separate checks.

## 4. Governance and execution boundaries

The source describes a platform where enterprise capabilities are exposed through APIs and plugins/SDKs, with identity, event bus, runtime and observability services. For AgentBox, all external side effects should be mediated through the tool/connector runtime and policy service.

## 5. Source caveats

The source is a long evolving enterprise design conversation. It includes status/progress tables from that project, which are not AgentBox status and must not be copied as readiness claims. This extraction retains architecture patterns only.

## 6. Recommended AgentBox placement

Shared platform services:
- Agent Registry
- Agent Runtime
- Agent Orchestrator
- Agent Communication
- Agent Memory
- Capability Graph
- Tool/Connector Fabric
- Governance and Audit

These services support all three evolution engines, but remain independent of their genome-specific logic.
