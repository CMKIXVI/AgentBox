# AgentBox tenant data isolation

This change makes tenant ownership a persisted property of AgentBox's agent versions,
executions, evaluation profiles and evaluation runs. API handlers obtain the tenant ID only
from the verified authentication principal and pass it into every corresponding storage
operation. Request bodies and caller-supplied tenant headers cannot select the storage tenant.

## Storage behavior

- Agent versions persist `tenant_id`; get/list/create queries include the tenant predicate.
- Executions persist `tenant_id`; reads are tenant-filtered and idempotency keys are
  transformed using a tenant-scoped SHA-256 key before persistence.
- Evaluation profiles and runs persist `tenant_id`; profile lookup/list, run lookup and
  agent-run listing include the tenant predicate.
- Tenant indexes support the principal-scoped lookup paths.
- Existing databases are migrated in place. Rows that predate tenant ownership receive the
  reserved owner `__legacy_unassigned__`; they are not visible to authenticated tenant IDs.
  They require an explicit, reviewed administrative reassignment before normal tenant access.

## Identifier namespace limitation

The initial SQLite tables retain their original globally unique primary keys for agent
(agent_id, version) and evaluation profile (profile_id, version). Therefore different tenants
must currently use globally distinct agent and profile IDs. This is a functional namespace
restriction, not a cross-tenant read permission. A later schema migration can change these to
composite tenant-scoped keys after a controlled data migration.

## Verification scope and remaining gates

Tests cover tenant-mismatched reads, tenant-scoped execution idempotency, and migration
quarantine for pre-tenant rows. These are local SQLite integration tests, not a production
database deployment test. The API still requires verified OIDC authentication and explicit
authorization policies. This work does not add organization provisioning, tenant lifecycle
administration, backup/restore tenant controls, database encryption, or production-grade
migration rollback. Do not describe the whole service as production multi-tenant ready until
those controls and cross-tenant end-to-end tests are completed.
