import hashlib
from urllib.parse import parse_qs, urlsplit

import pytest

from app.oidc_authorization_flow import (
    OidcAuthorizationError,
    OidcAuthorizationFlow,
)
from app.oidc_callback_store_sqlite import SQLiteOidcCallbackTransactionStore


class MemorySecrets:
    def __init__(self):
        self.values = {}

    def put(self, reference, secret):
        self.values[reference] = secret

    def get(self, reference):
        return self.values[reference]

    def delete(self, reference):
        self.values.pop(reference, None)


class FakeExchanger:
    def __init__(self, claims):
        self.claims = claims
        self.calls = []

    def exchange_and_validate(self, **kwargs):
        self.calls.append(kwargs)
        return self.claims


def registration():
    return {
        "schema_version": "1.0",
        "protocol": "oidc",
        "clients": [{
            "client_id": "agentbox-web",
            "platform": "web",
            "client_type": "confidential",
            "token_endpoint_auth_method": "private_key_jwt",
            "client_secret_ref": "vault://agentbox/oidc/web-client",
            "redirect_uris": ["https://console.example.test/auth/callback"],
            "post_logout_redirect_uris": ["https://console.example.test/"],
            "response_type": "code",
            "pkce_method": "S256",
        }],
    }


def make_flow(tmp_path, exchanger, secrets_store=None):
    return OidcAuthorizationFlow(
        registration=registration(),
        issuer="https://identity.example.test/",
        authorization_endpoint="https://identity.example.test/authorize",
        tenant_claim="tenant_id",
        transactions=SQLiteOidcCallbackTransactionStore(tmp_path / "oidc.sqlite3"),
        secrets_store=secrets_store or MemorySecrets(),
        exchanger=exchanger,
    )


def valid_claims(nonce, **overrides):
    claims = {
        "iss": "https://identity.example.test/",
        "aud": "agentbox-web",
        "sub": "user-42",
        "tenant_id": "tenant-7",
        "iat": 1000,
        "exp": 1600,
        "nonce": nonce,
    }
    claims.update(overrides)
    return claims


def start_flow(flow, monkeypatch):
    tokens = iter(["transaction-id-123456789", "state-value-12345678901234567890",
                   "nonce-value-12345678901234567890", "verifier-value-12345678901234567890"])
    monkeypatch.setattr("app.oidc_authorization_flow.secrets.token_urlsafe", lambda _: next(tokens))
    started = flow.start(
        client_id="agentbox-web",
        redirect_uri="https://console.example.test/auth/callback",
        now_epoch=1000,
    )
    params = parse_qs(urlsplit(started.authorization_url).query)
    return params["state"][0], params["nonce"][0], started


def test_start_builds_code_flow_with_s256_and_persists_only_hashes(tmp_path, monkeypatch):
    secrets_store = MemorySecrets()
    flow = make_flow(tmp_path, FakeExchanger({}), secrets_store)
    state, nonce, started = start_flow(flow, monkeypatch)
    params = parse_qs(urlsplit(started.authorization_url).query)
    assert params["response_type"] == ["code"]
    assert params["code_challenge_method"] == ["S256"]
    assert params["state"] == [state]
    assert params["nonce"] == [nonce]
    assert params["scope"] == ["openid profile email"]
    assert started.expires_at_epoch == 1300
    assert len(secrets_store.values) == 1
    verifier = next(iter(secrets_store.values.values()))
    assert len(verifier) >= 43
    assert state not in str(secrets_store.values)
    assert nonce not in str(secrets_store.values)


def test_start_rejects_unregistered_redirect(tmp_path, monkeypatch):
    flow = make_flow(tmp_path, FakeExchanger({}))
    with pytest.raises(OidcAuthorizationError, match="Unknown OIDC client"):
        flow.start(
            client_id="unknown-client",
            redirect_uri="https://attacker.example/callback",
            now_epoch=1000,
        )
    assert not list(tmp_path.glob("*.sqlite3-wal"))


def test_complete_validates_identity_and_deletes_verifier(tmp_path, monkeypatch):
    nonce = "nonce-value-12345678901234567890"
    secrets_store = MemorySecrets()
    exchanger = FakeExchanger(valid_claims(nonce))
    flow = make_flow(tmp_path, exchanger, secrets_store)
    state, _, _ = start_flow(flow, monkeypatch)

    identity = flow.complete(
        state=state,
        code="authorization-code",
        client_id="agentbox-web",
        redirect_uri="https://console.example.test/auth/callback",
        now_epoch=1001,
    )
    assert identity.subject_id == "user-42"
    assert identity.tenant_id == "tenant-7"
    assert identity.client_id == "agentbox-web"
    assert len(exchanger.calls) == 1
    assert exchanger.calls[0]["code"] == "authorization-code"
    assert exchanger.calls[0]["code_verifier"].startswith("verifier-value")
    assert secrets_store.values == {}


