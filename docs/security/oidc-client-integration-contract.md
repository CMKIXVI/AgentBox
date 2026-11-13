# AgentBox OIDC client integration contract

**Status:** Provider-neutral integration contract; identity-provider selection remains open  
**Applies to:** Next.js web console, Flutter operational client, FastAPI API  
**Security authority:** FastAPI validates access tokens and derives the AgentBox principal and tenant

## 1. Decision

AgentBox uses standard OpenID Connect (OIDC) rather than a provider-specific frontend authentication implementation. Keycloak, Microsoft Entra ID, Auth0, or another conformant provider may be selected later without changing the API authorization model.

This document does not select or deploy an identity provider. Do not hard-code provider endpoints, tenant claim names, client IDs, secrets, or callback URLs until the deployment decision is made.

## 2. Protocol and client patterns

### Next.js web console

Use Authorization Code Flow with PKCE. Prefer a backend-for-frontend (BFF) session boundary:

1. Browser navigates to the configured provider authorization endpoint.
2. Next.js creates and validates state, nonce, and PKCE verifier; callback URI is registered exactly at the provider.
3. The callback exchanges the authorization code server-side.
4. Next.js creates an opaque, server-managed session and sets only a session identifier in a Secure, HttpOnly, appropriately SameSite cookie.
5. Server-side route handlers obtain a short-lived API access token from the session and call AgentBox FastAPI with an Authorization: Bearer header.
6. Logout invalidates the local session and follows the provider's supported logout behavior.

Access tokens, refresh tokens, client secrets, and PKCE verifiers must not be exposed to browser JavaScript, placed in local/session storage, or embedded in the Next.js client bundle. The current Auth.js JWT session is encrypted and carried in an HttpOnly cookie; this is not a separate database-backed opaque session store, so cookie size, rotation, revocation and key-rotation behavior require deployment validation. Never use an ID token as the API access token.

### Flutter mobile client

Use Authorization Code Flow with PKCE through the operating system's external browser and a registered app redirect (verified app/universal link where supported). Use a maintained OIDC/AppAuth implementation and platform-protected credential storage. Do not implement an embedded password form or embedded webview login.

The Flutter client supplies a short-lived API access token to the existing injected AccessTokenProvider. Refresh credentials, if issued, remain in secure platform storage and are handled by the authentication library. Logout clears local credentials and invokes provider logout/revocation where supported.

## 3. FastAPI API contract

The API remains the authority for authentication and authorization:

- Accept only signed access tokens intended for the configured AgentBox API audience.
- Validate signature against the configured provider JWKS, exact issuer, audience, expiry, issued-at, and required subject.
- Use an explicitly configured, verified tenant claim. Never infer tenant from email, username, URL, request body, or client header.
- Reject missing, malformed, expired, wrong-issuer, wrong-audience, inactive, or tenant-less principals.
- Enforce resource authorization and tenant isolation on every protected route.
- Do not accept a client-supplied X-Tenant-ID as authority.
- Keep public endpoints explicitly allowlisted in the route inventory.

The current backend configuration is environment-driven:

| Variable | Meaning |
|---|---|
| AGENTBOX_OIDC_ISSUER | Exact issuer identifier |
| AGENTBOX_OIDC_AUDIENCE | API audience expected in access tokens |
| AGENTBOX_OIDC_JWKS_URI | HTTPS JWKS endpoint |
| AGENTBOX_OIDC_TENANT_CLAIM | Provider claim mapped to AgentBox tenant ID |
| AGENTBOX_OIDC_ALGORITHMS | Asymmetric signing algorithm allowlist; default RS256 |
| AGENTBOX_OIDC_LEEWAY_SECONDS | Clock-skew allowance, 0–60 seconds |
| AGENTBOX_OIDC_JWKS_TIMEOUT_SECONDS | JWKS request timeout, 1–15 seconds |

Keep these values in deployment configuration or a secret/configuration manager, not source control. The tenant claim must be populated by a trusted identity/tenant provisioning process; a user-editable profile attribute is not sufficient.

## 4. Provider onboarding checklist

Before enabling login in a deployment, record and review:

- [ ] Provider and tenant/realm identity
- [ ] Exact issuer URL and discovery document
- [ ] API audience/resource identifier and access-token format
- [ ] HTTPS JWKS endpoint and signing algorithm
- [ ] Stable subject claim
- [ ] Trusted tenant claim and provisioning/assignment process
- [ ] Web client ID, exact callback and post-logout URLs
- [ ] Native Flutter client ID, redirect URI and allowed app platforms
- [ ] Required scopes and consent model
- [ ] Access-token lifetime, refresh-token rotation and revocation behavior
- [ ] Account deactivation and tenant membership removal behavior
- [ ] Key rotation, outage, clock-skew and recovery tests

Do not assume that the default OIDC sub claim is a tenant identifier. Do not assume a provider emits the configured tenant claim in access tokens; verify a real, non-production token and its signature before deployment.

## 5. Required security tests

### Protocol and token tests

- Authorization code cannot be replayed.
- State and nonce mismatches fail closed.
- PKCE verifier mismatch fails.
- Redirect URI mismatch is rejected.
- Wrong issuer, audience, signature, algorithm, expiry, or missing claims return 401.
- Missing/invalid server OIDC configuration returns 503, not anonymous access.
- JWKS rotation and unknown key IDs are handled safely.
- Provider/JWKS outage fails closed without bypassing authentication.

### Session tests

- Web session cookie is Secure, HttpOnly and SameSite-configured.
- Session identifier rotates after authentication and privilege changes.
- CSRF protections cover state-changing browser requests.
- Tokens and secrets are absent from browser storage, URLs, logs, analytics and error messages.
- Flutter credentials are stored only in platform-protected storage.
- Logout clears local session state; revoked/deactivated accounts lose access within the documented token/session lifetime.

### Tenant and authorization tests

- Two tenants cannot read or mutate each other's resources.
- Forged tenant headers and request-body tenant IDs have no effect.
- A valid user token without tenant membership is rejected.
- Disabled tenant/user access is denied.
- Every protected route is covered by negative authorization tests.

## 6. Rollout gates

1. Select provider and complete the onboarding checklist.
2. Configure a non-production realm/tenant and test clients.
3. Validate real access tokens against the backend using provider-issued JWKS.
4. Configure and validate the Next.js encrypted-cookie BFF session and Flutter AppAuth integration.
5. Run protocol, session, tenant-isolation, and authorization tests.
6. Exercise both clients against a deployed non-production API.
7. Enable production login only after security review, monitoring, key-rotation and recovery procedures are approved.

Current feature-branch implementation includes Next.js Auth.js OIDC sign-in with PKCE/state/nonce, an encrypted HttpOnly session cookie, server-side refresh logic and a same-origin API proxy, plus Flutter AppAuth and secure-storage token refresh. Native redirect registration, real provider/JWKS validation, cookie/session lifecycle review, and deployed client-to-API end-to-end tests remain mandatory. A green unit-test workflow is not proof of provider integration or production authentication readiness.
