# AgentBox OIDC authentication foundation

This change adds a provider-neutral boundary around verified OIDC bearer identity.
It is a security foundation, not a declaration that every API route is protected.

## Ten implementation units

1. Add a maintained JWT/JWKS verification dependency with cryptographic support.
2. Define the versioned authentication configuration schema.
3. Validate HTTPS issuer/JWKS endpoints, audience, tenant claim, timeout and algorithm allowlist.
4. Parse bearer credentials strictly and bound token size.
5. Resolve signing keys from the configured JWKS endpoint with a bounded timeout.
6. Verify signature, issuer, audience, expiration and issued-at claims.
7. Reject unsupported algorithms, missing subject/tenant claims and inactive identities.
8. Construct an AgentBox Principal only from verified claims; ignore caller-provided identity headers.
9. Provide a FastAPI dependency that fails closed when authentication is absent or invalid.
10. Add cryptographic, schema, claim-validation and fail-closed tests plus this operational guide.

## Configuration

Set these environment variables in the API deployment:

- `AGENTBOX_OIDC_ISSUER`: exact HTTPS issuer expected in the token's `iss` claim.
- `AGENTBOX_OIDC_AUDIENCE`: API audience expected in `aud`.
- `AGENTBOX_OIDC_JWKS_URI`: HTTPS JWKS endpoint for signing-key lookup.
- `AGENTBOX_OIDC_TENANT_CLAIM`: claim containing the authenticated tenant identifier.
- `AGENTBOX_OIDC_ALGORITHMS`: optional comma-separated asymmetric algorithm allowlist; defaults to `RS256`.
- `AGENTBOX_OIDC_LEEWAY_SECONDS`: optional clock skew allowance, 0–60; defaults to 0.
- `AGENTBOX_OIDC_JWKS_TIMEOUT_SECONDS`: optional JWKS network timeout, 1–15; defaults to 5.

Do not put tokens, private keys, client secrets or signing secrets in this configuration.
The runtime accepts only HTTPS issuer and JWKS URLs and asymmetric algorithms from a fixed
allowlist. The tenant claim is mandatory. The raw bearer token is never returned or stored
by this module.

The versioned JSON Schema is at
`schemas/authentication-config-v1.schema.json`; validation is available through
`validate_authentication_config`.

## FastAPI integration boundary

Use `require_authenticated_principal` as a dependency on protected endpoints, then pass
the resulting `Principal` explicitly into authorization evaluation. Do not construct a
principal from request JSON, query parameters, tenant headers or unverified JWT payloads.

This PR deliberately does **not** attach the dependency to existing API routes yet.
The existing routes and tests predate an authentication contract; protecting them safely
requires a separate route-by-route authorization mapping and test update. Until that work
is completed, do not expose the API to untrusted networks or treat this PR as route-level
authentication. The capability execution endpoint remains denied for tool-enabled agents.

## Remaining production gates

- Route inventory and explicit public/protected classification.
- Authentication dependency on every protected read/write/execution route.
- Principal-to-policy enforcement at the capability invocation boundary.
- Tenant-scoped data access and cross-tenant isolation tests.
- Production JWKS rotation, outage, cache and key-revocation behavior validation.
- Deployment-level TLS, trusted proxy and secret/configuration management.