def test_callback_replay_is_rejected_after_success(tmp_path, monkeypatch):
    nonce = "nonce-value-12345678901234567890"
    flow = make_flow(tmp_path, FakeExchanger(valid_claims(nonce)))
    state, _, _ = start_flow(flow, monkeypatch)
    flow.complete(
        state=state, code="authorization-code", client_id="agentbox-web",
        redirect_uri="https://console.example.test/auth/callback", now_epoch=1001,
    )
    with pytest.raises(OidcAuthorizationError, match="Invalid or expired"):
        flow.complete(
            state=state, code="authorization-code", client_id="agentbox-web",
            redirect_uri="https://console.example.test/auth/callback", now_epoch=1001,
        )


def test_wrong_nonce_fails_and_verifier_is_deleted(tmp_path, monkeypatch):
    secrets_store = MemorySecrets()
    flow = make_flow(tmp_path, FakeExchanger(valid_claims("attacker-nonce")), secrets_store)
    state, _, _ = start_flow(flow, monkeypatch)
    with pytest.raises(OidcAuthorizationError, match="nonce"):
        flow.complete(
            state=state, code="authorization-code", client_id="agentbox-web",
            redirect_uri="https://console.example.test/auth/callback", now_epoch=1001,
        )
    assert secrets_store.values == {}


def test_wrong_callback_client_consumes_transaction_and_fails_closed(tmp_path, monkeypatch):
    flow = make_flow(tmp_path, FakeExchanger({}))
    state, _, _ = start_flow(flow, monkeypatch)
    with pytest.raises(OidcAuthorizationError, match="does not match"):
        flow.complete(
            state=state, code="authorization-code", client_id="other-client",
            redirect_uri="https://console.example.test/auth/callback", now_epoch=1001,
        )
    with pytest.raises(OidcAuthorizationError, match="Invalid or expired"):
        flow.complete(
            state=state, code="authorization-code", client_id="agentbox-web",
            redirect_uri="https://console.example.test/auth/callback", now_epoch=1001,
        )


def test_wrong_issuer_audience_and_expiry_are_rejected(tmp_path, monkeypatch):
    cases = [
        {"iss": "https://attacker.example/"},
        {"aud": "other-client"},
        {"exp": 1001},
        {"aud": ["agentbox-web", "other"], "azp": "other"},
    ]
    for index, overrides in enumerate(cases):
        case_dir = tmp_path / str(index)
        case_dir.mkdir()
        nonce = "nonce-value-12345678901234567890"
        flow = make_flow(case_dir, FakeExchanger(valid_claims(nonce, **overrides)))
        tokens = iter([f"transaction-{index}-123456", f"state-{index}-value-123456789",
                       nonce, f"verifier-{index}-value-12345678901234567890"])
        monkeypatch.setattr("app.oidc_authorization_flow.secrets.token_urlsafe", lambda _, t=tokens: next(t))
        started = flow.start(
            client_id="agentbox-web",
            redirect_uri="https://console.example.test/auth/callback",
            now_epoch=1000,
        )
        state = parse_qs(urlsplit(started.authorization_url).query)["state"][0]
        with pytest.raises(OidcAuthorizationError):
            flow.complete(
                state=state, code="authorization-code", client_id="agentbox-web",
                redirect_uri="https://console.example.test/auth/callback", now_epoch=1001,
            )


def test_expired_state_is_rejected(tmp_path, monkeypatch):
    flow = make_flow(tmp_path, FakeExchanger({}))
    state, _, _ = start_flow(flow, monkeypatch)
    with pytest.raises(OidcAuthorizationError, match="Invalid or expired"):
        flow.complete(
            state=state, code="authorization-code", client_id="agentbox-web",
            redirect_uri="https://console.example.test/auth/callback", now_epoch=1300,
        )


def test_invalid_authorization_endpoint_query_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="trusted HTTPS"):
        OidcAuthorizationFlow(
            registration=registration(),
            issuer="https://identity.example.test/",
            authorization_endpoint="https://identity.example.test/authorize?client_id=evil",
            tenant_claim="tenant_id",
            transactions=SQLiteOidcCallbackTransactionStore(tmp_path / "oidc.sqlite3"),
            secrets_store=MemorySecrets(),
            exchanger=FakeExchanger({}),
        )


def test_state_hash_is_not_the_raw_state_in_storage(tmp_path, monkeypatch):
    flow = make_flow(tmp_path, FakeExchanger({}))
    state, _, _ = start_flow(flow, monkeypatch)
    stored = flow._transactions.consume_by_state_hash(
        hashlib.sha256(state.encode()).hexdigest(), now_epoch=1001
    )
    assert stored is not None
    assert stored.state_hash == hashlib.sha256(state.encode()).hexdigest()
    assert stored.state_hash != state
