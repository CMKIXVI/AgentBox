# AgentBox encrypted tenant backup and restore

## Security model

AgentBox creates tenant-scoped logical backups encrypted with **AES-256-GCM**. The backup contains only records whose `tenant_id` matches the requested tenant:

- Agent versions and immutable manifests
- Execution records and results
- Evaluation profiles and evaluation runs
- Tenant audit events
- Enterprise Context Engine entities, relationship versions, evidence references and append-only context events

The envelope exposes the format/version, algorithm, key identifier, and tenant ID. Record contents, metadata, execution results, manifests, and audit actor labels are encrypted. The tenant's lifecycle record is included inside the authenticated payload for provenance, but restore never overwrites the target tenant's lifecycle state, display name, or metadata.

The envelope uses a random 96-bit nonce and authenticated additional data binding the format, version, algorithm, key ID, and tenant ID. AES-GCM authentication failure, a wrong key, a modified envelope, or a cross-tenant payload is rejected. A SHA-256 digest inside the encrypted payload provides an additional canonical-content integrity check; it is not a replacement for AEAD authentication.

## Key management boundary

AgentBox does **not** generate, persist, rotate, escrow, or retrieve encryption keys from a KMS. The deployment must provision a cryptographically random 32-byte key through its secret manager and inject it into the process environment:

- `AGENTBOX_BACKUP_KEY_ID`: active key identifier
- `AGENTBOX_BACKUP_KEY_<NORMALIZED_KEY_ID>`: standard-base64 encoding of exactly 32 key bytes

For key ID `BACKUP_2026_01`, the key variable is `AGENTBOX_BACKUP_KEY_BACKUP_2026_01`. The key ID is limited to uppercase letters, digits, and underscore so environment-variable mapping is unambiguous. Keys are never printed, included in the backup, or written to the database.

For rotation, inject both the new active key and all historical decryption keys still needed for retained backups. Change `AGENTBOX_BACKUP_KEY_ID` to the new ID only after the new key is available. Do not remove an old key until the retention period for backups encrypted with it has ended or those backups have been re-encrypted under a new key. Key custody, access approval, revocation, escrow, and recovery remain the responsibility of the external secret-management/KMS system.

Never put raw key bytes in command arguments, source control, tenant metadata, or logs. Environment variables are a deployment bridge, not a full KMS integration; production should inject them from a protected secret manager and restrict process inspection and host access.

## Commands

Install the backend package and run the local operator CLI on the AgentBox host:

```bash
cd backend
pip install -e .

# Create a tenant backup; destination must not already exist.
agentbox-tenant backup --tenant-id customer-001 --output /secure/backups/customer-001-2026-11.agb

# Restore into an already provisioned tenant with the same ID.
agentbox-tenant restore --tenant-id customer-001 --input /secure/backups/customer-001-2026-11.agb
```

Both operations fail closed if the key ID/key is absent or malformed. Backup creation refuses to overwrite an existing destination and writes a private file with mode `0600`. Symbolic-link paths are rejected. Restore accepts regular files up to 512 MiB.

## Restore semantics

Restore requires the destination AgentBox database to be initialized and the same tenant ID to have been provisioned first. It does not create tenants, activate tenants, or change lifecycle state. The target tenant's current status remains authoritative, including if it is suspended or decommissioned.

Pre-ECE v1 backups containing the original five tenant tables remain restorable; absent ECE tables are treated as empty. New backups include all ECE tables. Restore runs in one SQLite transaction. Existing identical records are skipped, making repeated restores idempotent. If a primary-key identity already exists with different content, restore raises a conflict and rolls back all rows inserted by that restore. Evaluation runs are restored only after their tenant-scoped evaluation profiles, preserving the composite foreign-key constraint. Audit event timestamps and actor labels are preserved; SQLite audit sequence IDs are regenerated when events are imported. Existing audit rows are never updated or deleted.

The encrypted bundle is a logical tenant data export, not a complete system disaster-recovery image. It does not include OIDC configuration, authorization policy files, provider credentials, external secrets, application configuration, global schema files, or data not keyed by tenant ID. Use a separately tested whole-system backup for infrastructure recovery.

## Operational verification and limits

- Keep backup files outside the application repository and database directory; store them in access-controlled, encrypted-at-rest backup storage.
- Test restore regularly into an isolated database and verify application-level reads, tenant boundaries, and audit history.
- Preserve old decryption keys for the full backup retention period.
- Monitor backup success/failure and verify off-host copies independently.
- This feature does not provide a KMS connector, automatic key rotation, scheduled backups, retention deletion, immutable object storage, point-in-time recovery, or a full disaster-recovery orchestrator.
- The implementation is a tenant-scoped logical backup/restore foundation; production readiness still depends on operational key custody, tested off-host storage, recovery drills, monitoring, and live isolation validation.
