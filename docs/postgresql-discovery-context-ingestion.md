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
8. An optional Ed25519 connector attestation binds the tenant, source locator, snapshot hash, discovery timestamp, key ID and signing timestamp. AgentBox verifies it against the active public key in the tenant-scoped connector registry before ingestion.
9. Signed evidence is stored separately from legacy unsigned evidence, with the verified key ID and snapshot digest in its immutable metadata. It remains unverified for human/context acceptance; cryptographic source attestation does not itself make a fact human-validated.
10. Repeated ingestion is idempotent for identical records. Changed entity metadata creates a new immutable entity version; relationship identity incorporates endpoint versions and edge metadata.

## Epistemic and provenance boundary

Unsigned ingestion remains supported for compatibility and does not prove which PostgreSQL server produced a snapshot. With an attestation, AgentBox verifies an Ed25519 signature using an active public key provisioned through the authorized tenant-scoped connector registry; the signed message binds the authenticated tenant, exact credential-free source locator, snapshot hash, discovery timestamp, key ID and signed_at. Unknown keys, malformed signatures, tampering, tenant/source replay and stale signatures fail closed. Attestations expire after 15 minutes (with 60 seconds of future clock skew). The private signing key stays in the connector environment.

Cryptographic attestation proves possession of a trusted connector key and integrity of the signed snapshot; it does not prove that the connector's database role was correctly provisioned or that the source database itself was truthful. Imported entities and relationships therefore remain `inferred`; all evidence remains `unverified` until the separate review process accepts it.

The AgentBox API accepts no DSN, password, token or private key and makes no external database connection. The source locator must use the `postgresql-catalog://` scheme and cannot contain credentials, query parameters or fragments.

### Source-side catalog connector

`app.postgresql_catalog_connector` supplies a source-side collector that can run inside the database network. It uses an injected DB-API connection factory, starts an explicit read-only transaction, applies a bounded statement timeout, and reads only PostgreSQL system catalogs for an explicit schema allowlist. It never selects application table rows and always rolls back/closes the connection. The resulting snapshot uses the same canonical hash and metadata-only contract as the ingestion API.

The connector's signing boundary is the `SigningKeyProvider` protocol. A deployment supplies an implementation backed by its KMS, HSM or OS keyring; AgentBox's connector package never exports or persists private key material. `PostgreSQLCatalogAttestor` creates the exact Ed25519 attestation accepted by the API. `PostgreSQLCatalogConnector.discover()` returns the request envelope containing connector ID, source locator, snapshot and attestation. The external connector must use the tenant ID and source locator bound during registration, then POST that envelope to the snapshot-ingestion endpoint.

The optional `postgresql` dependency group installs Psycopg 3 for deployments that choose it as their DB-API driver. The collector itself remains driver-agnostic and can be tested with a DB-API-compatible adapter. No production KMS/HSM provider, DSN/secret resolver, deployment agent, or live PostgreSQL service is bundled yet.

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

The source-side read-only collector and signing-provider interface are implemented, but AgentBox does not yet provision a deployment agent, resolve database secrets, or ship a concrete KMS/HSM provider. No live PostgreSQL service or deployed end-to-end test has been run. Source identity attestation, durable discovery scheduling and source-system event ingestion remain out of scope.


## Connector trust configuration

Connector trust is managed through tenant-scoped APIs and persisted in the existing AgentBox SQLite database. Register a connector with `POST /v1/enterprise-discovery/postgresql/connectors`; rotate by adding a new key ID at `POST /v1/enterprise-discovery/postgresql/connectors/{connector_id}/keys`; revoke a key at `POST /v1/enterprise-discovery/postgresql/connectors/{connector_id}/keys/{key_id}/revoke`. All operations require explicit `enterprise.discovery` grants and derive tenant/actor identity from the authenticated principal. Public key material and lifecycle events are append-only; revocation is an immutable event. The old key remains valid during a planned overlap until explicitly revoked.

