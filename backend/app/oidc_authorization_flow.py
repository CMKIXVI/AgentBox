"""Provider-neutral OIDC Authorization Code + PKCE orchestration.

The provider adapter is responsible for code exchange and cryptographic ID-token
validation (signature/JWKS, issuer, audience, timestamps and algorithm allowlist).
This module binds that verified result to the one-time state/nonce transaction.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from contextlib import suppress
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlencode, urlsplit, urlunsplit

from app.oidc_callback_contract import (
    OidcCallbackTransaction,
    OidcCallbackTransactionStore,
    is_registered_redirect_uri,
)
from app.oidc_client_registration import validate_oidc_client_registration


class OidcAuthorizationError(Exception):
    """A login transaction could not be safely started or completed."""


class PkceSecretStore(Protocol):
    def put(self, reference: str, secret: str) -> None: ...
    def get(self, reference: str) -> str: ...
    def delete(self, reference: str) -> None: ...


class OidcAuthorizationCodeExchanger(Protocol):
    """Exchange code and cryptographically validate the ID token before returning claims."""

    def exchange_and_validate(
        self,
        *,
        code: str,
        client_id: str,
        redirect_uri: str,
        code_verifier: str,
        now_epoch: int,
    ) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class OidcLoginStart:
    authorization_url: str
    expires_at_epoch: int


@dataclass(frozen=True)
class VerifiedOidcIdentity:
    subject_id: str
    tenant_id: str
    issuer: str
    client_id: str


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


class OidcAuthorizationFlow:
    """Create and complete short-lived OIDC login transactions."""

    def __init__(
        self,
        *,
        registration: dict[str, Any],
        issuer: str,
        authorization_endpoint: str,
        tenant_claim: str,
        transactions: OidcCallbackTransactionStore,
        secrets_store: PkceSecretStore,
        exchanger: OidcAuthorizationCodeExchanger,
        transaction_ttl_seconds: int = 300,
        scopes: tuple[str, ...] = ("openid", "profile", "email"),
    ) -> None:
        errors = validate_oidc_client_registration(registration)
        if errors:
            raise ValueError("Invalid OIDC client registration")
        issuer_parts = urlsplit(issuer)
        endpoint_parts = urlsplit(authorization_endpoint)
        if (
            issuer_parts.scheme != "https"
            or not issuer_parts.netloc
            or issuer_parts.username is not None
            or issuer_parts.password is not None
            or issuer_parts.query
            or issuer_parts.fragment
        ):
            raise ValueError("OIDC issuer must be a trusted HTTPS URL")
        if (
            endpoint_parts.scheme != "https"
            or not endpoint_parts.netloc
            or endpoint_parts.username is not None
            or endpoint_parts.password is not None
            or endpoint_parts.fragment
            or endpoint_parts.query
        ):
            raise ValueError("OIDC authorization endpoint must be a trusted HTTPS URL")
        if not tenant_claim or len(tenant_claim) > 128:
            raise ValueError("tenant_claim must contain 1 to 128 characters")
        if (
            isinstance(transaction_ttl_seconds, bool)
            or not isinstance(transaction_ttl_seconds, int)
            or not 1 <= transaction_ttl_seconds <= 600
        ):
            raise ValueError("transaction_ttl_seconds must be between 1 and 600")
        if (
            not isinstance(scopes, (tuple, list))
            or not scopes
            or "openid" not in scopes
            or any(not isinstance(scope, str) or not scope or " " in scope for scope in scopes)
        ):
            raise ValueError("OIDC scopes must include openid and contain valid scope tokens")
        self._registration = registration
        self._issuer = issuer
        self._authorization_endpoint = authorization_endpoint
        self._tenant_claim = tenant_claim
        self._transactions = transactions
        self._secrets_store = secrets_store
        self._exchanger = exchanger
        self._ttl = transaction_ttl_seconds
        self._scopes = tuple(dict.fromkeys(scopes))

    def _client(self, client_id: str) -> dict[str, Any]:
        matches = [
            item for item in self._registration["clients"]
            if item["client_id"] == client_id
        ]
        if len(matches) != 1:
            raise OidcAuthorizationError("Unknown OIDC client")
        return matches[0]

    def start(
        self, *, client_id: str, redirect_uri: str, now_epoch: int
    ) -> OidcLoginStart:
        if isinstance(now_epoch, bool) or not isinstance(now_epoch, int) or now_epoch < 0:
            raise ValueError("now_epoch must be a non-negative integer")
        self._client(client_id)
        if not is_registered_redirect_uri(self._registration, client_id, redirect_uri):
            raise OidcAuthorizationError("Redirect URI is not registered for this client")

        transaction_id = secrets.token_urlsafe(24)
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        secret_ref = f"vault://agentbox/oidc/pkce/{transaction_id}"
        expires_at = now_epoch + self._ttl
        transaction = OidcCallbackTransaction(
            transaction_id=transaction_id,
            client_id=client_id,
            redirect_uri=redirect_uri,
            state_hash=_sha256_hex(state),
            nonce_hash=_sha256_hex(nonce),
            pkce_verifier_ref=secret_ref,
            created_at_epoch=now_epoch,
            expires_at_epoch=expires_at,
        )

        self._secrets_store.put(secret_ref, verifier)
        try:
            self._transactions.save(transaction)
        except Exception:
            with suppress(Exception):
                self._secrets_store.delete(secret_ref)
            raise

        endpoint = urlsplit(self._authorization_endpoint)
        query = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(self._scopes),
            "state": state,
            "nonce": nonce,
            "code_challenge": _pkce_challenge(verifier),
            "code_challenge_method": "S256",
        }
        authorization_url = urlunsplit((
            endpoint.scheme, endpoint.netloc, endpoint.path, urlencode(query), ""
        ))
        return OidcLoginStart(
            authorization_url=authorization_url,
            expires_at_epoch=expires_at,
        )

    def complete(
        self,
        *,
        state: str,
        code: str,
        client_id: str,
        redirect_uri: str,
        now_epoch: int,
    ) -> VerifiedOidcIdentity:
        if not isinstance(state, str) or not 16 <= len(state) <= 512:
            raise OidcAuthorizationError("Invalid or expired OIDC login transaction")
        if not isinstance(code, str) or not 1 <= len(code) <= 8192:
            raise OidcAuthorizationError("Invalid or expired OIDC login transaction")
        if isinstance(now_epoch, bool) or not isinstance(now_epoch, int) or now_epoch < 0:
            raise ValueError("now_epoch must be a non-negative integer")

        transaction = self._transactions.consume_by_state_hash(
            _sha256_hex(state), now_epoch=now_epoch
        )
        if transaction is None:
            raise OidcAuthorizationError("Invalid or expired OIDC login transaction")

        secret_ref = transaction.pkce_verifier_ref
        try:
            if transaction.client_id != client_id or transaction.redirect_uri != redirect_uri:
                raise OidcAuthorizationError("OIDC callback does not match its original client")
            if not is_registered_redirect_uri(self._registration, client_id, redirect_uri):
                raise OidcAuthorizationError("OIDC callback redirect is no longer registered")

            verifier = self._secrets_store.get(secret_ref)
            claims = self._exchanger.exchange_and_validate(
                code=code,
                client_id=client_id,
                redirect_uri=redirect_uri,
                code_verifier=verifier,
                now_epoch=now_epoch,
            )
            if not isinstance(claims, Mapping):
                raise OidcAuthorizationError("OIDC provider returned an invalid identity")
            audience = claims.get("aud")
            audience_values = [audience] if isinstance(audience, str) else audience
            if (
                claims.get("iss") != self._issuer
                or not isinstance(audience_values, list)
                or client_id not in audience_values
                or (len(audience_values) > 1 and claims.get("azp") != client_id)
            ):
                raise OidcAuthorizationError("OIDC identity issuer or audience mismatch")
            expiry = claims.get("exp")
            issued_at = claims.get("iat")
            if (
                isinstance(expiry, bool) or not isinstance(expiry, int) or expiry <= now_epoch
                or isinstance(issued_at, bool) or not isinstance(issued_at, int)
                or issued_at > now_epoch + 60
            ):
                raise OidcAuthorizationError("OIDC identity is expired or has invalid timestamps")
            nonce = claims.get("nonce")
            if not isinstance(nonce, str) or not hmac.compare_digest(
                _sha256_hex(nonce), transaction.nonce_hash
            ):
                raise OidcAuthorizationError("OIDC nonce validation failed")
            subject = claims.get("sub")
            tenant_id = claims.get(self._tenant_claim)
            if (
                not isinstance(subject, str) or not subject or len(subject) > 256
                or not isinstance(tenant_id, str) or not tenant_id or len(tenant_id) > 256
            ):
                raise OidcAuthorizationError("OIDC identity is missing required claims")
            return VerifiedOidcIdentity(
                subject_id=subject,
                tenant_id=tenant_id,
                issuer=self._issuer,
                client_id=client_id,
            )
        except OidcAuthorizationError:
            raise
        except Exception as exc:
            raise OidcAuthorizationError("OIDC authorization code could not be validated") from exc
        finally:
            with suppress(Exception):
                # A verifier left in the secret store is unusable after transaction consumption.
                self._secrets_store.delete(secret_ref)
