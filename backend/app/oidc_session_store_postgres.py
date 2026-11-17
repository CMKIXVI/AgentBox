"""PostgreSQL adapter for shared, multi-instance OIDC application sessions."""
from __future__ import annotations

import re
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.oidc_session_contract import (
    OidcApplicationSession,
    OidcApplicationSessionStore,
    validate_oidc_application_session,
)

_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS oidc_application_sessions (
    token_hash CHAR(64) PRIMARY KEY CHECK(token_hash ~ '^[0-9a-f]{64}$'),
    csrf_token_hash CHAR(64) NOT NULL CHECK(csrf_token_hash ~ '^[0-9a-f]{64}$'),
    subject_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    issuer TEXT NOT NULL,
    client_id TEXT NOT NULL,
    created_at_epoch BIGINT NOT NULL,
    expires_at_epoch BIGINT NOT NULL,
    revoked_at_epoch BIGINT,
    CHECK(expires_at_epoch > created_at_epoch),
    CHECK(expires_at_epoch - created_at_epoch <= 43200),
    CHECK(revoked_at_epoch IS NULL OR revoked_at_epoch >= created_at_epoch)
)
"""
_CREATE_EXPIRY_INDEX = """
CREATE INDEX IF NOT EXISTS idx_oidc_application_sessions_expiry
ON oidc_application_sessions (expires_at_epoch)
"""
_CREATE_TENANT_INDEX = """
CREATE INDEX IF NOT EXISTS idx_oidc_application_sessions_tenant
ON oidc_application_sessions (tenant_id, subject_id)
"""


def _from_row(row: dict[str, Any]) -> OidcApplicationSession:
    return OidcApplicationSession(
        token_hash=row["token_hash"].strip(),
        csrf_token_hash=row["csrf_token_hash"].strip(),
        subject_id=row["subject_id"],
        tenant_id=row["tenant_id"],
        issuer=row["issuer"],
        client_id=row["client_id"],
        created_at_epoch=row["created_at_epoch"],
        expires_at_epoch=row["expires_at_epoch"],
        revoked_at_epoch=row["revoked_at_epoch"],
    )


class PostgresOidcApplicationSessionStore(OidcApplicationSessionStore):
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
            application_name="agentbox-oidc-session-store",
        )

    def initialize(self) -> None:
        """Apply the idempotent base schema; production deployments should run migrations."""
        with self._connect() as connection:
            connection.execute(_CREATE_TABLE)
            connection.execute(_CREATE_EXPIRY_INDEX)
            connection.execute(_CREATE_TENANT_INDEX)

    def create(self, session: OidcApplicationSession) -> None:
        errors = validate_oidc_application_session(session)
        if errors:
            raise ValueError("Invalid OIDC application session: " + "; ".join(errors))
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO oidc_application_sessions (
                    token_hash, csrf_token_hash, subject_id, tenant_id, issuer,
                    client_id, created_at_epoch, expires_at_epoch, revoked_at_epoch
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    session.token_hash, session.csrf_token_hash, session.subject_id,
                    session.tenant_id, session.issuer, session.client_id,
                    session.created_at_epoch, session.expires_at_epoch,
                    session.revoked_at_epoch,
                ),
            )

    def get_live(
        self, token_hash: str, *, now_epoch: int
    ) -> OidcApplicationSession | None:
        if not isinstance(token_hash, str) or not _SHA256_HEX.fullmatch(token_hash):
            return None
        if isinstance(now_epoch, bool) or not isinstance(now_epoch, int):
            raise TypeError("now_epoch must be an integer epoch timestamp")
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT token_hash, csrf_token_hash, subject_id, tenant_id, issuer,
                       client_id, created_at_epoch, expires_at_epoch, revoked_at_epoch
                FROM oidc_application_sessions
                WHERE token_hash = %s AND revoked_at_epoch IS NULL AND expires_at_epoch > %s
                """,
                (token_hash, now_epoch),
            ).fetchone()
            return _from_row(row) if row is not None else None

    def revoke(self, token_hash: str, *, now_epoch: int) -> bool:
        if not isinstance(token_hash, str) or not _SHA256_HEX.fullmatch(token_hash):
            return False
        if isinstance(now_epoch, bool) or not isinstance(now_epoch, int):
            raise TypeError("now_epoch must be an integer epoch timestamp")
        with self._connect() as connection:
            row = connection.execute(
                """
                UPDATE oidc_application_sessions
                SET revoked_at_epoch = %s
                WHERE token_hash = %s AND revoked_at_epoch IS NULL AND expires_at_epoch > %s
                RETURNING token_hash
                """,
                (now_epoch, token_hash, now_epoch),
            ).fetchone()
            return row is not None

    def purge(self, *, now_epoch: int) -> int:
        if isinstance(now_epoch, bool) or not isinstance(now_epoch, int):
            raise TypeError("now_epoch must be an integer epoch timestamp")
        with self._connect() as connection:
            cursor = connection.execute(
                """
                DELETE FROM oidc_application_sessions
                WHERE expires_at_epoch <= %s OR revoked_at_epoch IS NOT NULL
                """,
                (now_epoch,),
            )
            return cursor.rowcount
