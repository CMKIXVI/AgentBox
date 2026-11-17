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

The versioned contract is in `schemas/tenant-v1.schema.json`. The registry uses a separate SQLite database path supplied by its host; it is not yet wired into the API authentication dependency or protected routes. Consequently, this change establishes the authority and lifecycle primitives but does not yet block suspended tenants at the HTTP boundary. That enforcement is the next integration gate.

No self-service tenant creation, caller-selected tenant switching, tenant deletion, backup/restore, encryption, or key management is implemented. Production deployment still requires an administrator bootstrap path, protected database permissions, verified backup/restore, encryption/key management, operational monitoring, and live isolation tests.
