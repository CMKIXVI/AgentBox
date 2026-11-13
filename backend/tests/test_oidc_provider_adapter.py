import json
from urllib.parse import parse_qs

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.oidc_authorization_flow import OidcAuthorizationError
from app.oidc_provider_adapter import HttpOidcProviderAdapter


ISSUER = "https://identity.example.test/"
CLIENT_ID = "agentbox-web"


def _registration(**overrides):
    client = {
        "client_id": CLIENT_ID,
        "platform": "web",
        "client_type": "confidential",
        "token_endpoint_auth_method": "private_key_jwt",
        "client_secret_ref": "vault://agentbox/oidc/web-signing-key",
        "redirect_uris": ["https://console.example.test/auth/callback"],
        "response_type": "code",
        "pkce_method": "S256",
    }
    client.update(overrides)
    return {"clients": [client]}


def _metadata(**overrides):
    value = {
        "issuer": ISSUER,
        "authorization_endpoint": "https://identity.example.test/authorize",
        "token_endpoint": "https://identity.example.test/token",
        "jwks_uri": "https://identity.example.test/jwks",
        "response_types_supported": ["code"],
        "code_challenge_methods_supported": ["S256"],
        "scopes_supported": ["openid", "profile"],
        "token_endpoint_auth_methods_supported": ["private_key_jwt", "none"],
    }
    value.update(overrides)
    return value


def _signed_id_token(private_key, *, kid="signing-key", **overrides):
    claims = {
        "iss": ISSUER,
        "sub": "user-42",
        "aud": CLIENT_ID,
        "iat": 1000,
        "exp": 1600,
        "nonce": "nonce-value",
    }
    claims.update(overrides)
    return jwt.encode(
        claims, private_key, algorithm="RS256", headers={"kid": kid, "typ": "JWT"}
    )


def _jwks(public_key, *, kid="signing-key"):
    return {
        "keys": [{
            **json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(public_key)),
            "kid": kid,
            "use": "sig",
            "alg": "RS256",
        }]
    }


class MemoryPrivateKeys:
    def __init__(self, key):
        self.key = key
        self.references = []

    def resolve(self, reference):
        self.references.append(reference)
        return self.key, "client-key-1"


def _make_adapter(handler, *, registration=None, key_resolver=None):
    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        follow_redirects=False,
    )
    return HttpOidcProviderAdapter(
        issuer=ISSUER,
        registration=registration or _registration(),
        private_key_resolver=key_resolver,
        http_client=client,
    )


def test_discovery_and_token_exchange_verify_signature_and_pkce():
    signing_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path.endswith("openid-configuration"):
            return httpx.Response(200, json=_metadata())
        if request.url.path == "/token":
            return httpx.Response(200, json={
                "access_token": "opaque-access-token",
                "token_type": "Bearer",
                "id_token": _signed_id_token(signing_key),
            })
        if request.url.path == "/jwks":
            return httpx.Response(200, json=_jwks(signing_key.public_key()))
        return httpx.Response(404)

    adapter = _make_adapter(handler)
    try:
        assert adapter.authorization_endpoint == "https://identity.example.test/authorize"
        claims = adapter.exchange_and_validate(
            code="one-time-code",
            client_id=CLIENT_ID,
            redirect_uri="https://console.example.test/auth/callback",
            code_verifier="a-long-pkce-verifier",
            now_epoch=1001,
        )
    finally:
        adapter.close()

    assert claims["sub"] == "user-42"
    assert [request.url.path for request in requests] == [
        "/.well-known/openid-configuration", "/token", "/jwks"
    ]
    token_form = parse_qs(requests[1].content.decode())
    assert token_form["grant_type"] == ["authorization_code"]
    assert token_form["code"] == ["one-time-code"]
    assert token_form["code_verifier"] == ["a-long-pkce-verifier"]


def test_private_key_jwt_assertion_is_signed_for_token_endpoint():
    signing_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    client_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    resolver = MemoryPrivateKeys(
        client_key.private_bytes(
            encoding=__import__("cryptography").hazmat.primitives.serialization.Encoding.PEM,
            format=__import__("cryptography").hazmat.primitives.serialization.PrivateFormat.PKCS8,
            encryption_algorithm=__import__("cryptography").hazmat.primitives.serialization.NoEncryption(),
        )
    )
    assertion_headers = {}

    def handler(request):
        if request.url.path.endswith("openid-configuration"):
            return httpx.Response(200, json=_metadata())
        if request.url.path == "/token":
            form = parse_qs(request.content.decode())
            assertion = form["client_assertion"][0]
            assertion_headers.update(jwt.get_unverified_header(assertion))
            claims = jwt.decode(
                assertion, client_key.public_key(), algorithms=["RS256"],
                audience="https://identity.example.test/token",
                issuer=CLIENT_ID, subject=CLIENT_ID,
            )
            assert claims["exp"] - claims["iat"] <= 60
            return httpx.Response(200, json={
                "id_token": _signed_id_token(signing_key)
            })
        if request.url.path == "/jwks":
            return httpx.Response(200, json=_jwks(signing_key.public_key()))
        return httpx.Response(404)

    adapter = _make_adapter(handler, key_resolver=resolver)
    try:
        adapter.exchange_and_validate(
            code="code", client_id=CLIENT_ID,
            redirect_uri="https://console.example.test/auth/callback",
            code_verifier="verifier", now_epoch=1001,
        )
    finally:
        adapter.close()
    assert resolver.references == ["vault://agentbox/oidc/web-signing-key"]
    assert assertion_headers["kid"] == "client-key-1"


