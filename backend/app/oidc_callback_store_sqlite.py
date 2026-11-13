"""SQLite development adapter for one-time OIDC callback transactions.

SQLite serializes writers with BEGIN IMMEDIATE, making consume_once atomic for
processes sharing this database file on one host. This is not a multi-host store.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from app.oidc_callback_contract import (
    OidcCallbackTransaction,
    OidcCallbackTransactionStore,
    validate_callback_transaction,
)


class SQLiteOidcCallbackTransactionStore(OidcCallbackTransactionStore):
    """Durable single-host adapter; use a shared transactional DB for multi-host."""

    def __init__(self, database_path: str | Path, *, timeout_seconds: float = 5.0):
        self._database_path = str(database_path)
        self._timeout_seconds = timeout_seconds
        if self._database_path != ":memory:":
            Path(self._database_path).parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self._database_path,
            timeout=self._timeout_seconds,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute(
            f"PRAGMA busy_timeout = {max(1, int(self._timeout_seconds * 1000))}"
        )
        return connection

    def initialize(self) -> None:
        """Create the durable transaction table; safe to call on startup."""
        with self._connect() as connection:
            if self._database_path != ":memory:":
                connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS oidc_callback_transactions (
                    transaction_id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    redirect_uri TEXT NOT NULL,
                    state_hash TEXT NOT NULL CHECK(length(state_hash) = 64),
                    nonce_hash TEXT NOT NULL CHECK(length(nonce_hash) = 64),
                    pkce_verifier_ref TEXT NOT NULL,
                    created_at_epoch INTEGER NOT NULL,
                    expires_at_epoch INTEGER NOT NULL,
                    CHECK(expires_at_epoch > created_at_epoch),
                    CHECK(expires_at_epoch - created_at_epoch <= 600)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_oidc_callback_expiry
                ON oidc_callback_transactions(expires_at_epoch)
                """
            )

    def save(self, transaction: OidcCallbackTransaction) -> None:
        """Insert a validated transaction; duplicate IDs are rejected."""
        errors = validate_callback_transaction(transaction)
        if errors:
            raise ValueError("Invalid OIDC callback transaction: " + "; ".join(errors))
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO oidc_callback_transactions (
                    transaction_id, client_id, redirect_uri, state_hash,
                    nonce_hash, pkce_verifier_ref, created_at_epoch, expires_at_epoch
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    transaction.transaction_id,
                    transaction.client_id,
                    transaction.redirect_uri,
                    transaction.state_hash,
                    transaction.nonce_hash,
                    transaction.pkce_verifier_ref,
                    transaction.created_at_epoch,
                    transaction.expires_at_epoch,
                ),
            )
            connection.commit()
        except sqlite3.IntegrityError as exc:
            connection.rollback()
            raise ValueError("Callback transaction ID already exists or violates storage constraints") from exc
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def consume_once(
        self, transaction_id: str, *, now_epoch: int
    ) -> OidcCallbackTransaction | None:
        """Atomically delete and return one unexpired transaction.

        BEGIN IMMEDIATE serializes competing writers before the read. This
        guarantee applies only to processes sharing this SQLite database file.
        """
        if not isinstance(transaction_id, str) or not transaction_id:
            return None
        if isinstance(now_epoch, bool) or not isinstance(now_epoch, int):
            raise ValueError("now_epoch must be an integer epoch timestamp")

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT transaction_id, client_id, redirect_uri, state_hash,
                       nonce_hash, pkce_verifier_ref, created_at_epoch, expires_at_epoch
                FROM oidc_callback_transactions
                WHERE transaction_id = ? AND expires_at_epoch > ?
                """,
                (transaction_id, now_epoch),
            ).fetchone()

            if row is None:
                connection.execute(
                    "DELETE FROM oidc_callback_transactions WHERE transaction_id = ?",
                    (transaction_id,),
                )
                connection.commit()
                return None

            deleted = connection.execute(
                "DELETE FROM oidc_callback_transactions WHERE transaction_id = ?",
                (transaction_id,),
            ).rowcount
            if deleted != 1:
                connection.rollback()
                return None
            connection.commit()
            return OidcCallbackTransaction(
                transaction_id=row["transaction_id"],
                client_id=row["client_id"],
                redirect_uri=row["redirect_uri"],
                state_hash=row["state_hash"],
                nonce_hash=row["nonce_hash"],
                pkce_verifier_ref=row["pkce_verifier_ref"],
                created_at_epoch=row["created_at_epoch"],
                expires_at_epoch=row["expires_at_epoch"],
            )
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def purge_expired(self, *, now_epoch: int) -> int:
        """Delete expired rows as maintenance; return the number removed."""
        if isinstance(now_epoch, bool) or not isinstance(now_epoch, int):
            raise ValueError("now_epoch must be an integer epoch timestamp")
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                "DELETE FROM oidc_callback_transactions WHERE expires_at_epoch <= ?",
                (now_epoch,),
            )
            deleted = cursor.rowcount
            connection.commit()
            return deleted
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
