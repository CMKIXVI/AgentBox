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

## Current UI capabilities

The authenticated Next.js console and Flutter client now provide:

- A five-pillar overview aligned with the canonical AgentBox architecture.
- Agent Studio: register an immutable agent manifest version, list versions for a known agent ID, and inspect a selected version.
- Execution: submit tenant-scoped durable jobs with idempotency keys, refresh job state, inspect append-only lifecycle events, request cancellation, and retrieve existing synchronous execution records.
- Evaluation Explorer: create immutable evaluation profile versions, inspect profile history, submit externally measured case outputs for deterministic scoring, inspect gate results, and browse prior evaluation runs.
- Cognitive Runtime Explorer: create and inspect tenant-scoped cognitive runs, view the nine-stage append-only event timeline, and explicitly assemble minimized context snapshots from policy-eligible evidence.
- Experience, Learning & Fitness Explorer: record minimized execution/evaluation links, create and inspect source-linked proposed lessons, and select agents using repeated samples from an exact evaluation profile version.
- Parent–Candidate Experiment Explorer: create and inspect immutable comparisons that verify candidate lineage, exact agent versions, completed evaluation runs and pinned profile-version identity; the workload hash remains caller-asserted.
- Visible authentication/session state and explicit sign-out.
- Structured success/error feedback and JSON inspection without fabricated data.

Experience records are explicitly caller-asserted and unverified until a trusted execution attestation exists; fitness aggregates are prioritization signals only and cannot authorize promotion. Lessons remain proposed and immutable. Parent/candidate experiment comparisons likewise remain unverified and advisory: they do not execute a shared workload, independently attest workload identity, enforce hard promotion gates or change the active version. Cognitive lifecycle events are displayed read-only; event records cannot authorize or execute tools. Context assembly is an explicit backend operation and includes currently valid observed facts and human-validated entities by default. The screens use the existing API contracts only. The backend does not yet expose a tenant-scoped agent catalogue endpoint, so the UI does not pretend to provide a global agent list. Execution creation, evaluation, candidate promotion, workflow authoring, and approval inbox screens remain gated on their complete operational contracts and evidence.

## Local development

### Next.js console

```bash
cd frontend/nextjs/console
npm install
npm run dev
```

Configure server-side `AUTH_SECRET`, `AGENTBOX_OIDC_CLIENT_ISSUER`, `AGENTBOX_OIDC_WEB_CLIENT_ID`, `AGENTBOX_OIDC_WEB_CLIENT_SECRET`, and `AGENTBOX_API_BASE_URL`. Register the Auth.js callback `/api/auth/callback/agentbox-oidc`.

### Flutter client

```bash
cd frontend/flutter
flutter pub get
flutter run \
  --dart-define=AGENTBOX_API_BASE_URL=https://api.example.com \
  --dart-define=AGENTBOX_OIDC_ISSUER=https://identity.example.com/realms/agentbox \
  --dart-define=AGENTBOX_OIDC_MOBILE_CLIENT_ID=agentbox-mobile \
  --dart-define=AGENTBOX_OIDC_MOBILE_REDIRECT_URI=com.example.agentbox:/oauth2redirect
```

Register the native redirect URI with the identity provider and the corresponding Android/iOS URL scheme or app link. Never pass a client secret to Flutter.

See [the master architecture](../ARCHITECTURE.md) for client responsibilities, security boundaries, and delivery sequence.

## Shared API transport and security

The backend is the authority for API schemas and authentication. The versioned route inventory under `contracts/api/` is tested against FastAPI's generated OpenAPI paths. Both clients use bearer-token-injected transports; neither sends a tenant-authority header. Next.js uses an Auth.js server-managed session, protected HttpOnly cookie, and same-origin `/api/agentbox/*` proxy. Flutter uses AppAuth Authorization Code + PKCE and platform-secure token storage. Provider selection remains a deployment decision.

The OIDC tenant claim must be populated by trusted tenant provisioning. Client login alone does not prove API authorization or tenant membership. Backend authorization and resource checks remain decisive.

## CI and release gates

The repository workflow validates the Next.js console (TypeScript and production build) and Flutter client (static analysis and widget tests) independently. A green pipeline is code-quality evidence only. It does not prove live issuer/JWKS validation, native redirect configuration, client-to-API end-to-end operation, accessibility review on devices, deployment security, or production operations.

The current screens are an API-connected operational foundation, not a claim that every AgentBox lifecycle stage is implemented. Missing backend capabilities must be completed before corresponding UI actions are enabled.
