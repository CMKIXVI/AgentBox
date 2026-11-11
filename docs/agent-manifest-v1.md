# AgentBox Agent Manifest v1

**Status:** initial schema contract; not yet wired to an application runtime.  
**Schema:** `schemas/agent-manifest-v1.schema.json`  
**Example:** `examples/agent-manifest-v1.json`

## Purpose

An agent manifest is the portable, declarative definition of an agent. It describes what the agent is for, which versioned prompt/schema/tool/workflow/knowledge artifacts it references, which model binding it uses, and which permissions it may request.

The manifest is not executable code and is not itself an authorization grant. Runtime policy must independently authorize every tool, data, network and model operation.

## Design rules

1. **Stable identity, immutable versions.** `agent_id` identifies the logical agent; `version` identifies an immutable definition revision. A changed definition creates a new version.
2. **No embedded secrets.** Provider credentials are represented only by a secret reference such as `vault://...`. The runtime resolves it under server-side policy. Exported packages must not contain secret values.
3. **No embedded executable tool code.** Tools are referenced by ID and version range, with a permission profile and optional input/output schema references.
4. **Bounded execution.** `max_steps` and `timeout_seconds` are required. The runtime may enforce stricter limits.
5. **Least privilege.** The manifest declares requested scopes; runtime policy intersects these with the caller, tenant, environment and tool policies. A manifest cannot grant itself access.
6. **Explicit provenance.** Authored, imported, derived and generated definitions are distinguished.
7. **External artifact envelope.** Registry metadata such as content hash, parent artifact IDs, lifecycle status, creation actor and signature belongs in the registry/package envelope. It is calculated and validated by the platform, not trusted from user-supplied manifest fields.
8. **No implied portability guarantee.** `runtime_targets` declares intended targets only. Import/deployment must check actual tool, provider, model and runtime compatibility.

## Field groups

| Group | Purpose |
|---|---|
| Identity | schema version, stable agent ID, semantic version, name and description |
| Behavior | objective, versioned instruction/schema references and hard execution limits |
| Model binding | provider/model IDs, optional credential reference, parameters and routing/fallback references |
| Tools | versioned tool references and permission profiles |
| Workflow | optional workflow artifact reference |
| Memory | opt-in memory store, retention and read/write scopes |
| Knowledge | source, snapshot and retrieval-profile references with access scope |
| Permissions | requested tool/data/network scopes and actions requiring human approval |
| Policies | references to independently enforced policy artifacts |
| Dependencies | artifact references and version ranges |
| Runtime targets | intended server/web/desktop/mobile/local/remote/edge/container targets |
| Evaluation | evaluation-profile references |
| Provenance | origin, source references, creator and timestamp |

## Validation and runtime semantics

- Validate against JSON Schema Draft 2020-12 before registry insertion.
- Apply semantic validation beyond JSON Schema: resolve every reference; check version ranges; reject dependency cycles; verify tool permission profiles; ensure provider/model compatibility; and validate runtime target compatibility.
- Normalize and canonicalize the manifest before computing its content hash.
- The registry must reject attempts to overwrite an existing immutable `agent_id + version` pair with different content.
- A clone creates a new candidate version with a parent relationship in the external artifact envelope.
- A mutation is a proposed manifest change. It must not be promoted until evaluation and policy gates pass.
- Imported manifests are untrusted input. Enforce size/depth limits and safe reference resolution to prevent path traversal, SSRF and dependency-confusion attacks.
- `credential_ref` is a locator, not proof of authorization. The runtime must check that the invoking principal is allowed to use the referenced secret.

## Known v1 limitations

- This schema does not define a complete workflow graph format.
- It does not define the secret manager, provider adapter protocol, tool execution protocol or sandbox.
- It does not define package signatures, registry API or database schema.
- It does not guarantee that a referenced model or tool exists or can run offline.
- Schema validation alone does not make an agent safe or production-ready.

## Next implementation step

Build a schema validator and immutable registry operations: create, validate, fetch, list and clone. Add negative tests for unknown fields, invalid versions, out-of-range step/time limits, malformed references and attempts to embed credentials.