"""HTTP OIDC provider adapter with discovery, PKCE exchange and ID-token verification.

Network access is injectable for deterministic tests. The adapter never follows
redirects, accepts only HTTPS metadata endpoints, and verifies ID tokens against
the issuer's live JWKS with an asymmetric algorithm allowlist.
"""
from __future__ import annotations

import json
import re
import secrets
import time
from collections.abc import Mapping
from typing import Any, Protocol, Self
from urllib.parse import urlsplit

import httpx
import jwt

from app.oidc_authorization_flow import OidcAuthorizationError
from app.oidc_callback_contract import is_registered_redirect_uri
from app.oidc_client_registration import validate_oidc_client_registration


_ALLOWED_ID_TOKEN_ALGORITHMS = frozenset({"RS256", "PS256", "ES256"})
_MAX_DOCUMENT_BYTES = 1_048_576
_MAX_JWKS_KEYS = 100
_PKCE_VERIFIER = re.compile(r"^[A-Za-z0-9._~-]{43,128}$")


class PrivateKeyResolver(Protocol):
    """Resolve a registered private-key reference to a PEM key and optional key id."""

    def resolve(self, reference: str) -> tuple[str | bytes, str | None]: ...


def _require_https_endpoint(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise OidcAuthorizationError(f"OIDC metadata field {field} must be an HTTPS URL")
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise OidcAuthorizationError(f"OIDC metadata field {field} must be an HTTPS URL")
    return value


class HttpOidcProviderAdapter:
    """Concrete OIDC authorization-code exchanger for web and native clients."""

    def __init__(
        self,
        *,
        issuer: str,
        registration: dict[str, Any],
        private_key_resolver: PrivateKeyResolver | None = None,
        http_client: httpx.Client | None = None,
        timeout_seconds: float = 5.0,
        clock_skew_seconds: int = 60,
    ) -> None:
        errors = validate_oidc_client_registration(registration)
        if errors:
            raise ValueError("Invalid OIDC client registration")
        issuer = _require_https_endpoint(issuer, "issuer")
        if urlsplit(issuer).query:
            raise ValueError("OIDC issuer must not contain a query")
        if not 0 < timeout_seconds <= 30:
            raise ValueError("timeout_seconds must be greater than 0 and at most 30")
        if not 0 <= clock_skew_seconds <= 120:
            raise ValueError("clock_skew_seconds must be between 0 and 120")
        self._issuer = issuer
        self._registration = registration
        self._private_key_resolver = private_key_resolver
        self._http = http_client or httpx.Client(
            timeout=httpx.Timeout(timeout_seconds),
            follow_redirects=False,
            headers={"Accept": "application/json"},
        )
        self._owns_http = http_client is None
        self._clock_skew = clock_skew_seconds
        self._metadata: dict[str, Any] | None = None

    def close(self) -> None:
        if self._owns_http:
            self._http.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _request_json(
        self, method: str, url: str, label: str, **kwargs: Any
    ) -> dict[str, Any]:
        try:
            with self._http.stream(method, url, follow_redirects=False, **kwargs) as response:
                if response.is_redirect:
                    raise OidcAuthorizationError(f"OIDC {label} endpoint must not redirect")
                response.raise_for_status()
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > _MAX_DOCUMENT_BYTES:
                        raise OidcAuthorizationError(
                            f"OIDC {label} response exceeds the size limit"
                        )
        except httpx.HTTPError as exc:
            raise OidcAuthorizationError(f"OIDC {label} request failed") from exc
        try:
            value = json.loads(body)
        except (ValueError, UnicodeDecodeError) as exc:
            raise OidcAuthorizationError(f"OIDC {label} response is not valid JSON") from exc
        if not isinstance(value, dict):
            raise OidcAuthorizationError(f"OIDC {label} response must be a JSON object")
        return value

    def _get_metadata(self) -> dict[str, Any]:
        if self._metadata is not None:
            return self._metadata
        discovery_url = f"{self._issuer.rstrip('/')}/.well-known/openid-configuration"
        try:
            metadata = self._request_json("GET", discovery_url, "discovery")
        except OidcAuthorizationError as exc:
            raise OidcAuthorizationError("OIDC discovery could not be loaded") from exc
        if metadata.get("issuer") != self._issuer:
            raise OidcAuthorizationError("OIDC discovery issuer does not exactly match configuration")
        for field in ("authorization_endpoint", "token_endpoint", "jwks_uri"):
            _require_https_endpoint(metadata.get(field), field)
        if "code" not in metadata.get("response_types_supported", []):
            raise OidcAuthorizationError("OIDC provider does not support authorization code flow")
        if "S256" not in metadata.get("code_challenge_methods_supported", []):
            raise OidcAuthorizationError("OIDC provider does not support PKCE S256")
        if "openid" not in metadata.get("scopes_supported", ["openid"]):
            raise OidcAuthorizationError("OIDC provider does not advertise the openid scope")
        self._metadata = metadata
        return metadata

    @property
    def authorization_endpoint(self) -> str:
        return self._get_metadata()["authorization_endpoint"]

    def _client(self, client_id: str) -> dict[str, Any]:
        clients = self._registration.get("clients", [])
        matches = [
            item for item in clients
            if isinstance(item, dict) and item.get("client_id") == client_id
        ]
        if len(matches) != 1:
            raise OidcAuthorizationError("Unknown OIDC client")
        return matches[0]

    def _client_auth(self, client: dict[str, Any], token_endpoint: str) -> dict[str, str]:
        method = client["token_endpoint_auth_method"]
        if method == "none":
            return {}
        if method != "private_key_jwt":
            raise OidcAuthorizationError(
                "This adapter supports only none and private_key_jwt client authentication"
            )
        if self._private_key_resolver is None:
            raise OidcAuthorizationError("OIDC private-key resolver is not configured")
        reference = client.get("client_secret_ref")
        if not isinstance(reference, str) or not reference:
            raise OidcAuthorizationError("OIDC client signing-key reference is missing")
        try:
            key, kid = self._private_key_resolver.resolve(reference)
            now = int(time.time())
            assertion = jwt.encode(
                {
                    "iss": client["client_id"],
                    "sub": client["client_id"],
                    "aud": token_endpoint,
                    "iat": now,
                    "exp": now + 60,
                    "jti": secrets.token_urlsafe(24),
                },
                key,
                algorithm="RS256",
                headers={"kid": kid} if kid else None,
            )
        except Exception as exc:
            raise OidcAuthorizationError("OIDC client assertion could not be created") from exc
        return {
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_assertion": assertion,
        }

    def _verify_id_token(
        self, token: str, *, client_id: str, now_epoch: int
    ) -> Mapping[str, Any]:
        if not isinstance(token, str) or not token or len(token) > 65_536:
            raise OidcAuthorizationError("OIDC provider returned an invalid ID token")
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as exc:
            raise OidcAuthorizationError("OIDC ID token header is invalid") from exc
        algorithm = header.get("alg")
        if algorithm not in _ALLOWED_ID_TOKEN_ALGORITHMS or header.get("crit"):
            raise OidcAuthorizationError("OIDC ID token uses an unsupported signing algorithm")
        kid = header.get("kid")
        if kid is not None and (not isinstance(kid, str) or not kid or len(kid) > 256):
            raise OidcAuthorizationError("OIDC ID token key identifier is invalid")

        metadata = self._get_metadata()
        try:
            jwks = self._request_json("GET", metadata["jwks_uri"], "JWKS")
        except OidcAuthorizationError as exc:
            raise OidcAuthorizationError("OIDC signing keys could not be loaded") from exc
        keys = jwks.get("keys")
        if not isinstance(keys, list) or not 1 <= len(keys) <= _MAX_JWKS_KEYS:
            raise OidcAuthorizationError("OIDC JWKS has an invalid key set")
        candidates = [
            item for item in keys
            if isinstance(item, dict)
            and item.get("use", "sig") == "sig"
            and item.get("kty") in {"RSA", "EC"}
            and (item.get("alg") in (None, algorithm))
            and (kid is None or item.get("kid") == kid)
        ]
        if len(candidates) != 1:
            raise OidcAuthorizationError("OIDC ID token signing key is missing or ambiguous")
        try:
            signing_key = jwt.PyJWK.from_dict(candidates[0], algorithm=algorithm).key
            claims = jwt.decode(
                token,
                signing_key,
                algorithms=[algorithm],
                audience=client_id,
                issuer=self._issuer,
                leeway=self._clock_skew,
                options={
                    "require": ["exp", "iat", "iss", "sub", "aud"],
                    "verify_signature": True,
                    "verify_exp": False,
                    "verify_iat": False,
                    "verify_nbf": False,
                    "verify_iss": True,
                    "verify_aud": True,
                },
            )
        except (jwt.PyJWTError, ValueError, TypeError) as exc:
            raise OidcAuthorizationError("OIDC ID token cryptographic validation failed") from exc
        if not isinstance(claims, dict):
            raise OidcAuthorizationError("OIDC ID token claims are invalid")
        expiry = claims.get("exp")
        issued_at = claims.get("iat")
        not_before = claims.get("nbf")
        if (
            isinstance(expiry, bool) or not isinstance(expiry, int)
            or expiry <= now_epoch
            or isinstance(issued_at, bool) or not isinstance(issued_at, int)
            or issued_at > now_epoch + self._clock_skew
            or (
                not_before is not None
                and (
                    isinstance(not_before, bool)
                    or not isinstance(not_before, int)
                    or not_before > now_epoch + self._clock_skew
                )
            )
        ):
            raise OidcAuthorizationError("OIDC ID token time claims are invalid")
        return claims

    def exchange_and_validate(
        self,
        *,
        code: str,
        client_id: str,
        redirect_uri: str,
        code_verifier: str,
        now_epoch: int,
    ) -> Mapping[str, Any]:
        if not isinstance(code, str) or not 1 <= len(code) <= 8192:
            raise OidcAuthorizationError("OIDC authorization code is invalid")
        if not isinstance(code_verifier, str) or not _PKCE_VERIFIER.fullmatch(code_verifier):
            raise OidcAuthorizationError("OIDC PKCE verifier must be 43 to 128 unreserved characters")
        if isinstance(now_epoch, bool) or not isinstance(now_epoch, int) or now_epoch < 0:
            raise ValueError("now_epoch must be a non-negative integer")
        client = self._client(client_id)
        if not is_registered_redirect_uri(self._registration, client_id, redirect_uri):
            raise OidcAuthorizationError("Redirect URI is not registered for this OIDC client")
        metadata = self._get_metadata()
        if "private_key_jwt" not in metadata.get(
            "token_endpoint_auth_methods_supported", ["client_secret_basic"]
        ) and client["token_endpoint_auth_method"] == "private_key_jwt":
            raise OidcAuthorizationError("OIDC provider does not support private_key_jwt")
        if "none" not in metadata.get(
            "token_endpoint_auth_methods_supported", ["client_secret_basic"]
        ) and client["token_endpoint_auth_method"] == "none":
            raise OidcAuthorizationError("OIDC provider does not support public-client authentication")
        form = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "code_verifier": code_verifier,
            **self._client_auth(client, metadata["token_endpoint"]),
        }
        try:
            token_payload = self._request_json(
                "POST", metadata["token_endpoint"], "token",
                data=form, headers={"Accept": "application/json"},
            )
        except OidcAuthorizationError as exc:
            raise OidcAuthorizationError("OIDC authorization code exchange failed") from exc
        id_token = token_payload.get("id_token")
        return self._verify_id_token(id_token, client_id=client_id, now_epoch=now_epoch)
