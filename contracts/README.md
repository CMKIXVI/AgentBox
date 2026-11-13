# AgentBox API contracts

## Authority

The running FastAPI application is the source of truth for request/response schemas. Its generated OpenAPI document is exposed at `/openapi.json`. Do not hand-edit a second full OpenAPI specification or duplicate Pydantic models.

`api/agentbox-route-inventory-v1.json` is a deliberately small, versioned route and authentication inventory. It is used to detect route drift and document which operations require a verified OIDC bearer principal. It is not a replacement for the generated OpenAPI document.

## Authentication and tenancy

- Protected operations require an OIDC JWT in `Authorization: Bearer <access-token>`.
- AgentBox validates issuer, audience, signature, time claims, and the configured tenant claim.
- The backend derives the active tenant from the verified principal and checks tenant lifecycle and resource authorization.
- Frontends must not send `X-Tenant-ID` or treat a user-selected tenant value as authority.
- Frontend API transports accept a short-lived token through an injected provider. They do not store credentials, refresh tokens, or client secrets.
- OIDC login, callback, logout, token refresh, and session lifecycle are provider/session integration work, not part of the transport layer.

## OpenAPI export

From `backend/`:

```bash
python scripts/export_openapi.py --output ../contracts/openapi/agentbox-openapi.json
```

The generated file is an export of the actual FastAPI application. Regenerate it when API models or routes change; review the diff rather than editing it manually.

## Client generation

The current TypeScript and Dart clients are thin, typed transports with a small set of typed convenience methods. They deliberately do not claim to be fully generated SDKs. The next integration stage can generate full models/clients from the exported OpenAPI document and replace manual model fragments incrementally.
