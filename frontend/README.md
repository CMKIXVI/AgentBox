# AgentBox frontend workspace

AgentBox has two first-class clients backed by one FastAPI platform:

- `nextjs/console`: browser-first Agent Studio, engineering, administration, and observability workspace.
- `flutter/`: mobile-first operational client, with desktop targets added when justified.

## Non-negotiable boundaries

- Both clients use the same AgentBox backend and authoritative OpenAPI/JSON Schema contracts.
- Identity, active tenant, permissions, policy, and resource ownership are enforced by the backend.
- Do not duplicate domain logic, agent execution, evaluation, or promotion decisions in either frontend.
- Do not store secrets or long-lived credentials in source code, bundles, local storage, or application preferences.
- Do not invent API routes or manually drift client models from backend schemas.
- UI may hide unavailable actions, but server authorization remains decisive.

## Current implementation status

The Next.js and Flutter application shells, bearer-token API transports, and versioned route inventory are implemented on the current stacked feature branches. Screens remain preview/static: client login/session flows and live end-to-end API integration are not yet enabled. The backend validates OIDC access tokens and derives tenant context from a configured verified claim.

## Local development

### Next.js console

```bash
cd frontend/nextjs/console
npm install
npm run dev
```

### Flutter client

```bash
cd frontend/flutter
flutter pub get
flutter run
```

See [the master architecture](../ARCHITECTURE.md) for client responsibilities, security boundaries, and delivery sequence.

## Continuous integration

The repository workflow `.github/workflows/backend-ci.yml` validates the Next.js console (TypeScript and production build) and Flutter client (static analysis and widget tests) independently. The pipeline is a code-quality gate, not evidence of live API integration or production deployment.

## Shared API transport

The backend is the authority for API schemas and authentication. The versioned route inventory under `contracts/api/` is tested against FastAPI's generated OpenAPI paths. CI exports the generated OpenAPI document as a build artifact. The Flutter and Next.js clients use bearer-token-injected transports; an OIDC session integration must supply short-lived access tokens. Neither client sends a tenant-authority header or persists credentials in the transport layer. The provider-neutral implementation contract is documented in [OIDC client integration](../docs/security/oidc-client-integration-contract.md). Web login is planned as a Next.js BFF session with Secure/HttpOnly cookies; Flutter login uses system-browser Authorization Code + PKCE and platform-protected storage. Provider selection remains a deployment decision.


## OIDC client configuration

Authentication is provider-neutral. Configure a conformant OIDC provider per deployment; no provider URL, client identifier, secret, or callback is committed to the repository.

### Next.js web console

Set these server-side environment variables in the deployment secret/configuration store:

- `AUTH_SECRET`: high-entropy Auth.js session encryption secret.
- `AGENTBOX_OIDC_CLIENT_ISSUER`: exact OIDC issuer URL.
- `AGENTBOX_OIDC_WEB_CLIENT_ID`: confidential web client identifier.
- `AGENTBOX_OIDC_WEB_CLIENT_SECRET`: confidential web client secret.
- `AGENTBOX_API_BASE_URL`: AgentBox FastAPI base URL.

Register the Auth.js callback URL `/api/auth/callback/agentbox-oidc` and the exact post-logout/return URLs used by the deployment. The web client uses Authorization Code + PKCE, state and nonce checks. Auth.js keeps the session in its protected HttpOnly cookie; access and refresh tokens are never returned in the browser session object. Browser API calls should use the same-origin `/api/agentbox/*` proxy, which attaches the server-held bearer token.

### Flutter mobile client

Supply build-time configuration using Dart defines:

```bash
flutter run \
  --dart-define=AGENTBOX_OIDC_ISSUER=https://identity.example.com/realms/agentbox \
  --dart-define=AGENTBOX_OIDC_MOBILE_CLIENT_ID=agentbox-mobile \
  --dart-define=AGENTBOX_OIDC_MOBILE_REDIRECT_URI=com.example.agentbox:/oauth2redirect
```

Register the native redirect URI with the provider and the matching Android/iOS app-link or URL-scheme configuration in the native application projects. Flutter uses the system browser and AppAuth PKCE flow; access and refresh tokens are stored with platform-protected secure storage. Never pass a client secret to the mobile application.

### Backend alignment

Configure the FastAPI OIDC issuer, API audience, JWKS URI and trusted tenant claim independently. The issuer must match the provider used by the clients, while the API audience must identify the AgentBox API. The tenant claim must be populated by trusted tenant provisioning. Client login alone does not prove API authorization or tenant membership.

### Current integration boundary

The code now includes a configurable Next.js OIDC sign-in/session flow, server-side token refresh and same-origin API proxy, plus a Flutter AppAuth/secure-storage token lifecycle. Provider registration, native platform redirect configuration, live issuer/JWKS validation and deployed client-to-API end-to-end tests remain environment-specific release gates. CI validates code, not a real identity-provider deployment.
