# AgentBox tenant registry and lifecycle

## Authority boundary

The registry is server-owned persistent state. Tenant IDs from verified identity claims are references to registry records, not permission to create or activate tenants. Provisioning and lifecycle operations must be exposed only through a separately authenticated and authorized system-administrator workflow. The registry methods accept an actor identifier for audit attribution but do not authenticate that actor; callers must enforce that boundary.

New tenants begin in `pending`. Only explicit lifecycle transitions can activate or suspend them. A tenant is accessible only when its persisted status is `active`. Decommissioning is terminal; tenant records are never deleted by this interface.

## Lifecycle

- `pending -> active | suspended | decommissioned`
- `active -> suspended | decommissioned`
- `suspended -> active | decommissioned`
- `decommissioned ->` no further transition

Each create/transition operation and its audit event commit in one SQLite transaction. Audit rows are protected by update/delete triggers. Metadata is bounded scalar JSON; credentials and secrets do not belong in tenant metadata.

## Persistence and operational limits

The versioned contract is in `schemas/tenant-v1.schema.json`. The registry shares the AgentBox API SQLite database and is checked by a FastAPI dependency after OIDC verification. Every protected agent, execution, and evaluation route now requires a tenant record in the active state. Missing, pending, suspended, and decommissioned tenants are denied before authorization-policy evaluation. Tenant state is read on each request, so suspension takes effect on the next request. Health and side-effect-free schema-validation endpoints remain public.

No self-service tenant creation, caller-selected tenant switching, tenant deletion, backup/restore, encryption, or key management is implemented. Production deployment still requires an administrator bootstrap path, protected database permissions, verified backup/restore, encryption/key management, operational monitoring, and live isolation tests.


## HTTP enforcement integration

The protected-route dependency chains from verified OIDC authentication into a server-side registry lookup. The signed tenant claim is treated only as the tenant key to look up; it cannot create, activate, or switch a tenant. No registry record means deny. Any status other than active means deny. Existing capability/action/resource policies still run after the tenant lifecycle check, so an active tenant does not receive implicit permissions.

The test access helper provisions a test tenant explicitly. Tests cover missing, pending, suspended and decommissioned tenants, active tenant authorization, policy enforcement after lifecycle validation, and suspension taking effect without restarting the API. Public validation endpoints remain side-effect-free.

The registry is not exposed through public provisioning endpoints. A trusted bootstrap/operator process must create and activate tenants using controlled access to the registry. This PR does not yet provide an operator CLI or administrator API.
