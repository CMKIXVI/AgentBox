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
