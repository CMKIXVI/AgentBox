# OIDC application sessions

**Status:** Opaque session issuance, validation, CSRF-token verification, revocation, and SQLite/PostgreSQL persistence are implemented. HTTP login routes and cookie/session middleware are not yet wired.

## Session issuance

Only a `VerifiedOidcIdentity` returned by the authorization flow can be exchanged for an application session. The service generates independent high-entropy session and CSRF tokens. It persists only SHA-256 hashes of those values, along with the subject, tenant, issuer, client, and bounded timestamps.

The raw session and CSRF credentials are returned once to the caller. They must never be logged or written to the database. The default session lifetime is eight hours; the maximum is twelve hours.

## Validation and revocation

A presented session token is hashed and looked up as a live, unexpired, non-revoked session. CSRF validation hashes the submitted CSRF token and compares it to the stored hash using constant-time comparison. Revocation is an atomic conditional update, so concurrent logout requests have one winner. Expired and revoked rows can be removed by the store's purge operation.

## Persistence

- SQLite is a durable single-host development adapter.
- PostgreSQL is the shared multi-instance adapter.
- Both persist hashes, enforce expiry, and atomically revoke.
- The PostgreSQL migration is `backend/migrations/0002_oidc_application_sessions.sql`.

## Remaining before production login

- Wire session issuance to the HTTP OIDC callback.
- Set secure HttpOnly session cookies and a readable CSRF cookie with appropriate SameSite policy.
- Require CSRF header validation on cookie-authenticated state-changing requests.
- Add session-reading middleware and logout endpoints.
- Add production secret-store integration for the OIDC client signing key.
- Add Flutter secure storage and native session lifecycle.
- Add browser/mobile end-to-end tests and deployment-specific cookie/origin configuration.

This session service is not a complete web authentication flow until the HTTP routes, cookie transport, CSRF enforcement, and client integration are connected.
