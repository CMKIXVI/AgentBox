# AgentBox PostgreSQL catalog snapshot ingestion

## Scope

This batch connects the read-only PostgreSQL catalog adapter contract to the native Enterprise Context Engine (ECE). It accepts a metadata-only snapshot produced by the adapter, maps it into tenant-scoped ECE entities and relationships, and attaches unverified provenance evidence.

## Flow

1. A separately provisioned read-only PostgreSQL adapter performs catalog-only inspection.
2. The adapter returns a versioned snapshot with a SHA-256 content hash and explicit zero application rows read / zero source writes.
3. An authenticated AgentBox principal with the exact `enterprise.discovery / discovery.snapshot.ingest / tenant-context` grant submits the snapshot.
4. AgentBox verifies the snapshot contract, recomputes the hash, checks the metadata-only assertions and enforces payload/count bounds.
5. Schema, relation, column, index and constraint objects are mapped to immutable tenant-owned ECE entity versions.
6. Schema containment, relation-column, index, constraint and in-snapshot foreign-key dependencies become typed ECE relationships.
7. Every discovered entity receives an evidence record containing the snapshot hash and a credential-free source locator.
8. Repeated ingestion is idempotent for identical records. Changed entity metadata creates a new immutable entity version; relationship identity incorporates endpoint versions and edge metadata.

## Epistemic and provenance boundary

The HTTP ingestion endpoint receives a caller-supplied snapshot; it does not independently prove which PostgreSQL server produced it. Therefore imported entities and relationships are marked `inferred`, not `human_validated` or verified observed facts. Evidence remains `unverified`. A SHA-256 digest detects content alteration relative to the supplied digest; it is not a signature or proof of source authenticity.

The endpoint accepts no DSN, password, token or private key and makes no external database connection. The source locator must use the `postgresql-catalog://` scheme and cannot contain credentials, query parameters or fragments.

## Limits

- Snapshot JSON: 8 MiB.
- Schemas: 100.
- Relations: 2,000.
- Columns: 20,000.
- Indexes and constraints: 10,000 each.
- Total ingested entities: 5,000.
- Total ingested relationships: 10,000.

The existing ECE service enforces its own per-record metadata limits and tenant/version foreign keys. Records are written through the existing SQLite context service and are covered by its tenant backup inventory.

## API

`POST /v1/enterprise-discovery/postgresql/snapshots/ingest`

Requires OIDC authentication, an active tenant and the exact policy grant:

- Capability: `enterprise.discovery`
- Action: `discovery.snapshot.ingest`
- Resource: `tenant-context`

The response reports created/reused entity, relationship and evidence counts. This is a synchronous ingestion endpoint, not a durable background discovery job.

## Not yet production end-to-end

The current adapter uses an injected DB-API connection factory; AgentBox does not yet register a live connector or resolve secrets. This batch does not include operator connector provisioning, secret-provider integration, live PostgreSQL connection tests, source identity attestation, durable discovery scheduling or source-system event ingestion. Do not expose a live connection until those controls are implemented.
