from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient

from app.authentication import (
    AuthenticationError,
    OIDCAuthenticationConfig,
    OIDCAuthenticator,
    OIDCSigningKeyResolver,
)
from app.main import create_app
from mock_oidc_provider import MockOIDCError, MockOIDCProvider


@pytest.fixture
def provider() -> MockOIDCProvider:
    return MockOIDCProvider()


def begin_login(provider: MockOIDCProvider, *, state: str = "state-123", nonce: str = "nonce-456"):
    verifier = "a-strong-test-code-verifier-with-enough-entropy"
    import base64
    import hashlib

    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
    challenge = challenge.rstrip(b"=").decode("ascii")
    code = provider.authorize(
        client_id=provider.client_id,
        redirect_uri=provider.redirect_uri,
        code_challenge=challenge,
        state=state,
        nonce=nonce,
    )
    return code, verifier, state, nonce


def test_mock_oidc_authorization_code_pkce_nonce_and_refresh(provider):
    code, verifier, state, nonce = begin_login(provider)
    provider.validate_callback_state(state, state)
    tokens = provider.exchange_code(
        code=code,
        redirect_uri=provider.redirect_uri,
        code_verifier=verifier,
        tenant_id="tenant-alpha",
    )

    id_claims = provider.validate_id_token(
        tokens["id_token"], client_id=provider.client_id, expected_nonce=nonce
    )
    assert id_claims["sub"] == "mock-user-1"

    access_claims = jwt.decode(
        tokens["access_token"],
        provider.resolve(tokens["access_token"]),
        algorithms=["RS256"],
        issuer=provider.issuer,
        audience=provider.audience,
    )
    assert access_claims["tenant_id"] == "tenant-alpha"

    renewed = provider.refresh(tokens["refresh_token"])
    assert renewed["refresh_token"] != tokens["refresh_token"]
    with pytest.raises(MockOIDCError, match="invalid|expired|revoked"):
        provider.refresh(tokens["refresh_token"])

    provider.logout(renewed["refresh_token"])
    with pytest.raises(MockOIDCError):
        provider.refresh(renewed["refresh_token"])


def test_mock_oidc_rejects_pkce_state_nonce_and_redirect_tampering(provider):
    code, verifier, state, nonce = begin_login(provider)
    with pytest.raises(MockOIDCError, match="state"):
        provider.validate_callback_state(state, "attacker-state")

    with pytest.raises(MockOIDCError, match="PKCE"):
        provider.exchange_code(
            code=code,
            redirect_uri=provider.redirect_uri,
            code_verifier="wrong-verifier",
            tenant_id="tenant-alpha",
        )
    with pytest.raises(MockOIDCError, match="invalid|already used"):
        provider.exchange_code(
            code=code,
            redirect_uri=provider.redirect_uri,
            code_verifier=verifier,
            tenant_id="tenant-alpha",
        )

    code, verifier, _, _ = begin_login(provider, state="state-2", nonce="nonce-2")
    tokens = provider.exchange_code(
        code=code,
        redirect_uri=provider.redirect_uri,
        code_verifier=verifier,
        tenant_id="tenant-alpha",
    )
    with pytest.raises(MockOIDCError, match="nonce"):
        provider.validate_id_token(
            tokens["id_token"], client_id=provider.client_id, expected_nonce="wrong-nonce"
        )

    with pytest.raises(MockOIDCError, match="redirect"):
        provider.authorize(
            client_id=provider.client_id,
            redirect_uri="https://attacker.test/callback",
            code_challenge="challenge",
            state="state",
            nonce="nonce",
        )


def test_mock_oidc_discovery_and_jwks_are_well_formed(provider):
    discovery = provider.discovery_document()
    jwks = provider.jwks_document()
    assert discovery["issuer"] == provider.issuer
    assert discovery["jwks_uri"] == provider.jwks_uri
    assert discovery["code_challenge_methods_supported"] == ["S256"]
    assert jwks["keys"][0]["kid"] == "agentbox-mock-key-1"
    assert jwks["keys"][0]["kty"] == "RSA"


