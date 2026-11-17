"""SQLite development adapter for opaque OIDC application sessions.

Use the PostgreSQL adapter for shared multi-instance deployments. Raw session and
CSRF credentials are never persisted; only SHA-256 hashes are stored.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from app.oidc_session_contract import (
    OidcApplicationSession,
    OidcApplicationSessionStore,
    validate_oidc_application_session,
)

_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS oidc_application_sessions (
    token_hash TEXT PRIMARY KEY CHECK(length(token_hash) = 64),
    csrf_token_hash TEXT NOT NULL CHECK(length(csrf_token_hash) = 64),
    subject_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    issuer TEXT NOT NULL,
    client_id TEXT NOT NULL,
    created_at_epoch INTEGER NOT NULL,
    expires_at_epoch INTEGER NOT NULL,
    revoked_at_epoch INTEGER,
    CHECK(expires_at_epoch > created_at_epoch),
    CHECK(expires_at_epoch - created_at_epoch <= 43200),
    CHECK(revoked_at_epoch IS NULL OR revoked_at_epoch >= created_at_epoch)
)
"""


def _from_row(row: sqlite3.Row) -> OidcApplicationSession:
    return OidcApplicationSession(
        token_hash=row["token_hash"],
        csrf_token_hash=row["csrf_token_hash"],
        subject_id=row["subject_id"],
        tenant_id=row["tenant_id"],
        issuer=row["issuer"],
        client_id=row["client_id"],
        created_at_epoch=row["created_at_epoch"],
        expires_at_epoch=row["expires_at_epoch"],
        revoked_at_epoch=row["revoked_at_epoch"],
    )


class SQLiteOidcApplicationSessionStore(OidcApplicationSessionStore):
    """Durable single-host session repository."""

    def __init__(self, database_path: str | Path, *, timeout_seconds: float = 5.0):
        self._database_path = str(database_path)
        if self._database_path == ":memory:":
            raise ValueError("A durable SQLite file path is required for OIDC sessions")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._timeout_seconds = timeout_seconds
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
        connection = self._connect()
        try:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(_CREATE_TABLE)
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_oidc_application_sessions_expiry
                ON oidc_application_sessions(expires_at_epoch)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_oidc_application_sessions_tenant
                ON oidc_application_sessions(tenant_id, subject_id)
                """
            )
        finally:
            connection.close()

    def create(self, session: OidcApplicationSession) -> None:
        errors = validate_oidc_application_session(session)
        if errors:
            raise ValueError("Invalid OIDC application session: " + "; ".join(errors))
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO oidc_application_sessions (
                    token_hash, csrf_token_hash, subject_id, tenant_id, issuer,
                    client_id, created_at_epoch, expires_at_epoch, revoked_at_epoch
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.token_hash, session.csrf_token_hash, session.subject_id,
                    session.tenant_id, session.issuer, session.client_id,
                    session.created_at_epoch, session.expires_at_epoch,
                    session.revoked_at_epoch,
                ),
            )
            connection.commit()
        except sqlite3.IntegrityError as exc:
            connection.rollback()
            raise ValueError("OIDC application session already exists or violates storage constraints") from exc
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def get_live(
        self, token_hash: str, *, now_epoch: int
    ) -> OidcApplicationSession | None:
        if not isinstance(token_hash, str) or not _SHA256_HEX.fullmatch(token_hash):
            return None
        if isinstance(now_epoch, bool) or not isinstance(now_epoch, int):
            raise TypeError("now_epoch must be an integer epoch timestamp")
        connection = self._connect()
        try:
            row = connection.execute(
                """
                SELECT token_hash, csrf_token_hash, subject_id, tenant_id, issuer,
                       client_id, created_at_epoch, expires_at_epoch, revoked_at_epoch
                FROM oidc_application_sessions
                WHERE token_hash = ? AND revoked_at_epoch IS NULL AND expires_at_epoch > ?
                """,
                (token_hash, now_epoch),
            ).fetchone()
            return _from_row(row) if row is not None else None
        finally:
            connection.close()

    def revoke(self, token_hash: str, *, now_epoch: int) -> bool:
        if not isinstance(token_hash, str) or not _SHA256_HEX.fullmatch(token_hash):
            return False
        if isinstance(now_epoch, bool) or not isinstance(now_epoch, int):
            raise TypeError("now_epoch must be an integer epoch timestamp")
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            changed = connection.execute(
                """
                UPDATE oidc_application_sessions
                SET revoked_at_epoch = ?
                WHERE token_hash = ? AND revoked_at_epoch IS NULL AND expires_at_epoch > ?
                """,
                (now_epoch, token_hash, now_epoch),
            ).rowcount
            connection.commit()
            return changed == 1
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def purge(self, *, now_epoch: int) -> int:
        if isinstance(now_epoch, bool) or not isinstance(now_epoch, int):
            raise TypeError("now_epoch must be an integer epoch timestamp")
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            removed = connection.execute(
                """
                DELETE FROM oidc_application_sessions
                WHERE expires_at_epoch <= ? OR revoked_at_epoch IS NOT NULL
                """,
                (now_epoch,),
            ).rowcount
            connection.commit()
            return removed
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
