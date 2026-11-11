// Extracted from: 2026/Agent Factory OS Concept.md
// Source block: TypeScript AgentDefinition interface.
// Supporting types (ModelConfig, Tool, Workflow, Permission, MemoryConfig,
// KnowledgeBase, DeploymentTarget, BillingConfig, Metadata) are defined elsewhere
// in the source conversation and are not included in this excerpt.

interface AgentDefinition {
  id: string
  name: string
  description: string
  version: string

  model: ModelConfig

  tools: Tool[]

  workflows: Workflow[]

  permissions: Permission[]

  memory: MemoryConfig

  knowledgeBases: KnowledgeBase[]

  deploymentTargets: DeploymentTarget[]

  billing: BillingConfig

  metadata: Metadata
}
