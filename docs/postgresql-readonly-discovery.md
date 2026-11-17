# AgentBox PostgreSQL Read-only Discovery

## Scope

This is the first PostgreSQL discovery adapter for the existing AgentBox Enterprise Context Engine. It uses an injected DB-API connection factory and the PostgreSQL system catalogs only. The connector does not require a second database, graph service, broker, microservice, or frontend.

## Safety and operating contract

- The caller supplies an already-authenticated connection factory; AgentBox does not accept or persist passwords, DSNs, tokens, or private keys in discovery payloads.
- The adapter starts a `READ ONLY` transaction, applies a bounded statement timeout, and rolls the transaction back after catalog inspection.
- It reads schema, relation, column, index, and constraint metadata from `pg_catalog`.
- It never selects application table rows, reads application payloads, or issues source-system writes.
- Schema allowlists are exact, validated identifiers. Catalog result counts have hard bounds.
- The output contains metadata and a stable SHA-256 snapshot hash. It contains no connection string or credential field.

## Contract

`PostgreSQLCatalogDiscovery(connection_factory).discover(schemas=None)` returns a versioned metadata snapshot. Optional `schemas` is an exact allowlist. Relations include tables, partitioned tables, views, materialized views, and foreign tables. Columns include ordinal position, formatted data type, nullability, and comments. Indexes and constraints include definitions and foreign-key target metadata.

## Current boundary

This batch supplies the tested catalog adapter library only. It is deliberately not wired to a public HTTP endpoint: the repository does not yet have a production secret-provider / connector-registration contract to safely resolve source credentials. The next integration stage must add an operator-provisioned connector identity, secret reference resolution, least-privilege role verification, tenant-bound discovery job persistence, ECE entity/relationship/evidence ingestion, and API authorization before exposing remote discovery.

The adapter's injected connection must be provisioned with a dedicated PostgreSQL role limited to catalog visibility and read-only transaction use. A local fake DB-API test verifies query routing and lifecycle; it is not a live PostgreSQL integration test.