@pytest.mark.parametrize("metadata", [
    _metadata(issuer="https://attacker.example/"),
    _metadata(token_endpoint="http://identity.example.test/token"),
    _metadata(code_challenge_methods_supported=["plain"]),
    _metadata(response_types_supported=["token"]),
])
def test_discovery_rejects_untrusted_or_unsupported_metadata(metadata):
    def handler(request):
        return httpx.Response(200, json=metadata)

    adapter = _make_adapter(handler)
    try:
        with pytest.raises(OidcAuthorizationError):
            _ = adapter.authorization_endpoint
    finally:
        adapter.close()


def test_id_token_with_unknown_kid_is_rejected():
    signing_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def handler(request):
        if request.url.path.endswith("openid-configuration"):
            return httpx.Response(200, json=_metadata())
        if request.url.path == "/token":
            return httpx.Response(200, json={
                "id_token": _signed_id_token(signing_key, kid="unknown-key")
            })
        if request.url.path == "/jwks":
            return httpx.Response(200, json=_jwks(signing_key.public_key()))
        return httpx.Response(404)

    adapter = _make_adapter(handler)
    try:
        with pytest.raises(OidcAuthorizationError, match="signing key"):
            adapter.exchange_and_validate(
                code="code", client_id=CLIENT_ID,
                redirect_uri="https://console.example.test/auth/callback",
                code_verifier="verifier", now_epoch=1001,
            )
    finally:
        adapter.close()


def test_hmac_signed_id_token_is_rejected():
    def handler(request):
        if request.url.path.endswith("openid-configuration"):
            return httpx.Response(200, json=_metadata())
        if request.url.path == "/token":
            token = jwt.encode(
                {"iss": ISSUER, "sub": "u", "aud": CLIENT_ID, "iat": 1000, "exp": 1600},
                "shared-secret", algorithm="HS256",
            )
            return httpx.Response(200, json={"id_token": token})
        if request.url.path == "/jwks":
            return httpx.Response(200, json={"keys": []})
        return httpx.Response(404)

    adapter = _make_adapter(handler)
    try:
        with pytest.raises(OidcAuthorizationError, match="unsupported signing algorithm"):
            adapter.exchange_and_validate(
                code="code", client_id=CLIENT_ID,
                redirect_uri="https://console.example.test/auth/callback",
                code_verifier="verifier", now_epoch=1001,
            )
    finally:
        adapter.close()


def test_token_endpoint_redirect_is_rejected():
    def handler(request):
        if request.url.path.endswith("openid-configuration"):
            return httpx.Response(200, json=_metadata())
        return httpx.Response(302, headers={"Location": "https://attacker.example/token"})

    adapter = _make_adapter(handler)
    try:
        with pytest.raises(OidcAuthorizationError, match="exchange failed"):
            adapter.exchange_and_validate(
                code="code", client_id=CLIENT_ID,
                redirect_uri="https://console.example.test/auth/callback",
                code_verifier="verifier", now_epoch=1001,
            )
    finally:
        adapter.close()


def test_public_client_uses_no_client_assertion():
    signing_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_registration = _registration(
        platform="native",
        client_type="public",
        token_endpoint_auth_method="none",
    )
    token_fields = {}

    def handler(request):
        if request.url.path.endswith("openid-configuration"):
            return httpx.Response(200, json=_metadata())
        if request.url.path == "/token":
            token_fields.update(parse_qs(request.content.decode()))
            return httpx.Response(200, json={
                "id_token": _signed_id_token(signing_key)
            })
        if request.url.path == "/jwks":
            return httpx.Response(200, json=_jwks(signing_key.public_key()))
        return httpx.Response(404)

    adapter = _make_adapter(handler, registration=public_registration)
    try:
        adapter.exchange_and_validate(
            code="code", client_id=CLIENT_ID,
            redirect_uri="com.agentbox.app:/callback",
            code_verifier="verifier", now_epoch=1001,
        )
    finally:
        adapter.close()
    assert "client_assertion" not in token_fields
    assert token_fields["client_id"] == [CLIENT_ID]
