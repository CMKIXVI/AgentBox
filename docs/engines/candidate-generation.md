# AgentBox bounded candidate generation

**Status:** first bounded candidate-generation runtime slice implemented; candidates are unverified and cannot be promoted by this service.

## Purpose

Create a new immutable agent manifest version from an existing tenant-scoped parent. This is a controlled configuration mutation facility, not arbitrary code generation or self-modifying runtime behaviour.

## API

`POST /v1/agents/{agent_id}/versions/{version}/candidates`

Request fields:

- `candidate_version`: new semantic version; an existing version is never overwritten.
- `operator_ids`: one to five unique registered mutation operators.
- `seed`: integer from 0 through 4294967295; determines deterministic operator ordering.

The route requires the existing active-tenant principal and the existing `agent.registry / agent.clone` authorization grant.

## Registered operators

| Operator | Allowed path | Bound |
|---|---|---|
| `behavior.max_steps.decrement` / `increment` | `/behavior/max_steps` | 1–100 |
| `behavior.timeout_seconds.decrement` / `increment` | `/behavior/timeout_seconds` | 1–3600 seconds; 5-second steps |
| `model.parameters.temperature.lower` / `higher` | `/model_binding/parameters/temperature` | 0.0–2.0; 0.1 steps |
| `model.parameters.top_p.lower` / `higher` | `/model_binding/parameters/top_p` | 0.0–1.0; 0.05 steps |

The operator registry is closed by default. Unknown operators, duplicate operators, invalid seeds, invalid semantic versions, no-op mutations and schema-invalid candidates are rejected.

## Protected boundaries

The candidate generator preserves the parent’s schema version, agent identity, tools and permissions. It does not mutate tenant ownership, credentials, authorization policies, secrets, runtime isolation or deployment targets. No operator can be supplied as arbitrary code or a JSON path.

The candidate receives a new immutable registry version, a parent artifact reference and mutation/operator provenance. The parent manifest and hash remain unchanged.

## Trust and promotion

The API returns `trust_status=unverified_candidate` and `promotion_eligible=false`. It does not execute the candidate, evaluate it, approve it, change an active-version pointer or promote it to production. Those functions require the trusted runner, same-workload parent/candidate comparison, mandatory gates and approval workflow described in the autonomous improvement architecture.

## Verification scope

The API tests cover bounded mutation, schema-valid materialization, immutable parent preservation, security-field preservation, unknown operator rejection, invalid seeds, no-op rejection and duplicate candidate-version conflicts. CI remains the authoritative execution environment for Ruff and pytest.
