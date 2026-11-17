"""Issue and validate opaque AgentBox application sessions after OIDC identity verification."""
from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass

from app.oidc_authorization_flow import VerifiedOidcIdentity
from app.oidc_session_contract import (
    OidcApplicationSession,
    OidcApplicationSessionStore,
    validate_oidc_application_session,
)


@dataclass(frozen=True)
class IssuedOidcSession:
    """Raw credentials returned exactly once to the caller for secure transport."""

    session_token: str
    csrf_token: str
    expires_at_epoch: int


class OidcSessionService:
    """Exchange a verified OIDC identity for a revocable, opaque application session."""

    def __init__(
        self,
        store: OidcApplicationSessionStore,
        *,
        ttl_seconds: int = 28_800,
    ) -> None:
        if (
            isinstance(ttl_seconds, bool)
            or not isinstance(ttl_seconds, int)
            or not 1 <= ttl_seconds <= 43_200
        ):
            raise ValueError("ttl_seconds must be between 1 and 43200")
        self._store = store
        self._ttl = ttl_seconds

    @staticmethod
    def _hash(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _validate_clock(now_epoch: int) -> None:
        if isinstance(now_epoch, bool) or not isinstance(now_epoch, int) or now_epoch < 0:
            raise ValueError("now_epoch must be a non-negative integer")

    def issue(
        self, identity: VerifiedOidcIdentity, *, now_epoch: int
    ) -> IssuedOidcSession:
        self._validate_clock(now_epoch)
        if not isinstance(identity, VerifiedOidcIdentity):
            raise TypeError("A verified OIDC identity is required")
        session_token = secrets.token_urlsafe(48)
        csrf_token = secrets.token_urlsafe(32)
        expires_at = now_epoch + self._ttl
        session = OidcApplicationSession(
            token_hash=self._hash(session_token),
            csrf_token_hash=self._hash(csrf_token),
            subject_id=identity.subject_id,
            tenant_id=identity.tenant_id,
            issuer=identity.issuer,
            client_id=identity.client_id,
            created_at_epoch=now_epoch,
            expires_at_epoch=expires_at,
        )
        errors = validate_oidc_application_session(session)
        if errors:
            raise ValueError("Invalid OIDC application session: " + "; ".join(errors))
        self._store.create(session)
        return IssuedOidcSession(
            session_token=session_token,
            csrf_token=csrf_token,
            expires_at_epoch=expires_at,
        )

    def authenticate(
        self, session_token: str, *, now_epoch: int
    ) -> OidcApplicationSession | None:
        self._validate_clock(now_epoch)
        if not isinstance(session_token, str) or not 43 <= len(session_token) <= 256:
            return None
        return self._store.get_live(self._hash(session_token), now_epoch=now_epoch)

    @classmethod
    def validate_csrf(
        cls, session: OidcApplicationSession, csrf_token: str | None
    ) -> bool:
        if not isinstance(csrf_token, str) or not 32 <= len(csrf_token) <= 256:
            return False
        return hmac.compare_digest(
            cls._hash(csrf_token), session.csrf_token_hash
        )

    def revoke(self, session_token: str, *, now_epoch: int) -> bool:
        self._validate_clock(now_epoch)
        if not isinstance(session_token, str) or not 43 <= len(session_token) <= 256:
            return False
        return self._store.revoke(self._hash(session_token), now_epoch=now_epoch)
