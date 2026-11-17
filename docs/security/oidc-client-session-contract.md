# OIDC client and session integration contract

**Status:** Provider-neutral interface; no live identity provider is configured.

## Authority and trust boundaries

- The existing FastAPI OIDC verifier remains the only authority that turns a bearer JWT into an AgentBox principal.
- The configured issuer, audience, signing algorithms, JWKS URI, subject claim, and tenant claim are validated by the backend.
- The backend derives tenant context from the verified token. A client-selected tenant, URL parameter, request body, or header is never proof of tenant membership.
- The client session is a credential-delivery boundary only. It cannot grant permissions or override backend authorization.

## Required login protocol

When a provider is selected, use Authorization Code Flow with PKCE (S256) through a maintained OIDC SDK or reviewed server-side BFF integration. Do not implement cryptography, nonce/state validation, token exchange, discovery, JWKS verification, or refresh-token rotation manually.

The selected adapter must:
1. Discover and pin the expected issuer; validate issuer and redirect URI.
2. Generate cryptographically random state, nonce, and PKCE verifier/challenge using the SDK.
3. Use exact registered redirect URIs and Authorization Code + PKCE (S256).
4. Validate state, nonce, issuer, audience, signature, and token time claims through the SDK.
5. Keep client secrets exclusively on the server; public/native clients must not contain a client secret.
6. Keep web session cookies HttpOnly, Secure, and appropriately SameSite; use CSRF protection for state-changing cookie-authenticated BFF routes.
7. Use platform-protected secure storage for native refresh credentials. Never use browser localStorage, IndexedDB, app preferences, or plaintext files for tokens.
8. Rotate refresh tokens where supported, revoke on logout where supported, and clear local session state.
9. Supply only a short-lived access token to the existing AgentBox API transport.
10. Never pass tenant authority from the UI. Tenant claim mapping is configured and checked server-side.

## Safe post-authentication return targets

The Next.js client includes `src/lib/safe-return-target.ts`, a standalone navigation helper for a future callback or sign-in flow. It accepts only root-relative same-origin paths and rejects absolute/protocol-relative URLs, backslashes, control characters, encoded path separators, malformed encodings, and dot-segment traversal. It returns a validated fallback when input is unsafe. This helper is not yet wired to a login flow, does not validate OIDC state or nonce, and is not an authorization control. A future provider adapter must use a maintained OIDC SDK/BFF and independently validate the protocol response before using any return target.

## Provider-neutral Next.js BFF security primitives

`frontend/nextjs/console/src/lib/bff-security.ts` defines testable cookie attributes and a strict CSRF request guard for a future Next.js BFF:
- Production session cookies use the `__Host-agentbox_session` name, `HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/`, and no Domain attribute. Development uses a separate non-`__Host-` cookie name so local HTTP remains usable.
- Cookie lifetime is bounded to eight hours; clearing uses the same cookie scope with immediate expiry.
- The configured public web origin must be an exact HTTPS origin (HTTP is accepted only for localhost development).
- State-changing requests require an exact `Origin` match and reject `Sec-Fetch-Site: cross-site` or `none`. Safe methods do not require CSRF headers.

These are policy helpers only. No cookie is issued or read, no session identifier is generated or stored, no CSRF token is issued, and no BFF route exists yet. Every future route must authenticate the session, apply this guard before processing mutations, and enforce FastAPI authorization for the underlying operation.

## Provider-neutral BFF upstream boundary

`frontend/nextjs/console/src/lib/bff-upstream.ts` adds a tested request-policy boundary for a future Next.js BFF:
- Backend origin is configured server-side and must be HTTPS, except localhost development.
- Only existing AgentBox client operations are allowlisted: health GET, agent creation POST, agent-version collection/detail GET, and execution-detail GET.
- Version-list query parameters are limited to bounded, unique `limit` and `offset` values. Other routes reject query strings.
- Path traversal, encoded separators, backslashes, malformed encodings, and unlisted methods/routes fail closed.
- Only `Accept` and `Content-Type` are forwarded by the header helper. Browser cookies, Authorization, tenant/user identity, host, and forwarded headers are not copied.
- Request bodies are limited to JSON POST operations; safe methods must be bodyless.

This remains a policy layer, not an HTTP proxy. No Next.js route handler exists, no session cookie is read, no server-side access token is attached, and no backend request is made. A future route must obtain identity only from the server session adapter, attach its server-derived bearer token, and let FastAPI enforce authorization and tenant isolation.

