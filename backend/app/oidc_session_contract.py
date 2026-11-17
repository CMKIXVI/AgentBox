"""Opaque application-session contracts for AgentBox OIDC login."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
_MAX_SESSION_TTL_SECONDS = 43_200


@dataclass(frozen=True)
class OidcApplicationSession:
    """Persisted session metadata; bearer and CSRF secrets are represented only by hashes."""

    token_hash: str
    csrf_token_hash: str
    subject_id: str
    tenant_id: str
    issuer: str
    client_id: str
    created_at_epoch: int
    expires_at_epoch: int
    revoked_at_epoch: int | None = None


def validate_oidc_application_session(session: OidcApplicationSession) -> list[str]:
    """Return stable validation errors for an opaque session record."""
    errors: list[str] = []
    for field_name in ("token_hash", "csrf_token_hash"):
        value = getattr(session, field_name)
        if not isinstance(value, str) or not _SHA256_HEX.fullmatch(value):
            errors.append(f"{field_name} must be a lowercase SHA-256 hex digest")
    for field_name, maximum in (
        ("subject_id", 256), ("tenant_id", 256), ("issuer", 2048), ("client_id", 256)
    ):
        value = getattr(session, field_name)
        if not isinstance(value, str) or not value.strip() or len(value) > maximum:
            errors.append(f"{field_name} must contain 1 to {maximum} characters")
    if (
        isinstance(session.created_at_epoch, bool)
        or not isinstance(session.created_at_epoch, int)
        or isinstance(session.expires_at_epoch, bool)
        or not isinstance(session.expires_at_epoch, int)
    ):
        errors.append("session timestamps must be integer epoch seconds")
    elif (
        session.created_at_epoch < 0
        or session.expires_at_epoch <= session.created_at_epoch
        or session.expires_at_epoch - session.created_at_epoch > _MAX_SESSION_TTL_SECONDS
    ):
        errors.append("session lifetime must be between 1 and 43200 seconds")
    if session.revoked_at_epoch is not None and (
        isinstance(session.revoked_at_epoch, bool)
        or not isinstance(session.revoked_at_epoch, int)
        or session.revoked_at_epoch < session.created_at_epoch
    ):
        errors.append("revoked_at_epoch must be null or an integer at/after session creation")
    return errors


@runtime_checkable
class OidcApplicationSessionStore(Protocol):
    """Durable repository for hashed, revocable application sessions."""

    def create(self, session: OidcApplicationSession) -> None:
        """Persist a new session; duplicate token hashes must be rejected."""
        ...

    def get_live(self, token_hash: str, *, now_epoch: int) -> OidcApplicationSession | None:
        """Return a non-revoked, unexpired session matching a token hash."""
        ...

    def revoke(self, token_hash: str, *, now_epoch: int) -> bool:
        """Atomically revoke one live session; return whether this call won."""
        ...

    def purge(self, *, now_epoch: int) -> int:
        """Delete expired or revoked sessions and return the number removed."""
        ...
