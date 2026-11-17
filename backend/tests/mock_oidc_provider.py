"""In-memory OIDC provider used only by authentication integration tests.

It models discovery/JWKS, authorization-code + PKCE, state/nonce binding,
refresh-token rotation, and revocation without network calls or production
credentials. It is deliberately not a deployable identity provider.
"""
from __future__ import annotations

import base64
import hashlib
import secrets
import time
from dataclasses import dataclass
from typing import Any

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa


class MockOIDCError(ValueError):
    """The simulated OIDC protocol rejected a request."""


@dataclass
class AuthorizationGrant:
    client_id: str
    redirect_uri: str
    code_challenge: str
    state: str
    nonce: str


class MockOIDCProvider:
    issuer = "https://mock.identity.agentbox.test"
    audience = "agentbox-api"
    jwks_uri = issuer + "/.well-known/jwks.json"
    token_endpoint = issuer + "/oauth/token"
    authorization_endpoint = issuer + "/oauth/authorize"
    client_id = "agentbox-test-client"
    redirect_uri = "https://agentbox.test/api/auth/callback/agentbox-oidc"

    def __init__(self) -> None:
        self._private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self._public_key = self._private_key.public_key()
        self._kid = "agentbox-mock-key-1"
        self._codes: dict[str, AuthorizationGrant] = {}
        self._refresh_tokens: dict[str, tuple[str, str]] = {}
        self._revoked_refresh_tokens: set[str] = set()

    @staticmethod
    def _b64url(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")

    def discovery_document(self) -> dict[str, Any]:
        return {
            "issuer": self.issuer,
            "authorization_endpoint": self.authorization_endpoint,
            "token_endpoint": self.token_endpoint,
            "jwks_uri": self.jwks_uri,
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "subject_types_supported": ["public"],
            "id_token_signing_alg_values_supported": ["RS256"],
            "token_endpoint_auth_methods_supported": ["client_secret_basic", "none"],
            "code_challenge_methods_supported": ["S256"],
            "scopes_supported": ["openid", "profile", "email", "offline_access"],
        }

    def jwks_document(self) -> dict[str, Any]:
        numbers = self._public_key.public_numbers()
        return {
            "keys": [{
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "kid": self._kid,
                "n": self._b64url(numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, "big")),
                "e": self._b64url(numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, "big")),
            }]
        }

    def resolve(self, token: str) -> Any:
        header = jwt.get_unverified_header(token)
        if header.get("kid") != self._kid or header.get("alg") != "RS256":
            raise MockOIDCError("Unknown signing key or algorithm")
        return self._public_key

    def authorize(
        self,
        *,
        client_id: str,
        redirect_uri: str,
        code_challenge: str,
        state: str,
        nonce: str,
        code_challenge_method: str = "S256",
    ) -> str:
        if client_id != self.client_id or redirect_uri != self.redirect_uri:
            raise MockOIDCError("Unregistered client or redirect URI")
        if code_challenge_method != "S256" or not all((code_challenge, state, nonce)):
            raise MockOIDCError("PKCE S256, state, and nonce are required")
        code = secrets.token_urlsafe(32)
        self._codes[code] = AuthorizationGrant(
            client_id, redirect_uri, code_challenge, state, nonce
        )
        return code

    @staticmethod
    def validate_callback_state(expected: str, received: str) -> None:
        if not expected or not secrets.compare_digest(expected, received):
            raise MockOIDCError("OAuth state validation failed")

    def exchange_code(
        self, *, code: str, redirect_uri: str, code_verifier: str, tenant_id: str,
        subject: str = "mock-user-1", expires_in: int = 300,
    ) -> dict[str, Any]:
        grant = self._codes.pop(code, None)
        if grant is None:
            raise MockOIDCError("Authorization code is invalid or already used")
        challenge = self._b64url(hashlib.sha256(code_verifier.encode()).digest())
        if redirect_uri != grant.redirect_uri or not secrets.compare_digest(
            challenge, grant.code_challenge
        ):
            raise MockOIDCError("Redirect URI or PKCE verifier mismatch")

        now = int(time.time())
        access_token = self._sign({
            "iss": self.issuer,
            "aud": self.audience,
            "sub": subject,
            "tenant_id": tenant_id,
            "iat": now,
            "exp": now + expires_in,
            "jti": secrets.token_urlsafe(16),
        })
        id_token = self._sign({
            "iss": self.issuer,
            "aud": grant.client_id,
            "sub": subject,
            "iat": now,
            "exp": now + expires_in,
            "nonce": grant.nonce,
        })
        refresh_token = secrets.token_urlsafe(48)
        self._refresh_tokens[refresh_token] = (subject, tenant_id)
        return {
            "token_type": "Bearer",
            "access_token": access_token,
            "id_token": id_token,
            "refresh_token": refresh_token,
            "expires_in": expires_in,
        }

    def _sign(self, claims: dict[str, Any]) -> str:
        return jwt.encode(
            claims,
            self._private_key,
            algorithm="RS256",
            headers={"kid": self._kid, "typ": "JWT"},
        )

    def validate_id_token(self, token: str, *, client_id: str, expected_nonce: str) -> dict[str, Any]:
        claims = jwt.decode(
            token,
            self._public_key,
            algorithms=["RS256"],
            issuer=self.issuer,
            audience=client_id,
            options={"require": ["exp", "iat", "sub", "iss", "aud", "nonce"]},
        )
        if not secrets.compare_digest(str(claims.get("nonce", "")), expected_nonce):
            raise MockOIDCError("OIDC nonce validation failed")
        return claims

    def refresh(self, refresh_token: str, *, expires_in: int = 300) -> dict[str, Any]:
        identity = self._refresh_tokens.pop(refresh_token, None)
        if identity is None or refresh_token in self._revoked_refresh_tokens:
            raise MockOIDCError("Refresh token is invalid, expired, or revoked")
        subject, tenant_id = identity
        now = int(time.time())
        replacement = secrets.token_urlsafe(48)
        self._refresh_tokens[replacement] = identity
        return {
            "token_type": "Bearer",
            "access_token": self._sign({
                "iss": self.issuer,
                "aud": self.audience,
                "sub": subject,
                "tenant_id": tenant_id,
                "iat": now,
                "exp": now + expires_in,
                "jti": secrets.token_urlsafe(16),
            }),
            "refresh_token": replacement,
            "expires_in": expires_in,
        }

    def revoke_refresh_token(self, refresh_token: str) -> None:
        self._refresh_tokens.pop(refresh_token, None)
        self._revoked_refresh_tokens.add(refresh_token)

    def logout(self, refresh_token: str) -> None:
        """Simulate provider logout by revoking the active refresh credential."""
        self.revoke_refresh_token(refresh_token)