## BFF HTTP envelope and response policy

`frontend/nextjs/console/src/lib/bff-http-policy.ts` adds provider-neutral policy helpers for a future route layer:
- Validate exact-origin/Fetch-Metadata CSRF policy before reading a mutation body.
- Accept only bodyless safe methods or JSON POST bodies.
- Require a declared, positive request Content-Length no larger than 1 MiB for body-bearing operations. A future route must additionally enforce the same limit while consuming the request stream; the header alone is not proof of actual size.
- Reject upstream redirects and accept only JSON or problem-JSON responses, with a 2 MiB declared response-length ceiling.
- Relay only content type plus fixed no-store, pragma, and nosniff headers. Never relay Set-Cookie, Location, server-identification, or upstream cache headers.
- Provide manual-redirect, no-store, ambient-credential-omitting fetch options and server-generated UUID correlation IDs.
- Provide a stable non-sensitive JSON error envelope for policy failures.

These helpers do not read or limit a stream, perform a fetch, authenticate a session, attach a bearer token, or implement a route. The eventual route must enforce byte limits while streaming, authenticate from a server-side session, derive the bearer token server-side, and preserve FastAPI authorization and tenant isolation.

## Client adapter ports

- Next.js: `frontend/nextjs/console/src/lib/auth-session.ts` defines the read-only session port and fail-closed access-token provider. The future provider SDK/BFF implements `SessionReader`.
- Flutter: `frontend/flutter/lib/auth_session.dart` defines the equivalent port. The future native OIDC adapter implements `AgentBoxSessionReader` and must use platform secure storage through a maintained SDK.
- Both access-token providers reject missing or near-expiry sessions. They do not refresh or persist tokens.
- Existing `AgentBoxApiClient` transports continue to receive an injected access-token provider. No duplicate API auth path is introduced.

## Provider-neutral UI session gates

- Next.js `SessionGate` and Flutter `AgentBoxSessionGate` read the existing session port and expose loading, authenticated, and unauthenticated presentation states.
- Both require a non-empty subject, non-empty access token, and expiry more than 30 seconds in the future.
- At 30 seconds before expiry, each gate re-reads its session adapter. If the adapter returns a refreshed valid session, the timer is rescheduled; otherwise protected UI is removed and the unauthenticated state is rendered.
- A session-reader exception fails closed. If the reader is replaced while a read is pending, only the newest read may update the gate; stale successes and failures are ignored. Flutter invalidates in-flight reads with a monotonically increasing generation and cancels the prior timer. Next.js combines effect cleanup with a read-generation guard. Timers are cleaned up on reader/state changes and disposal/unmount.
- These gates do not redirect, initiate login, or imply that a user is authorized for any backend resource.
- Every protected API operation must still pass FastAPI authentication, tenant isolation, and exact authorization checks.

## Required provider/deployment inputs

Before enabling live login, record and validate:
- Provider product and tenant/realm
- Exact issuer URL and discovery metadata
- Public web client ID and native mobile client ID (or provider-supported shared public client)
- API audience/resource identifier
- Exact web and mobile redirect URIs and post-logout redirect URIs
- Backend tenant claim name and authoritative claim issuance/mapping
- Allowed signing algorithms and key rotation behavior
- Web BFF/session deployment origin, cookie domain and CSRF strategy
- Native app identifiers and platform redirect configuration
- Logout, refresh, account disablement, and session revocation behavior

Never commit client secrets, signing keys, refresh tokens, or production credentials.

## Acceptance tests before enabling login

- Valid login, callback, state, nonce, PKCE, issuer and audience.
- Invalid/replayed state, nonce mismatch, wrong issuer/audience, expired token, and signature/key rotation failures.
- Missing or expired session fails closed before an API request.
- API requests attach only the access token and never a tenant-authority header.
- Tenant A cannot access Tenant B resources, including by guessed IDs.
- Disabled users and revoked sessions are rejected.
- Logout clears the client session and prevents subsequent protected API calls.
- Browser cookie flags, CSRF, redirect allowlist, and absence of browser token storage are verified.
- Native credentials use platform-protected storage and are not present in logs, crash reports, or backups.

## Current limitation

The provider-neutral session ports, API transport adapters, and UI gates are implemented and unit-tested, including expiry-boundary rechecks. This does not create a functional sign-in button, OAuth callback, token exchange, refresh mechanism, logout flow, BFF, provider configuration, or live identity-provider connection. Those require a provider decision and registered client applications.
