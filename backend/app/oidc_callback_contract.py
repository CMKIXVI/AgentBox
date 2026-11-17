"""Provider-neutral OIDC redirect and callback transaction contracts.

No HTTP callback, token exchange, or identity-provider SDK is implemented here.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
_MAX_TRANSACTION_TTL_SECONDS = 600


def is_registered_redirect_uri(
    registration: dict,
    client_id: str,
    redirect_uri: str,
    *,
    post_logout: bool = False,
) -> bool:
    """Check exact URI membership for the identified client; never normalize."""
    if not isinstance(registration, dict) or not isinstance(client_id, str):
        return False
    if not isinstance(redirect_uri, str) or not redirect_uri:
        return False
    clients = registration.get("clients")
    if not isinstance(clients, list):
        return False
    matches = [
        client for client in clients
        if isinstance(client, dict) and client.get("client_id") == client_id
    ]
    if len(matches) != 1:
        return False
    field = "post_logout_redirect_uris" if post_logout else "redirect_uris"
    allowlist = matches[0].get(field, [])
    return isinstance(allowlist, list) and redirect_uri in allowlist


@dataclass(frozen=True)
class OidcCallbackTransaction:
    """Persist only hashes/references, never raw state, nonce, or PKCE verifier."""

    transaction_id: str
    client_id: str
    redirect_uri: str
    state_hash: str
    nonce_hash: str
    pkce_verifier_ref: str
    created_at_epoch: int
    expires_at_epoch: int


def validate_callback_transaction(
    transaction: OidcCallbackTransaction,
) -> list[str]:
    """Return stable invariant violations for a callback transaction."""
    errors: list[str] = []
    for field_name in (
        "transaction_id", "client_id", "redirect_uri",
        "state_hash", "nonce_hash", "pkce_verifier_ref",
    ):
        value = getattr(transaction, field_name)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{field_name} is required")
    if isinstance(transaction.state_hash, str) and not _SHA256_HEX.fullmatch(
        transaction.state_hash
    ):
        errors.append("state_hash must be a lowercase SHA-256 hex digest")
    if isinstance(transaction.nonce_hash, str) and not _SHA256_HEX.fullmatch(
        transaction.nonce_hash
    ):
        errors.append("nonce_hash must be a lowercase SHA-256 hex digest")
    if (
        isinstance(transaction.created_at_epoch, bool)
        or not isinstance(transaction.created_at_epoch, int)
        or isinstance(transaction.expires_at_epoch, bool)
        or not isinstance(transaction.expires_at_epoch, int)
    ):
        errors.append("transaction timestamps must be integer epoch seconds")
    elif (
        transaction.expires_at_epoch <= transaction.created_at_epoch
        or transaction.expires_at_epoch - transaction.created_at_epoch
        > _MAX_TRANSACTION_TTL_SECONDS
    ):
        errors.append("transaction lifetime must be between 1 and 600 seconds")
    return errors


@runtime_checkable
class OidcCallbackTransactionStore(Protocol):
    """Persistence port for short-lived, single-use callback transactions."""

    def save(self, transaction: OidcCallbackTransaction) -> None:
        """Persist a validated transaction; reject duplicate transaction IDs."""
        ...

    def consume_once(
        self, transaction_id: str, *, now_epoch: int
    ) -> OidcCallbackTransaction | None:
        """Atomically return and consume a live record, or return None.

        Implementations must enforce expiry and one-time use in one transaction.
        A read followed by a separate delete/update is not sufficient.
        """
        ...
