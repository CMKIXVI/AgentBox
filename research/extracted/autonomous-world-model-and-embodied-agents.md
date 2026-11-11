# Source Extraction — Autonomous World Models and Embodied Agents

**Primary sources:**
- `2026/Autonomous OS Architecture.md`
- `2026/AGI Project Consolidation.md`
- `2026/Cognitive Brain Architecture.md`

**Classification:** optional future research track. Much of this material is from Aetheron/AEON autonomous robotics and cognitive-system discussions, not the AgentBox core.

## 1. World-model runtime

The autonomous OS source describes a persistent world-model runtime receiving perception data and maintaining a consistent shared understanding of the environment. It connects perception, planning, simulation, validation, persistent memory and action.

## 2. Embodied/autonomous system capabilities

The source references:
- Mission planning and dynamic replanning.
- Distributed planning and shared world models.
- Simulation synchronization.
- Mission validation.
- Embodied memory.
- Vision-language-action (VLA) runtime.
- Digital twins and simulation/training validation.
- Fleet deployment and lifecycle management.
- Telemetry, diagnostics and fault tolerance.

These capabilities are useful if AgentBox later evolves agents that operate robots, digital twins or external environments. They are not required for ordinary software agents.

## 3. Cognitive state graph

The AGI consolidation source emphasizes persistent cognitive state, including:
- Working memory.
- Episodic memory.
- Semantic memory.
- Procedural memory.
- Reflective memory.
- World model and cognitive loop.

The source's conceptual lifecycle connects perception, memory, world-state update, reasoning, planning, action and learning.

## 4. AgentBox extension model

If embodied agents are added later, they should be represented as agent packages with:
- Environment and simulator contract.
- Perception/action interfaces.
- Safety envelope and physical constraints.
- World-model schema.
- Planning policy.
- Simulation benchmark.
- Hardware/robot compatibility metadata.
- Human override and emergency stop policy.

## 5. Boundary

Do not import robot/drone control code into the generic AgentBox runtime. Physical actuation requires separate safety engineering, simulation, hardware-in-the-loop testing and deployment approval.
