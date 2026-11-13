"""PostgreSQL adapter for shared, multi-instance OIDC callback transactions.

Consumption uses one conditional DELETE ... RETURNING statement. PostgreSQL row
locking guarantees that concurrent consumers across backend instances have one winner.
"""
from __future__ import annotations

from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.oidc_callback_contract import (
    OidcCallbackTransaction,
    OidcCallbackTransactionStore,
    validate_callback_transaction,
)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS oidc_callback_transactions (
    transaction_id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    redirect_uri TEXT NOT NULL,
    state_hash CHAR(64) NOT NULL CHECK (state_hash ~ '^[0-9a-f]{64}$'),
    nonce_hash CHAR(64) NOT NULL CHECK (nonce_hash ~ '^[0-9a-f]{64}$'),
    pkce_verifier_ref TEXT NOT NULL,
    created_at_epoch BIGINT NOT NULL,
    expires_at_epoch BIGINT NOT NULL,
    CHECK (expires_at_epoch > created_at_epoch),
    CHECK (expires_at_epoch - created_at_epoch <= 600)
)
"""
_CREATE_EXPIRY_INDEX = """
CREATE INDEX IF NOT EXISTS idx_oidc_callback_transactions_expiry
ON oidc_callback_transactions (expires_at_epoch)
"""


def _from_row(row: dict[str, Any]) -> OidcCallbackTransaction:
    return OidcCallbackTransaction(
        transaction_id=row["transaction_id"],
        client_id=row["client_id"],
        redirect_uri=row["redirect_uri"],
        state_hash=row["state_hash"].strip(),
        nonce_hash=row["nonce_hash"].strip(),
        pkce_verifier_ref=row["pkce_verifier_ref"],
        created_at_epoch=row["created_at_epoch"],
        expires_at_epoch=row["expires_at_epoch"],
    )


class PostgresOidcCallbackTransactionStore(OidcCallbackTransactionStore):
    """Shared PostgreSQL repository; pass a secret-managed DSN at construction."""

    def __init__(self, dsn: str, *, connect_timeout: int = 5):
        if not isinstance(dsn, str) or not dsn.strip():
            raise ValueError("A PostgreSQL DSN is required")
        if isinstance(connect_timeout, bool) or not isinstance(connect_timeout, int) or connect_timeout <= 0:
            raise ValueError("connect_timeout must be a positive integer")
        self._dsn = dsn
        self._connect_timeout = connect_timeout

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(
            self._dsn,
            connect_timeout=self._connect_timeout,
            row_factory=dict_row,
            application_name="agentbox-oidc-callback-store",
        )

    def initialize(self) -> None:
        """Apply the idempotent base schema; production deployments should run migrations."""
        with self._connect() as connection:
            connection.execute(_CREATE_TABLE)
            connection.execute(_CREATE_EXPIRY_INDEX)

    def save(self, transaction: OidcCallbackTransaction) -> None:
        errors = validate_callback_transaction(transaction)
        if errors:
            raise ValueError("Invalid OIDC callback transaction: " + "; ".join(errors))
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO oidc_callback_transactions (
                    transaction_id, client_id, redirect_uri, state_hash,
                    nonce_hash, pkce_verifier_ref, created_at_epoch, expires_at_epoch
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    transaction.transaction_id, transaction.client_id,
                    transaction.redirect_uri, transaction.state_hash,
                    transaction.nonce_hash, transaction.pkce_verifier_ref,
                    transaction.created_at_epoch, transaction.expires_at_epoch,
                ),
            )

    def consume_once(
        self, transaction_id: str, *, now_epoch: int
    ) -> OidcCallbackTransaction | None:
        if not isinstance(transaction_id, str) or not transaction_id:
            return None
        if isinstance(now_epoch, bool) or not isinstance(now_epoch, int):
            raise TypeError("now_epoch must be an integer epoch timestamp")
        with self._connect() as connection:
            row = connection.execute(
                """
                DELETE FROM oidc_callback_transactions
                WHERE transaction_id = %s AND expires_at_epoch > %s
                RETURNING transaction_id, client_id, redirect_uri, state_hash,
                          nonce_hash, pkce_verifier_ref, created_at_epoch, expires_at_epoch
                """,
                (transaction_id, now_epoch),
            ).fetchone()
            if row is not None:
                return _from_row(row)
            connection.execute(
                """
                DELETE FROM oidc_callback_transactions
                WHERE transaction_id = %s AND expires_at_epoch <= %s
                """,
                (transaction_id, now_epoch),
            )
            return None

    def purge_expired(self, *, now_epoch: int) -> int:
        if isinstance(now_epoch, bool) or not isinstance(now_epoch, int):
            raise TypeError("now_epoch must be an integer epoch timestamp")
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM oidc_callback_transactions WHERE expires_at_epoch <= %s",
                (now_epoch,),
            )
            return cursor.rowcount
