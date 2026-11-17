# Agent Factory contract reconciliation

Status: research-to-implementation mapping; no recovered source code is imported by this document.

## Decision

AgentBox already has a stronger, versioned manifest contract than the small Agent Factory OS fragments recovered from the archive. Do not replace the existing manifest schema with a second Universal Agent Definition. Extend AgentBox only where a concrete gap is demonstrated, and keep runtime execution behind existing authorization and isolation gates.

All accepted implementation names, modules, identifiers and interfaces MUST use AgentBox naming. Historical lineage labels below are source provenance only.

## Evidence examined

Archive entries (from `Extracted_Code_Archive_Combined.zip`):

- `code/Agent_Factory_OS_Concept__Universal_Agent_Definition_UAD__b040.ts` — AgentDefinition with id, name, description, version, model, tools, workflows, permissions, memory, knowledgeBases, deploymentTargets, billing, metadata.
- `code/Agent_Factory_OS_Concept__Universal_Agent_Definition_UAD__b165.ts` — later/minimal AgentDefinition with id, name, description, model, tools, workflows, memory, permissions, knowledgeBases, deploymentTargets.
- `code/Agent_Factory_OS_Concept__Universal_Agent_Definition_UAD__b103.json` — illustrative JSON agent example; not a formal schema.
- `code/Agent_Factory_OS_Concept__Tool_Registry__b042.ts` and `b168.ts` — Tool shape: id, name, description, auth, inputSchema, outputSchema.
- `code/Agent_Factory_OS_Concept__Workflow_Engine__b169.ts` — node categories Agent, Tool, Decision, Human Approval, Loop, Trigger.
- `code/Agent_Factory_OS_Concept__Workflow_Engine__b170.json` — empty nodes/edges graph envelope.
- `code/Agent_Factory_OS_Concept__Agent_Versioning__b004.json` — illustrative agentId/version/status record.

These are small fragments, not a complete executable Agent Factory implementation. The package-layout and Agent DNA references in the source lineage register remain specification leads until the exact blocks and semantics are reassembled.

## Existing AgentBox contract baseline

The current main-branch `schemas/agent-manifest-v1.schema.json` already provides:

| Recovered concept | Existing AgentBox representation | Assessment |
|---|---|---|
| Agent identity/name/description/version | `agent_id`, `name`, `description`, `version` | Covered; retain AgentBox field names |
| Model selection | `model_binding.provider_id/model_id` | Covered, with credential references and routing extension points |
| Tool references | `tools[].tool_id/version_range/permission_profile` plus input/output schema refs | Partial; no executable tool registry or authorization implementation is implied |
| Workflow attachment | `workflow_ref` | Partial; no first-class workflow graph contract yet |
| Memory | `memory` store, retention and scopes | Covered as references/configuration, not a memory runtime |
| Knowledge bases | `knowledge_sources[]` with source/snapshot/retrieval refs | Covered as references |
| Permissions | `permissions.tool_scopes/data_scopes/network_profiles/human_approval_actions` | More explicit than source fragments |
| Deployment targets | `runtime_targets` | Covered with AgentBox enum |
| Billing | no dedicated billing object | Not yet covered; defer until billing requirements and trust boundaries are specified |
| Metadata | tags and provenance | Partial; provenance is authoritative, avoid an unbounded duplicate metadata bag |
| Version lifecycle | immutable registry, content hash, parent artifact lineage | Covered for create/version/clone lineage; publish/promote/rollback lifecycle still needs explicit state model |

The current API uses `AGENTBOX_DATABASE_PATH` and `AGENTBOX_SCHEMA_PATH`; do not introduce legacy-name environment aliases.

## Canonical AgentBox design decisions

1. Keep `agent-manifest-v1` authoritative. A new schema version is required for breaking contract changes.
2. Model workflow graphs as separately versioned AgentBox artifacts referenced by `workflow_ref`. A workflow artifact should define typed nodes, edges, entry/exit constraints, bounded loops, decision expressions, trigger contracts, and human-approval suspension/resumption. Do not put executable source code in the manifest.
3. Model tools as separately versioned AgentBox capability artifacts. Their contracts must include input/output JSON Schema references, declared authentication mechanism, permission profile, timeout/resource limits, and audit requirements. Credentials remain secret references and never appear in source or manifests.
4. Treat a human-approval node as a policy-enforced pause/resume boundary, not merely a visual node type.
5. Treat version status as a lifecycle record linked to immutable artifact versions. Avoid mutating immutable manifest content to change publication state.
6. Treat a portable agent package as a signed, content-addressed bundle of an AgentBox manifest plus referenced workflow/tool/knowledge artifacts and optional indexes. Do not assume a bundled database file is portable, safe, or authoritative; define import validation and trust policy first.
7. Keep Agent DNA, workflow graphs, retrieval profiles and neural/genetic model weights as distinct domain models. Similar words such as mutation, genome and fitness do not establish interchangeable data contracts.

## Gaps to implement in sequence

- **A — Workflow artifact contract:** define AgentBox-native schema and validation for graph nodes/edges; first implement structural validation only, no execution.
- **B — Tool capability contract:** define AgentBox-native tool descriptor and auth reference model; execution remains disabled until principal-aware authorization, isolation and audit are implemented.
- **C — Lifecycle state model:** define draft/validated/tested/published/deprecated/withdrawn as registry metadata or append-only events; enforce legal transitions and promotion evidence.
- **D — Package envelope:** define deterministic bundle manifest, hashes, signature verification interface, size limits and safe import quarantine.
- **E — DNA/mutation model:** only after Agent DNA source blocks are reassembled and reconciled with the current manifest; use immutable parent-child artifacts and bounded mutation proposals.

## Acceptance and validation gates

- Provenance: every accepted source fragment records archive path, block reference, content hash, source-document identity and review decision.
- Rights: licence/ownership is verified before copying implementation. This document does not authorize use of any source.
- Naming: all accepted code and public AgentBox interfaces use AgentBox names; historical labels remain only in provenance and required legal notices.
- Security: no recovered code execution; no arbitrary workflow expressions; no tool invocation without principal-aware authorization and sandboxing.
- Compatibility: schema migration and import/export round-trip tests are required before changing persisted formats.
- Testing: schema validation, negative cases, graph invariants, deterministic serialization, registry persistence and API contract tests.
- Readiness: structural tests do not prove live workflow execution or production isolation.

## Current conclusion

The archive fragments confirm useful design requirements but do not justify replacing AgentBox's current manifest/registry. The immediate engineering opportunity is a separate, validated workflow artifact contract and then a separately governed tool capability contract. No Agent Factory code is yet accepted as integrated.
