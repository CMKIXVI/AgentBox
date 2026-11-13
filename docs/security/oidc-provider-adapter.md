# Concrete OIDC provider adapter

**Status:** A concrete HTTP adapter is implemented for OIDC discovery, authorization-code exchange, PKCE verifier submission, and cryptographic ID-token validation. It is not yet wired into AgentBox HTTP routes or a production secret manager.

## Provider discovery

The adapter loads `{issuer}/.well-known/openid-configuration` from the configured issuer. It requires an exact issuer match and HTTPS authorization, token, and JWKS endpoints. It rejects redirects, oversized/non-object JSON documents, providers without authorization-code support, and providers that do not advertise PKCE S256.

Metadata is cached for the lifetime of the adapter. JWKS is fetched for each ID-token verification so key rotation is observed without relying on a stale in-process cache. JWKS responses are bounded to 1 MiB and 100 keys.

## Authorization-code exchange

The adapter submits the one-time code, exact registered redirect URI, client ID, and PKCE verifier to the discovered token endpoint. Public native clients use `token_endpoint_auth_method=none`. Confidential web clients use `private_key_jwt`; a deployment-provided key resolver returns the signing key and optional `kid`. Client assertions use RS256 and a 60-second lifetime.

The adapter deliberately does not implement `client_secret_basic`. Registrations using that method fail closed until a dedicated secret resolver and tests are added.

## ID-token validation

Only RS256, PS256, and ES256 are accepted. HMAC and `none` algorithms are rejected. The adapter selects exactly one signing JWK by `kid` (or a sole compatible key when `kid` is absent), verifies the signature, and validates issuer, audience, expiry, issued-at, and subject using PyJWT. The authorization orchestration subsequently validates nonce, tenant claim, client binding, and `azp` for multi-audience tokens.

## Network and secret boundaries

- HTTPX redirects are disabled; metadata, token, and JWKS endpoints must use HTTPS.
- HTTP timeouts are bounded; response documents and ID-token size are capped.
- Provider tokens and client assertions are never logged or persisted by this adapter.
- The HTTP client and private-key resolver are injectable for isolated tests.
- No real provider credentials or live identity-provider requests are used in CI.

## Remaining before production login

- Wire this adapter to trusted deployment configuration and the existing authorization flow.
- Implement production-grade key resolver/secret manager integration and rotation.
- Add HTTP start/callback routes, browser CSRF and secure-cookie/session issuance.
- Add Flutter callback handling and platform secure storage.
- Add provider sandbox/live end-to-end tests, operational telemetry, rate limiting, and deployment hardening.

A verified OIDC identity is not an AgentBox application session.