# OIDC redirect and callback transaction contract

**Status:** Provider-neutral security contract only. This is not a callback endpoint or login implementation.

## Exact redirect matching

The backend helper checks the requested URI against the allowlist belonging to exactly one registered client ID. It uses literal string equality. It does not lowercase hosts, remove default ports, normalize paths, decode escapes, or apply prefix, suffix, wildcard, or substring matching. Redirect and post-logout allowlists are separate.

Validate the registration artifact before calling this helper. A missing or duplicate client ID fails closed. A callback must never select a redirect URI from user-controlled state without this check.

## Callback transaction record

The versioned schema defines the minimal persisted record. Store only SHA-256 hashes of the opaque state and OIDC nonce, plus a secret-manager reference for the PKCE verifier. Do not store raw state, nonce, verifier, authorization code, access token, refresh token, or client secret in this record or logs.

Transactions must expire within 10 minutes. Compare the callback's state hash in constant time in the provider adapter, verify the nonce against the ID token, and bind the transaction to its original client ID and exact redirect URI.

## Atomic single-use requirement

The transaction-store protocol is a persistence port. Its implementation must atomically check existence, expiry and unused status while marking the transaction consumed. This must be safe across multiple backend processes and instances. A read-then-delete sequence is not acceptable. Replays and expired transactions must return no transaction.

The SQLite development adapter is documented separately. It uses an immediate write transaction for atomic single-host consumption; it is not a multi-host replay store.

## Trust boundaries

- The callback adapter must not accept tenant identity from query parameters, form fields, redirect URIs, or client-supplied transaction data.
- FastAPI continues to derive tenant identity and enforce authorization from its verified access token.
- A successful transaction consume is not proof that an authorization code or ID token is valid.
- A maintained OIDC SDK must perform authorization-code exchange, PKCE verification, issuer/audience/signature/time validation, nonce verification, and key rotation handling.
- No provider, callback route, token exchange, session issuance, BFF cookie, or native secure-storage adapter is configured by this contract.
