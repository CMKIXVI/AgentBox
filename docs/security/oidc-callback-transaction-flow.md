# OIDC Authorization Code + PKCE flow

**Status:** Provider-neutral login orchestration and atomic state-hash consumption are implemented. No concrete identity-provider adapter, HTTP callback route, or application session issuance is configured.

## Start

`OidcAuthorizationFlow.start` validates the client registration and exact client-specific redirect URI, generates independent opaque state and nonce values plus a high-entropy PKCE verifier, stores the verifier through a secret-store port, and persists only SHA-256 hashes of state and nonce with the verifier reference. It returns the authorization URL and expiry. The authorization request uses `response_type=code`, `openid` scope and PKCE S256.

The authorization endpoint and issuer are trusted deployment configuration and must be HTTPS. The authorization endpoint must not contain a pre-existing query or fragment. Never accept either value from the browser.

## Callback

The callback is resolved by SHA-256 hash of the supplied state. The repository atomically consumes the unique matching state hash and rejects expiry/replay. It then binds the transaction to the original client ID and exact redirect URI, retrieves the PKCE verifier, and calls an injected authorization-code exchanger.

The exchanger contract requires a maintained OIDC implementation to exchange the code and validate the ID-token signature using trusted JWKS, an asymmetric algorithm allowlist, issuer, audience, expiry, issued-at and key rotation. The orchestration independently checks issuer, client audience (including `azp` when multiple audiences are present), time bounds, nonce hash, subject and configured tenant claim. The PKCE verifier is deleted from the secret store after the one-time callback attempt.

## Storage

PostgreSQL and SQLite enforce unique state hashes. PostgreSQL uses a unique index and conditional `DELETE ... RETURNING`; SQLite uses `BEGIN IMMEDIATE`. The SQLite adapter remains single-host only. PostgreSQL is the shared multi-instance adapter.

## Security boundaries still pending

- Concrete provider discovery/metadata and authorization-code exchanger implementation.
- HTTP start/callback routes and browser CSRF/cookie binding.
- Session issuance, secure HttpOnly cookie/BFF for Next.js.
- Native Flutter authorization callback and platform secure storage.
- Live end-to-end tests against a real OIDC provider.
- Operational secret-store integration, PostgreSQL connection pooling and deployment migrations.

A verified identity returned by this flow is not itself an application session. Tenant and authorization authority remain server-side.
