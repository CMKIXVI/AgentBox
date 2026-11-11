# Source Extraction — Agent Runtime Language and Governance

**Primary source:** `2026/AI-native OS Language.md`  
**Supporting source:** `2026/Agent Factory OS Concept.md`

**Classification:** adjacent AI-native runtime research; relevant to AgentBox's capability security, runtime supervision and future dynamic agent lifecycle.

## 1. Runtime capabilities named in the source

The source describes an AI-native runtime with:
- Persistent cognitive entities.
- Runtime state replication.
- Adaptive sparse cognition.
- Cognitive message routing.
- Semantic attention.
- Runtime mutation guards.
- Distributed cognitive mesh.
- Dynamic runtime modules.
- Agent persistence.
- Cognitive journaling.
- Event stream replay.
- Goal execution DAG.
- Runtime recovery supervisor.
- Neural activation propagation.
- Multi-tier scheduler.
- Structured runtime governance.
- Dynamic agent evolution.
- Runtime replay engine.
- Semantic context windows.
- Adaptive cognitive thresholds.

These are proposed platform capabilities in the source conversation, not verified features of an existing executable runtime.

## 2. Capability-based resource controls

The source defines capability categories such as memory, execution, network, inference, storage, process and agent spawning, with a domain/resource structure carrying capabilities and CPU/memory limits.

AgentBox should adopt the general principle:
- Declare capabilities explicitly.
- Grant only the minimum required capabilities.
- Enforce them in the runtime, outside the model.
- Apply resource budgets to each agent execution.
- Require approval for capability expansion.
- Audit every grant and use.

A manifest declaration alone is not enforcement; the runtime must mediate access.

## 3. Agent lifecycle state

The source includes states such as:
- IDLE
- THINKING
- EXECUTING
- FAILED
- EVOLVING

AgentBox should formalize a state machine with valid transitions, retry/recovery rules and event records. Candidate evolution should be a separate lifecycle from an active production agent's execution state.

## 4. Sandbox warning

The source contains a simple sandbox sketch that writes generated Python code to a local file. This is not a secure sandbox. File separation or asynchronous execution alone does not isolate code.

AgentBox must use a real isolation boundary for untrusted code, with filesystem, network, process, CPU, memory and time restrictions. Do not reuse the source sandbox sketch as production security.

## 5. Runtime supervision and recovery

The source's runtime health, persistence, state replication and replay concepts imply:
- Health telemetry.
- Durable state snapshots.
- Event journaling.
- Replayable execution traces.
- Recovery supervisor.
- Mutation guards.
- Controlled module activation.

These can be introduced incrementally after the basic registry and execution contract exist.

## 6. AgentBox boundary

Use these concepts to strengthen the shared runtime and governance specifications. Do not import the entire AI-native language VM or neural cognitive substrate into the first AgentBox MVP.
