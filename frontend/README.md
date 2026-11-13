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

This workspace is the initial application foundation. The Next.js and Flutter shells are not yet authenticated or connected to live AgentBox APIs. Their current screens are intentionally static until the API contract inventory and OIDC client flows are implemented.

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
