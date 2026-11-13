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

The Next.js and Flutter application shells and API transports are implemented. Both clients have provider-neutral session-reader interfaces that supply a short-lived access token to the existing transport. The Next.js server-side `requireAgentBoxSession` guard and Flutter `AgentBoxProtectedSessionGate` reject missing, expired, malformed, or unreadable sessions before protected content is rendered.

These guards are reusable integration points, not live login. No OIDC provider is configured. There is no login/callback, token exchange, refresh, logout, Next.js BFF, or native secure-storage adapter yet. The current home screens remain explicitly marked preview shells and are not being represented as authenticated workspaces. Do not wire protected routes to a placeholder or browser-local session reader.

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

See [the master architecture](../ARCHITECTURE.md) and [OIDC session contract](../docs/security/oidc-client-session-contract.md) for client responsibilities, security boundaries, and provider integration requirements.

## Continuous integration

The repository workflow `.github/workflows/backend-ci.yml` validates the Next.js console (TypeScript, Node session/guard tests, and production build) and Flutter client (static analysis and widget/unit tests) independently. The pipeline is a code-quality gate, not evidence of live API integration or production deployment.

## Shared API transport

The backend is the authority for API schemas and authentication. The versioned route inventory under `contracts/api/` is tested against FastAPI's generated OpenAPI paths. CI exports the generated OpenAPI document as a build artifact. The Flutter and Next.js clients use bearer-token-injected transports. Their session ports do not persist or refresh credentials and never send a tenant-authority header. Both API clients accept the provider-neutral session reader directly; invalid or near-expiry sessions are rejected before a protected request. CI runs session adapter and protected-session guard tests for both clients.
