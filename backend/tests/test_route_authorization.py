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
    app.state.tenants.create("tenant-1", "Tenant One", "test-bootstrap")
    app.state.tenants.transition("tenant-1", "active", "test-bootstrap")
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
    with pytest.raises(TypeError, match="must be a JSON array"):
        create_app(str(tmp_path / "invalid-shape.sqlite3"))

from datetime import UTC, datetime

from auth_helpers import configure_test_access


def test_policy_tenant_mismatch_denies_access(tmp_path):
    app = configure_test_access(create_app(str(tmp_path / "tenant.sqlite3")))
    app.state.tenants.create("different-tenant", "Different Tenant", "test-bootstrap")
    app.state.tenants.transition("different-tenant", "active", "test-bootstrap")
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



def test_authenticated_unprovisioned_tenant_is_denied_before_policy(tmp_path):
    app = create_app(str(tmp_path / "unprovisioned.sqlite3"))
    app.dependency_overrides[require_authenticated_principal] = lambda: Principal(
        "user-1", "user", "unknown-tenant"
    )
    response = TestClient(app).get("/v1/agents/research.summarizer/versions")
    assert response.status_code == 403
    assert response.json()["detail"]["reason"] == "tenant_not_provisioned"


def test_pending_tenant_cannot_access_protected_routes(tmp_path):
    app = create_app(str(tmp_path / "pending.sqlite3"))
    app.state.tenants.create("pending-tenant", "Pending Tenant", "test-bootstrap")
    app.dependency_overrides[require_authenticated_principal] = lambda: Principal(
        "user-1", "user", "pending-tenant"
    )
    response = TestClient(app).get("/v1/agents/research.summarizer/versions")
    assert response.status_code == 403
    assert response.json()["detail"]["reason"] == "tenant_inactive"


@pytest.mark.parametrize("terminal_or_blocked", ["suspended", "decommissioned"])
def test_suspended_or_decommissioned_tenant_cannot_access_protected_routes(
    tmp_path, terminal_or_blocked
):
    app = create_app(str(tmp_path / f"{terminal_or_blocked}.sqlite3"))
    app.state.tenants.create("blocked-tenant", "Blocked Tenant", "test-bootstrap")
    app.state.tenants.transition("blocked-tenant", "active", "test-bootstrap")
    app.state.tenants.transition("blocked-tenant", terminal_or_blocked, "test-bootstrap")
    app.dependency_overrides[require_authenticated_principal] = lambda: Principal(
        "user-1", "user", "blocked-tenant"
    )
    response = TestClient(app).get("/v1/agents/research.summarizer/versions")
    assert response.status_code == 403
    assert response.json()["detail"]["reason"] == "tenant_inactive"


def test_active_tenant_passes_lifecycle_gate_then_requires_policy(tmp_path):
    app = create_app(str(tmp_path / "active-no-grant.sqlite3"))
    app.state.tenants.create("active-tenant", "Active Tenant", "test-bootstrap")
    app.state.tenants.transition("active-tenant", "active", "test-bootstrap")
    app.dependency_overrides[require_authenticated_principal] = lambda: Principal(
        "user-1", "user", "active-tenant"
    )
    response = TestClient(app).get("/v1/agents/research.summarizer/versions")
    assert response.status_code == 403
    assert response.json()["detail"]["reason"] == "no_matching_allow_policy"



def test_tenant_suspension_takes_effect_on_next_request(tmp_path):
    app = configure_test_access(create_app(str(tmp_path / "suspension-live.sqlite3")))
    client = TestClient(app)
    first = client.get("/v1/agents/research.summarizer/versions")
    assert first.status_code == 200
    app.state.tenants.transition("test-tenant", "suspended", "test-bootstrap")
    second = client.get("/v1/agents/research.summarizer/versions")
    assert second.status_code == 403
    assert second.json()["detail"]["reason"] == "tenant_inactive"


def test_public_validation_does_not_require_or_create_tenant(tmp_path):
    app = create_app(str(tmp_path / "public-validation.sqlite3"))
    response = TestClient(app).post("/v1/agents/validate", json={"manifest": {}})
    assert response.status_code == 200
    assert app.state.tenants.list() == []



def test_tenant_administration_is_not_exposed_as_public_http_api(tmp_path):
    schema = TestClient(create_app(str(tmp_path / "no-tenant-admin-api.sqlite3"))).get(
        "/openapi.json"
    ).json()
    paths = schema["paths"]
    assert not any(path.startswith("/v1/tenants") for path in paths)
    assert not any("tenant" in path and path != "/health" for path in paths)