def test_expired_mock_access_token_is_rejected(provider):
    expired = provider._sign({
        "iss": provider.issuer,
        "aud": provider.audience,
        "sub": "mock-user",
        "tenant_id": "tenant-alpha",
        "iat": int((datetime.now(UTC) - timedelta(minutes=5)).timestamp()),
        "exp": int((datetime.now(UTC) - timedelta(minutes=1)).timestamp()),
    })
    config = OIDCAuthenticationConfig(
        issuer=provider.issuer,
        audience=provider.audience,
        jwks_uri=provider.jwks_uri,
        tenant_claim="tenant_id",
    )
    with pytest.raises(AuthenticationError):
        OIDCAuthenticator(config, provider).authenticate(expired)


def configured_api(tmp_path, monkeypatch, provider):
    monkeypatch.setenv("AGENTBOX_OIDC_ISSUER", provider.issuer)
    monkeypatch.setenv("AGENTBOX_OIDC_AUDIENCE", provider.audience)
    monkeypatch.setenv("AGENTBOX_OIDC_JWKS_URI", provider.jwks_uri)
    monkeypatch.setenv("AGENTBOX_OIDC_TENANT_CLAIM", "tenant_id")
    monkeypatch.setattr(OIDCSigningKeyResolver, "resolve", lambda self, token: provider.resolve(token))

    app = create_app(str(tmp_path / "oidc-e2e.sqlite3"))
    for tenant_id in ("tenant-alpha", "tenant-beta"):
        app.state.tenants.create(tenant_id, tenant_id, "test-bootstrap")
        app.state.tenants.transition(tenant_id, "active", "test-bootstrap")

    app.state.authorization_policies = [{
        "schema_version": "1.0.0",
        "policy_id": "mock-oidc.agent-read.alpha",
        "version": "1.0.0",
        "active": True,
        "effect": "allow",
        "capability_id": "agent.registry",
        "principal_scope": "user",
        "principal_ids": ["mock-user-1"],
        "tenant_ids": ["tenant-alpha"],
        "actions": ["agent.read"],
        "resource_ids": ["research.summarizer"],
        "created_at": "2026-11-14T00:00:00+00:00",
    }]
    return app


def access_token(provider, tenant_id="tenant-alpha", subject="mock-user-1", expires_in=300):
    now = int(datetime.now(UTC).timestamp())
    return provider._sign({
        "iss": provider.issuer,
        "aud": provider.audience,
        "sub": subject,
        "tenant_id": tenant_id,
        "iat": now,
        "exp": now + expires_in,
    })


def test_real_oidc_dependency_protects_api_and_ignores_forged_tenant_header(
    tmp_path, monkeypatch, provider
):
    app = configured_api(tmp_path, monkeypatch, provider)
    client = TestClient(app)
    token = access_token(provider)

    response = client.get(
        "/v1/agents/research.summarizer/versions",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-beta"},
    )
    assert response.status_code == 200

    unauthenticated = client.get(
        "/v1/agents/research.summarizer/versions",
        headers={"X-Principal-Id": "mock-user-1", "X-Tenant-ID": "tenant-alpha"},
    )
    assert unauthenticated.status_code == 401


def test_valid_token_cannot_cross_tenant_policy_boundary(
    tmp_path, monkeypatch, provider
):
    app = configured_api(tmp_path, monkeypatch, provider)
    client = TestClient(app)
    token = access_token(provider, tenant_id="tenant-beta")

    response = client.get(
        "/v1/agents/research.summarizer/versions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["reason"] == "no_matching_allow_policy"


def test_expired_token_cannot_access_protected_api(tmp_path, monkeypatch, provider):
    app = configured_api(tmp_path, monkeypatch, provider)
    client = TestClient(app)
    token = access_token(provider, expires_in=-60)

    response = client.get(
        "/v1/agents/research.summarizer/versions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401
