# Provider-neutral OIDC client registration contract

**Status:** Versioned validation contract only. No provider registration or interactive login is configured.

## Purpose

The schema at `schemas/oidc-client-registration-v1.schema.json` describes the web and native public-client registrations AgentBox will need after an identity provider is selected. The backend validator rejects unsafe redirect metadata before deployment configuration is accepted.

This artifact is separate from `authentication-config-v1.schema.json`, which configures the existing FastAPI JWT verifier (issuer, audience, JWKS URI, tenant claim, algorithms, and bounded timeouts).

## Security rules

- Authorization Code Flow only (`response_type=code`).
- PKCE S256 is mandatory for both web and native clients.
- Web is represented as a confidential client used only by a future server-side BFF; it must refer to a server-side secret using a secret-manager reference, never a literal secret.
- Native is a public client; it cannot contain a client secret or use client authentication.
- Web redirect and post-logout URIs must use HTTPS.
- Native redirect URIs may use HTTPS app links or a registered custom application scheme.
- Wildcards, URI fragments, embedded user information, dangerous schemes, and ambiguous custom-scheme URIs are rejected.
- Client IDs must be unique within one registration artifact.
- Redirect URI matching at runtime must be exact against the registered allowlist; prefix, wildcard, suffix, and substring matching are prohibited.
- The provider SDK/BFF must still validate state, nonce, issuer, audience, signature, and token time claims. This schema does not perform those checks.
- Secrets are resolved only by the server-side deployment secret manager. The registration artifact contains references, not secret values.

## Validation entry point

Use `backend.app.oidc_client_registration.validate_oidc_client_registration` to validate an artifact. It returns a stable list of path/message errors. It does not write provider settings, register clients, exchange tokens, or enable login.

## Still required for live login

A provider must be selected and its actual issuer/discovery metadata, client IDs, API audience, redirect URIs, tenant-claim mapping, logout behavior, and secret-manager references supplied. Then implement and test a maintained provider SDK integration, Next.js BFF session cookies and CSRF protections, and Flutter platform-secure token storage. FastAPI remains the sole JWT verification, tenant, and authorization authority.
