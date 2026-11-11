# Source Extraction — Agent Factory OS / AgentBox

**Primary source:** `2026/Agent Factory OS Concept.md` in `chatgpt_22-26.zip`.

This document extracts the recurring AgentBox platform architecture from the source conversation. It is a source-derived consolidation, not an assertion that every proposed capability is implemented or technically validated.

## 1. Product identity and first principles

The source explicitly names AgentBox OS and frames it as an agent-native operating system / resource operating system, rather than only an agent builder, workflow tool, marketplace or chat application.

Repeated first principles:
- Everything is a resource.
- Everything is discoverable.
- Everything is versioned.
- Everything is governed.
- Everything is deployable.
- Agents are primary execution units.
- Complex agents are composed from smaller agents and capabilities.
- The platform itself is operated through specialized factory/system agents.

The source's resource-oriented model lists Agent, Workflow, Tool, Knowledge, Model, Memory, Policy, Human, Organization, Project, Team, Deployment and Marketplace Asset. Shared resource properties include identity, version, ownership, permissions, relationships, audit history and lifecycle state.

## 2. Resource graph and event bus

The platform is described as a graph:
- Nodes: agents, tools, workflows, models, knowledge, humans, organizations, projects and deployments.
- Edges: uses, owns, depends on, calls, controls, creates, deploys and collaborates with.

An event bus is a separate platform primitive. The source repeatedly emphasizes event generation around resource operations and workflow execution. AgentBox should preserve event provenance so mutations, tests, evaluations, approvals and deployments are traceable.

## 3. Universal Agent Definition (UAD)

The source's TypeScript interface contains:
- id, name, description, version
- model configuration
- tools
- workflows
- permissions
- memory configuration
- knowledge bases
- deployment targets
- billing configuration
- metadata

A Tool schema includes identity/name/description, authentication configuration, input schema and output schema.

The source also names agent DNA as capabilities, tools, knowledge, workflows, behaviors, history, performance and dependencies. It describes cloning, forking, merging and evolving agents.

**Important separation:** Agent DNA is an agent-behavior/configuration genome. It is not equivalent to a foundation model's neural weights or architecture. AgentBox must not imply that arbitrary LLM weights can be crossed or merged just because agent manifests can be combined.

## 4. Agent lifecycle management (ALM)

The source proposes a registry for agents, workflows, tools, knowledge packs, deployment packages and templates. Each asset has:
- Unique ID
- Semantic version
- Publisher and owner
- Tags and status
- Dependencies

Semantic versioning is explicitly described as MAJOR.MINOR.PATCH:
- PATCH: prompt fixes, minor bug fixes and documentation changes.
- MINOR: workflow enhancements, new tools and additional features.
- MAJOR: architecture/runtime changes and breaking changes.

The package format named in the source is `.agentpkg`, with:
- `agent.yaml`
- `workflow.json`
- `tools.json`
- `permissions.json`
- `knowledge.json`
- `metadata.json`
- `tests/`
- `docs/`

The manifest should declare runtime requirements, dependencies, tool requirements, permissions and deployment targets.

## 5. Git-like versioning and safe change management

The source specifies:
- Forking installed assets without overwriting the upstream asset.
- Commits for prompt, workflow, tool, permission and knowledge changes.
- Commit ID, author, timestamp, description and diff.
- Branches such as Main, Development, Testing and Production.
- Compare, diff, merge, rebase and promotion.
- Compatibility analysis before updates.
- Manual, scheduled or automatic update policies.
- One-click rollback and permanent preservation of prior versions.

These are core lifecycle concepts. The MVP should start with immutable snapshots and parent-version references; branches, rebase and marketplace sync can follow later.

## 6. Agent factory and composition

The source describes a factory pipeline:
1. User intent / requirements.
2. Architecture.
3. Workflow.
4. Tool selection/design.
5. Knowledge selection.
6. Security review.
7. Testing.
8. Deployment.
9. Published agent.

It describes composition over complexity: a larger agent can contain planner, scheduler, reporting, risk, financial and coordinator agents.

Factory/system roles named in the source include Agent Architect, Agent Builder, Workflow Architect, Tool Architect, Knowledge Architect, Model Architect, Security Architect, Testing Architect, Deployment Architect, Billing Agent, Marketplace Agent and Governance Agent.

## 7. Runtime, compiler and model routing

The source includes separate concepts for:
- Agent runtime.
- Agent compiler/adapters.
- Workflow engine.
- Model registry.
- Model management agent.
- Model orchestration/routing.

The compiler examples refer to adapters for external agent frameworks. These are source ideas, not a mandate to adopt a third-party framework. The model routing material discusses capability-aware selection, model/provider configuration, failover, benchmarking, cost and governance.

AgentBox should keep the runtime contract independent from any one model provider or agent framework.

## 8. Security and governance

The source calls for:
- Agent approval and certification.
- Agent risk scoring and access policies.
- Approved/blocked model lists, risk ratings and licensing validation.
- Tool approval, certification and risk assessment.
- Workflow reviews, promotion and certification.
- A policy engine for security, compliance, cost and usage policies.
- Human approval for production assets.

The source's certification levels are Draft, Verified, Certified and Enterprise Certified.

All execution should pass through policy evaluation. Production promotion should require approval and evidence.

## 9. Testing and deployment

The source names unit, integration, API, widget, end-to-end, load and security tests, with a stated 90%+ coverage target in one section. That percentage is a proposal from the source, not a measured result or a universal guarantee of quality.

Deployment modes mentioned across the document include local, hosted, cloud, private cloud, hybrid, on-premises, edge, offline and air-gapped environments.

## 10. Self-evolution concept

The source describes a feedback loop:
- Observe usage.
- Analyze performance.
- Suggest improvements.
- Generate new versions.
- Create upgrade plans.
- Request approval.
- Deploy upgrades.

The key safety implication is that self-evolution should create candidate versions, not directly overwrite a live version. The approval and rollback mechanisms described elsewhere in the same source should govern any promotion.

## 11. AgentBox MVP implications

Source-derived minimum:
- A validated Agent Definition.
- Immutable agent versions.
- A registry.
- Clone/fork from a parent version.
- Controlled changes to prompts, tool declarations, workflow and policy metadata.
- A test suite attached to each agent version.
- Evaluation records linked to the exact version and test run.
- Explicit approval/promotion state.
- Rollback by reactivating a previous immutable version.

Deferred:
- Full marketplace, billing, hiring marketplace, multi-tenant enterprise topology, offline packages, full Git-style rebase, broad compiler adapters and weight-level model genetics.

## Source integrity notes

The source document is a long exported conversation containing repeated and evolving specifications. This extraction consolidates recurring requirements; it does not imply that every repeated statement is a separate feature or that the source snippets form a complete runnable implementation.
