# OIDC deployment configuration checklist (example only)

This is a deployment worksheet, not a working configuration file. Replace every placeholder with values issued by the selected identity provider. Do not commit secrets.

| Setting | Example placeholder | Owner |
|---|---|---|
| Provider | <keycloak-or-entra-or-auth0> | Platform administrator |
| Issuer | https://identity.example.invalid/realms/agentbox | Identity provider |
| Discovery URL | <issuer>/.well-known/openid-configuration | Identity provider |
| Web client ID | <agentbox-web-public-client-id> | Identity provider |
| Native client ID | <agentbox-mobile-public-client-id> | Identity provider |
| API audience | agentbox-api | Identity provider + backend |
| Web redirect URI | https://console.example.invalid/auth/callback | Web deployment |
| Mobile redirect URI | <registered-app-link-or-custom-scheme> | Mobile deployment |
| Post-logout URI | https://console.example.invalid/ | Web deployment |
| Tenant claim | tenant_id | Identity provider + backend |
| Signing algorithms | RS256 (confirm provider metadata) | Identity provider |
| Web session | HttpOnly + Secure + SameSite cookie | Web BFF |
| Native credential store | Platform-protected secure storage | Native OIDC SDK |

Backend verifier environment variables already consumed by AgentBox:
- AGENTBOX_OIDC_ISSUER
- AGENTBOX_OIDC_AUDIENCE
- AGENTBOX_OIDC_JWKS_URI
- AGENTBOX_OIDC_TENANT_CLAIM
- Optional: AGENTBOX_OIDC_ALGORITHMS, AGENTBOX_OIDC_LEEWAY_SECONDS, AGENTBOX_OIDC_JWKS_TIMEOUT_SECONDS

The web and native public client registrations are separate from the backend verifier settings. No client secret is required or permitted in Flutter or browser code.


## Client registration contract

The separate provider-neutral client registration artifact is defined by `schemas/oidc-client-registration-v1.schema.json` and documented in [the OIDC client registration contract](oidc-client-registration-contract.md). It validates separate web BFF and native public-client registrations, exact redirect allowlists, Authorization Code Flow, and PKCE S256. It stores only server-side secret references, never secret values. It does not register clients with a provider or enable login.
