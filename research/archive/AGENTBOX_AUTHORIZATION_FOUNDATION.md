# AgentBox authorization foundation

This batch adds policy evaluation primitives only. It does not add an HTTP authentication mechanism, identity provider, policy administration endpoint, secret resolver, capability invoker, or enforcement middleware.

## Ten implementation batches

1. Principal identity value object with user, tenant, service, and system types.
2. Versioned authorization policy JSON Schema.
3. Strict policy schema validator.
4. Deny-by-default capability authorization evaluator.
5. Exact principal and tenant matching.
6. Exact action and resource matching; no wildcard expansion.
7. Explicit deny precedence over matching allow policies.
8. Time-window checks for not-before and expiry.
9. Append-only SQLite decision audit store with update/delete guards.
10. Focused tests for principal, policy, authorization and audit behavior.

## Enforcement boundary

These primitives are not yet wired into the execution endpoint. The API currently has no authenticated principal source. Passing a caller-supplied identity would be unsafe. Capability execution remains disabled until trusted authentication, tenant resolution, authorization enforcement, secret handling, and isolation are implemented end-to-end.

Audit rows contain identifiers and decision metadata only. They do not store request payloads, credentials, or model content.

## Naming and provenance

All new code-facing identifiers use AgentBox names. Historical archive identifiers are retained only in research/provenance records.
