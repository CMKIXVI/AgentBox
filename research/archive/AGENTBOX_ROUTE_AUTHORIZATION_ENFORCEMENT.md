AgentBox route-level authorization rollout

The API now applies verified bearer authentication and explicit capability policies to stateful /v1 routes. Only health and schema-validation endpoints remain public; those validation endpoints are intentionally side-effect-free and do not read or mutate stored records.

## Protected route matrix

| Route family | Capability | Action | Resource |
|---|---|---|---|
| Create agent | agent.registry | agent.create | manifest agent ID |
| List/get agent versions | agent.registry | agent.read | agent ID |
| Clone agent version | agent.registry | agent.clone | source agent ID |
| Start execution | agent.execution | agent.execute | agent ID |
| Read execution | agent.execution | execution.read | execution's agent ID |
| Create evaluation profile | evaluation.profile | profile.create | profile ID |
| List/get evaluation profiles | evaluation.profile | profile.read | profile ID |
| Submit evaluation | agent.evaluation | evaluation.create | agent ID plus profile read |
| Read/list evaluations | agent.evaluation | evaluation.read | evaluation's agent ID |

Every decision is evaluated against the authenticated principal's exact subject, principal type and tenant ID. Exact resource and action matching applies; no wildcard expansion is performed. Explicit deny overrides allow. Missing policy grants deny access.

## Deployment policy file

Set AGENTBOX_AUTHORIZATION_POLICIES_PATH to a mounted JSON file containing an array of versioned AgentBox authorization policies. Each policy is validated against schemas/authorization-policy-v1.schema.json at application startup. Missing configuration loads an empty policy set, so protected requests are denied. A malformed policy file prevents startup rather than silently weakening access control.

The OIDC settings documented in AGENTBOX_OIDC_AUTHENTICATION_FOUNDATION.md are also required to establish the principal. Do not trust identity or tenant headers supplied by clients.

## Explicit security limits

This change enforces authentication and policy checks at the API route boundary, but it does not yet provide storage-level tenant partitioning. Agent, execution, evaluation-profile and evaluation-run rows do not yet all carry an immutable tenant owner, and registry/service queries are not yet tenant-filtered. Policy checks are therefore a necessary authorization gate, not a substitute for tenant ownership enforcement. Do not expose the service as a multi-tenant production system until storage ownership, tenant-scoped reads/writes, migration behavior and cross-tenant isolation tests are implemented.

Policy files are loaded at process startup. Policy hot reload, policy administration APIs, revocation propagation, durable decision audit correlation and key-rotation operations remain future work. Capability execution remains restricted for tool-enabled agents.
