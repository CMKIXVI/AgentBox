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

## Client adapter and guard ports

- Next.js: `frontend/nextjs/console/src/lib/auth-session.ts` defines the read-only session port and fail-closed access-token provider. The future provider SDK/BFF implements `SessionReader`.
- Flutter: `frontend/flutter/lib/auth_session.dart` defines the equivalent port. The future native OIDC adapter implements `AgentBoxSessionReader` and must use platform secure storage through a maintained SDK.
- Both access-token providers reject missing or near-expiry sessions. They do not refresh or persist tokens.
- Existing `AgentBoxApiClient` transports continue to receive an injected access-token provider. No duplicate API auth path is introduced.

## Provider-neutral UI session gates

- Next.js `SessionGate` and Flutter `AgentBoxSessionGate` read the existing session port and expose loading, authenticated, and unauthenticated presentation states.
- Both require a non-empty subject, non-empty access token, and expiry more than 30 seconds in the future.
- Session-reader exceptions, missing sessions, incomplete sessions, and expired/near-expiry sessions fail closed.
- These gates do not redirect, initiate login, refresh tokens, or imply that a user is authorized for any backend resource.
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
- Missing or expired session fails closed before an API request or protected UI render.
- Session-reader errors fail closed.
- API requests attach only the access token and never a tenant-authority header.
- Tenant A cannot access Tenant B resources, including by guessed IDs.
- Disabled users and revoked sessions are rejected.
- Logout clears the client session and prevents subsequent protected API calls.
- Browser cookie flags, CSRF, redirect allowlist, and absence of browser token persistence are verified.
- Native secure storage, app-link handling, logout, and platform builds are verified on supported devices.

## Explicitly not implemented

The provider-neutral session ports, API transport adapters, and UI gates are implemented and unit-tested. This does not create a functional sign-in button, OAuth callback, token exchange, refresh mechanism, logout flow, BFF, provider configuration, or live identity-provider connection. Those require a provider decision and registered client applications.
