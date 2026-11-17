# OIDC callback transaction storage

**Status:** SQLite development adapter and PostgreSQL shared-store adapter implemented. No provider callback, code exchange, or session issuance is enabled.

## Repository contract

Both adapters implement the provider-neutral `OidcCallbackTransactionStore` protocol. Records contain the client ID, exact redirect URI, SHA-256 state and nonce hashes, a PKCE verifier secret-manager reference, and bounded creation/expiry timestamps. Raw state, nonce, PKCE verifier, authorization code, access token, refresh token, and client secret are not persisted.

## SQLite development adapter

`app.oidc_callback_store_sqlite.SQLiteOidcCallbackTransactionStore` uses a durable SQLite file, WAL mode, a bounded busy timeout, parameterized statements, and `BEGIN IMMEDIATE` around read-and-delete consumption. It is limited to processes sharing a local database file on one host; it is not a distributed lock.

## PostgreSQL shared adapter

`app.oidc_callback_store_postgres.PostgresOidcCallbackTransactionStore` accepts a PostgreSQL DSN supplied by deployment secret management. Call `initialize()` for local/test bootstrap; production deployments should apply the versioned SQL migration at `backend/migrations/0001_oidc_callback_transactions.sql` through the deployment migration process.

Consumption uses a single conditional `DELETE ... RETURNING` statement with the expiry predicate. PostgreSQL row locking and statement atomicity ensure that concurrent consumers connected to the shared database have at most one winner across processes and hosts. Expired matching records are deleted and return no transaction. The expiry index supports cleanup through `purge_expired`.

The adapter opens a short-lived psycopg connection per operation and configures a bounded connection timeout. Production deployments should put a managed pool/proxy in front of PostgreSQL, use TLS and least-privilege database credentials, restrict network access, monitor connection exhaustion, and back up/patch PostgreSQL. Never log the DSN or transaction payloads. The CI integration tests use an ephemeral PostgreSQL 16 service and exercise real SQL, persistence, expiry, replay, duplicate IDs, and concurrent consumers across independent connections.

## Security and deployment boundaries

The PostgreSQL adapter provides shared-database atomicity; it does not by itself make the entire authentication flow production-ready. A maintained OIDC SDK must still perform authorization-code exchange, PKCE verification, issuer/audience/signature/time checks, nonce validation, and key rotation handling. No callback endpoint, provider integration, token exchange, web BFF, secure cookie issuance, or Flutter secure token storage is implemented here. Tenant identity remains server-authoritative.
