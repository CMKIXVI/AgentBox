# OIDC callback transaction storage

**Status:** SQLite development adapter implemented. No provider callback or token exchange is enabled.

## Repository contract

The callback transaction repository stores only the client ID, exact redirect URI, SHA-256 state and nonce hashes, a PKCE verifier secret-manager reference, and bounded creation/expiry timestamps. Raw state, nonce, PKCE verifier, authorization code, access token, refresh token, and client secret are not persisted.

The provider-neutral `OidcCallbackTransactionStore` protocol defines the consume operation. Implementations must additionally provide transaction insertion. The SQLite adapter implements both operations and expiry cleanup.

## SQLite development adapter

`app.oidc_callback_store_sqlite.SQLiteOidcCallbackTransactionStore` uses a durable SQLite file, WAL mode, a bounded busy timeout, parameterized statements, and `BEGIN IMMEDIATE` around read-and-delete consumption. The write lock is acquired before checking the row, so competing processes sharing the same database file cannot both consume one transaction. Successful consumption deletes the row; subsequent attempts return no record. Expired records are rejected and deleted.

Example:

```python
store = SQLiteOidcCallbackTransactionStore("/var/lib/agentbox/oidc-callbacks.sqlite3")
store.save(transaction)
consumed = store.consume_once(transaction.transaction_id, now_epoch=now_epoch)
```

The application must supply a trusted clock and generate state/nonce hashes and secret references through its future maintained OIDC SDK integration.

## Deployment boundary

This SQLite adapter is for development or a single-host deployment with a local durable filesystem. WAL mode is not a multi-host distributed lock. Do not place this database on an arbitrary network filesystem or use it to claim replay safety across multiple hosts/containers.

A production multi-instance deployment must implement the same repository protocol on PostgreSQL or another transactional shared database, using a single atomic consume operation (for example, row locking with `SELECT ... FOR UPDATE` inside a transaction or a conditional `DELETE ... RETURNING`). It must preserve unique transaction IDs, expiry checks, and one-winner semantics. That adapter is not included in this batch.

## Security boundaries

Consuming a transaction does not validate the authorization code or ID token. A maintained OIDC SDK must still perform code exchange, PKCE verification, issuer/audience/signature/time checks, nonce validation, and key rotation handling. FastAPI remains the sole tenant and authorization authority. No tenant identity is read from callback parameters.
