# AgentBox tenant composite identity keys

This migration advances the tenant storage model from tenant-filtered global IDs to
tenant-scoped identities.

## Composite keys

- Agent versions: primary key `(tenant_id, agent_id, version)`.
- Evaluation profiles: primary key `(tenant_id, profile_id, version)`.
- Evaluation runs: foreign key `(tenant_id, profile_id, profile_version)` references
  the matching tenant-owned evaluation profile.
- Execution IDs remain globally generated opaque IDs. Idempotency keys are transformed
  into a tenant-bound digest before persistence.

Two tenants can now independently create the same logical agent ID/version and the same
evaluation profile ID/version without collision. A run cannot reference another tenant's
profile, even if its profile identifier and version match.

## Data migration

The startup migration rebuilds the affected SQLite tables while preserving row data and
legacy tenant ownership. Rows already assigned to `__legacy_unassigned__` remain
quarantined. The migration does not guess tenant ownership. Table rebuilds and data copies
are performed through SQLite schema/data operations; production rollout still requires
a verified backup, maintenance window, and tested restore procedure.

## Remaining controls

The composite constraints enforce storage-level identity boundaries; they do not by
themselves complete production multi-tenancy. Tenant provisioning/lifecycle, tenant-scoped
backup and restore, encryption/key management, operational access controls, migration
rollback drills, and live multi-tenant deployment tests remain required. AgentBox capability
execution remains disabled pending its separate execution-security gates.
