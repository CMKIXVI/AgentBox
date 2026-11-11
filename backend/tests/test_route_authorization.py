import json

import pytest
from fastapi.testclient import TestClient

from app.authentication import require_authenticated_principal
from app.main import create_app
from app.principal import Principal


def test_protected_write_fails_closed_without_oidc_configuration(tmp_path, monkeypatch):
    for name in (
        "AGENTBOX_OIDC_ISSUER",
        "AGENTBOX_OIDC_AUDIENCE",
        "AGENTBOX_OIDC_JWKS_URI",
        "AGENTBOX_OIDC_TENANT_CLAIM",
    ):
        monkeypatch.delenv(name, raising=False)
    client = TestClient(create_app(str(tmp_path / "auth.sqlite3")))
    response = client.post("/v1/agents", json={"manifest": {"agent_id": "x"}})
    assert response.status_code == 503


def test_caller_identity_headers_do_not_bypass_authentication(tmp_path, monkeypatch):
    for name in (
        "AGENTBOX_OIDC_ISSUER",
        "AGENTBOX_OIDC_AUDIENCE",
        "AGENTBOX_OIDC_JWKS_URI",
        "AGENTBOX_OIDC_TENANT_CLAIM",
    ):
        monkeypatch.delenv(name, raising=False)
    client = TestClient(create_app(str(tmp_path / "headers.sqlite3")))
    response = client.get(
        "/v1/agents/research.summarizer/versions",
        headers={
            "X-Principal-Id": "test-user",
            "X-Tenant-Id": "test-tenant",
            "X-Principal-Type": "user",
        },
    )
    assert response.status_code == 503


def test_authenticated_principal_without_policy_is_denied(tmp_path):
    app = create_app(str(tmp_path / "policy.sqlite3"))
    app.dependency_overrides[require_authenticated_principal] = lambda: Principal(
        "user-1", "user", "tenant-1"
    )
    client = TestClient(app)
    response = client.get("/v1/agents/research.summarizer/versions")
    assert response.status_code == 403
    assert response.json()["detail"]["reason"] == "no_matching_allow_policy"


def test_manifest_validation_remains_public_and_side_effect_free(tmp_path):
    client = TestClient(create_app(str(tmp_path / "public.sqlite3")))
    response = client.post("/v1/agents/validate", json={"manifest": {}})
    assert response.status_code == 200
    assert response.json()["valid"] is False


def test_invalid_policy_file_prevents_app_startup(tmp_path, monkeypatch):
    path = tmp_path / "policies.json"
    path.write_text(json.dumps([{"policy_id": "bad"}]), encoding="utf-8")
    monkeypatch.setenv("AGENTBOX_AUTHORIZATION_POLICIES_PATH", str(path))
    with pytest.raises(RuntimeError, match="Invalid AgentBox authorization policy"):
        create_app(str(tmp_path / "invalid.sqlite3"))


def test_policy_file_must_be_an_array(tmp_path, monkeypatch):
    path = tmp_path / "policies.json"
    path.write_text(json.dumps({"policy_id": "not-an-array"}), encoding="utf-8")
    monkeypatch.setenv("AGENTBOX_AUTHORIZATION_POLICIES_PATH", str(path))
    with pytest.raises(RuntimeError, match="must be a JSON array"):
        create_app(str(tmp_path / "invalid-shape.sqlite3"))

from datetime import UTC, datetime

from auth_helpers import configure_test_access


def test_policy_tenant_mismatch_denies_access(tmp_path):
    app = configure_test_access(create_app(str(tmp_path / "tenant.sqlite3")))
    app.dependency_overrides[require_authenticated_principal] = lambda: Principal(
        "test-user", "user", "different-tenant"
    )
    response = TestClient(app).get("/v1/agents/research.summarizer/versions")
    assert response.status_code == 403
    assert response.json()["detail"]["reason"] == "no_matching_allow_policy"


def test_explicit_deny_policy_blocks_previously_allowed_route(tmp_path):
    app = configure_test_access(create_app(str(tmp_path / "deny.sqlite3")))
    app.state.authorization_policies.append(
        {
            "schema_version": "1.0.0",
            "policy_id": "test.explicit.deny",
            "version": "1.0.0",
            "active": True,
            "effect": "deny",
            "capability_id": "agent.registry",
            "principal_scope": "user",
            "principal_ids": ["test-user"],
            "tenant_ids": ["test-tenant"],
            "actions": ["agent.read"],
            "resource_ids": ["research.summarizer"],
            "created_at": datetime(2026, 11, 12, tzinfo=UTC).isoformat(),
        }
    )
    response = TestClient(app).get("/v1/agents/research.summarizer/versions")
    assert response.status_code == 403
    assert response.json()["detail"]["reason"] == "explicit_deny"