The optional request field `attestation` has exactly four fields: `algorithm: "Ed25519"`, `key_id`, timezone-aware `signed_at`, and base64url `signature`; signed ingestion also requires the registered `connector_id`. Sign the canonical UTF-8 JSON payload returned by `PostgreSQLProvenanceVerifier.signing_payload` in the AgentBox implementation. It includes the contract identifier, authenticated tenant, exact registered source_ref, snapshot_hash, discovered_at, key_id and signed_at. The server derives tenant identity from the OIDC principal; a caller cannot choose it in the request.


### Connector lifecycle and key rotation

Connector registration binds one tenant, connector ID and normalized source locator. Each connector may have multiple immutable signing-key IDs to support overlapping rotation. Revoke the old key only after the connector has switched to the new key. A revoked key ID cannot be reactivated or reused; register a new key ID. Key revocation takes effect immediately for subsequent signed ingestions. Connector key and event rows have database triggers preventing updates/deletes. The connector public key registry is not a secret store: only public Ed25519 keys are accepted. Private signing keys must remain in the connector's protected environment. The registry and its audit events share the AgentBox SQLite persistence boundary and therefore inherit the current single-instance/backup limitations.


### Connector-side operating rules

- Run the collector inside the network boundary that can reach the database; do not expose the database to the AgentBox API.
- Give the DB role only catalog visibility required for the selected schemas. Do not grant application-table SELECT, DML, DDL or role-management privileges.
- Resolve DSNs/passwords from the deployment's secret manager at runtime. Do not place them in connector registration, source locators, logs, snapshots or API payloads.
- Use a non-exportable Ed25519 signing key in a KMS/HSM where available. The `SigningKeyProvider` adapter must sign the supplied canonical bytes without returning private key material.
- Register the connector public key before enabling signed ingestion; during rotation, register the next public key, switch the source-side signer, verify successful ingestion, then revoke the previous key.
- Treat catalog metadata as sensitive operational data. Apply schema allowlists, transport encryption, short retention and tenant-scoped access controls.


### Secret-backed, TLS-verified source connections

`app.postgresql_connection` provides a source-side `PostgreSQLConnectionFactory`. It resolves an opaque secret-manager reference immediately before each connection attempt; it does not cache, persist, or log the returned DSN. Deployments inject a `DatabaseSecretProvider` backed by their chosen vault or cloud secret manager. Secret references are not database connection strings, and path traversal references are rejected.

Every connection forces Psycopg's `sslmode=verify-full`, which requires certificate-chain and hostname verification. A deployment may provide an explicit CA bundle path. Connection timeout is bounded to 1–30 seconds, and the application name is bounded to PostgreSQL's 63-character limit. Psycopg 3 is imported lazily and remains an optional dependency.

Driver and secret-provider exceptions are deliberately replaced with a generic connector error because their original messages may contain credentials or private host details. The caller should use deployment-side secret-manager audit logs and database telemetry for diagnosis; it must not enable DSN-bearing debug logs.

The factory is dependency-injectable for deterministic tests. These tests verify runtime secret resolution, TLS policy arguments, timeout validation, path traversal rejection and exception sanitization. They do not prove a real vault integration, CA deployment, database role permissions or a live TLS handshake. Production deployment must supply and test its own secret-provider adapter and trusted CA configuration.


Example deployment wiring (the secret provider and CA path are deployment-owned):

```python
from app.postgresql_catalog_connector import PostgreSQLCatalogReader
from app.postgresql_connection import (
    PostgreSQLConnectionConfig,
    PostgreSQLConnectionFactory,
)

connection_factory = PostgreSQLConnectionFactory(
    config=PostgreSQLConnectionConfig(
        secret_ref="vault://production/agentbox/postgres-reader",
        connect_timeout_seconds=8,
        sslrootcert="/run/secrets/postgres-ca.pem",
    ),
    secret_provider=deployment_secret_provider,
)
snapshot = PostgreSQLCatalogReader().collect(
    connection_factory,
    ["public", "sales"],
)
```

The `deployment_secret_provider` symbol above is intentionally supplied by the deployment; AgentBox does not invent or embed a vault credential implementation.
