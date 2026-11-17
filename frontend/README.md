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

The Next.js and Flutter application shells and API transports are implemented. Both clients have provider-neutral session-reader interfaces that supply a short-lived access token to the existing transport. The Next.js client includes a reusable `SessionGate`; Flutter includes `AgentBoxSessionGate`. Both render protected content only when a session is present, complete, and valid beyond a 30-second expiry safety window. Both gates schedule a session re-read at that boundary, close protected UI while rechecking, and fail closed when the session is still invalid or the reader fails. When a reader is replaced during an asynchronous read, stale success and error results are ignored; only the latest reader may determine the visible state. Timers are cancelled when the gate is disposed or its session reader changes.

The Next.js workspace includes tested, provider-neutral BFF policy helpers for cookie attributes, exact-origin/Fetch-Metadata CSRF checks, upstream route/method allowlisting, safe query validation, request-body rules, and positive header forwarding. They are not wired to route handlers and do not create or persist sessions. These gates are presentation boundaries only. They do not sign users in, redirect to a provider, or replace backend authorization. The Next.js client also has a standalone safe return-target utility for future authentication integration; it is not connected to a sign-in or callback flow. Session readers may return a refreshed session only if their future provider adapter legitimately supports that behavior. No live OIDC provider is configured. There is no login/callback, token exchange, refresh, logout, Next.js BFF, or native secure-storage adapter yet. Do not treat the session interfaces or gates as a working login implementation.

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

The repository workflow `.github/workflows/backend-ci.yml` validates the Next.js console (TypeScript, session-state tests, and production build) and Flutter client (static analysis and widget/unit tests) independently. The pipeline is a code-quality gate, not evidence of live API integration or production deployment.

## Shared API transport

The backend is the authority for API schemas and authentication. The versioned route inventory under `contracts/api/` is tested against FastAPI's generated OpenAPI paths. CI exports the generated OpenAPI document as a build artifact. The Flutter and Next.js clients use bearer-token-injected transports. Their session ports do not persist or refresh credentials and never send a tenant-authority header. Both API clients expose a constructor/factory that accepts the provider-neutral session reader directly; invalid or near-expiry sessions are rejected before a protected request. CI runs session adapter, session-expiry, and fail-closed UI-state tests for both clients.
