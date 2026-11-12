from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.enterprise_context import (
    ContextConflictError,
    ContextNotFoundError,
    ContextValidationError,
    EnterpriseContextService,
)
from app.main import create_app
from app.tenant_registry import TenantRegistry
from auth_helpers import configure_test_access

NOW = datetime.now(UTC).isoformat()


def entity(entity_id="app.alpha", entity_type="application", name="Alpha Application"):
    return {
        "entity_id": entity_id,
        "entity_type": entity_type,
        "name": name,
        "description": "Discovered application metadata",
        "attributes": {"environment": "production", "owner": "platform"},
        "assertion_class": "observed_fact",
        "confidence": 1.0,
    }


def relationship(relationship_id="rel.alpha", source="app.alpha", target="db.alpha"):
    return {
        "relationship_id": relationship_id,
        "relationship_type": "uses_database",
        "source_entity_id": source,
        "source_version": 1,
        "target_entity_id": target,
        "target_version": 1,
        "attributes": {"dependency": "read_write"},
        "assertion_class": "inferred",
        "confidence": 0.9,
    }


def evidence(evidence_id="evidence.alpha"):
    return {
        "evidence_id": evidence_id,
        "entity_id": "app.alpha",
        "entity_version": 1,
        "source_kind": "database_metadata",
        "source_ref": "postgres://catalog/public/applications",
        "source_hash": hashlib.sha256(b"catalog snapshot").hexdigest(),
        "observed_at": NOW,
        "confidence": 1.0,
        "validation_status": "validated",
        "metadata": {"connector": "read-only-catalog"},
    }


def create_tenant(path: Path, tenant_id: str):
    registry = TenantRegistry(path)
    registry.create(tenant_id, tenant_id, "test-operator")
    registry.transition(tenant_id, "active", "test-operator")
    return registry


def test_entity_versions_are_immutable_and_latest_query_is_deterministic(tmp_path):
    path = tmp_path / "context.sqlite3"
    create_tenant(path, "tenant-alpha")
    service = EnterpriseContextService(path)
    first = service.create_entity(entity(), "tenant-alpha", "test-user")
    changed = entity(name="Alpha Enterprise Application")
    changed["attributes"]["environment"] = "staging"
    second = service.version_entity(changed, "tenant-alpha", "test-user", 1)

    assert first["version"] == 1
    assert second["version"] == 2
    assert service.get_entity("app.alpha", "tenant-alpha", 1)["name"] == "Alpha Application"
    assert service.get_entity("app.alpha", "tenant-alpha")["name"] == "Alpha Enterprise Application"
    assert service.query_entities("tenant-alpha")[0]["version"] == 2


def test_entity_creation_conflict_and_stale_version_are_rejected(tmp_path):
    path = tmp_path / "conflicts.sqlite3"
    create_tenant(path, "tenant-alpha")
    service = EnterpriseContextService(path)
    service.create_entity(entity(), "tenant-alpha", "test-user")
    with pytest.raises(ContextConflictError):
        service.create_entity(entity(name="Different"), "tenant-alpha", "test-user")
    with pytest.raises(ContextConflictError, match="version changed"):
        service.version_entity(entity(name="Stale update"), "tenant-alpha", "test-user", 0)


def test_entity_reads_and_queries_are_tenant_scoped(tmp_path):
    path = tmp_path / "isolation.sqlite3"
    create_tenant(path, "tenant-alpha")
    create_tenant(path, "tenant-beta")
    service = EnterpriseContextService(path)
    service.create_entity(entity(), "tenant-alpha", "alpha-user")
    assert service.query_entities("tenant-beta") == []
    with pytest.raises(ContextNotFoundError):
        service.get_entity("app.alpha", "tenant-beta")


def test_relationship_requires_both_endpoints_in_the_same_tenant(tmp_path):
    path = tmp_path / "relationship.sqlite3"
    create_tenant(path, "tenant-alpha")
    create_tenant(path, "tenant-beta")
    service = EnterpriseContextService(path)
    service.create_entity(entity(), "tenant-alpha", "alpha-user")
    service.create_entity(
        entity("db.alpha", "database", "Alpha Database"), "tenant-alpha", "alpha-user"
    )
    service.create_entity(
        entity("db.beta", "database", "Beta Database"), "tenant-beta", "beta-user"
    )
    created = service.create_relationship(relationship(), "tenant-alpha", "alpha-user")
    assert created["relationship_type"] == "uses_database"
    with pytest.raises(ContextNotFoundError, match="does not exist in this tenant"):
        service.create_relationship(
            relationship("rel.cross", target="db.beta"), "tenant-alpha", "alpha-user"
        )
    assert len(service.query_relationships("tenant-alpha", "app.alpha")) == 1
    assert service.query_relationships("tenant-beta") == []


def test_evidence_is_tenant_scoped_and_context_events_are_append_only(tmp_path):
    path = tmp_path / "evidence.sqlite3"
    create_tenant(path, "tenant-alpha")
    service = EnterpriseContextService(path)
    service.create_entity(entity(), "tenant-alpha", "test-user")
    recorded = service.create_evidence(evidence(), "tenant-alpha", "test-user")
    assert recorded["validation_status"] == "validated"
    assert service.query_evidence("app.alpha", "tenant-alpha")[0]["evidence_id"] == "evidence.alpha"
    assert service.query_evidence("app.alpha", "tenant-beta") == []
    events = service.query_events("tenant-alpha")
    assert [item["event_type"] for item in events] == [
        "context.entity.created", "context.evidence.recorded"
    ]
    with sqlite3.connect(path) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "DELETE FROM context_events WHERE tenant_id=? AND event_id=?",
                ("tenant-alpha", events[0]["event_id"]),
            )


def test_evidence_rejects_unknown_entity_version_and_invalid_source_hash(tmp_path):
    path = tmp_path / "evidence-invalid.sqlite3"
    create_tenant(path, "tenant-alpha")
    service = EnterpriseContextService(path)
    with pytest.raises(ContextNotFoundError):
        service.create_evidence(evidence(), "tenant-alpha", "test-user")
    service.create_entity(entity(), "tenant-alpha", "test-user")
    invalid = evidence()
    invalid["source_hash"] = "not-a-hash"
    with pytest.raises(ContextValidationError):
        service.create_evidence(invalid, "tenant-alpha", "test-user")


def test_context_metadata_is_bounded_and_non_finite_values_are_rejected(tmp_path):
    path = tmp_path / "bounds.sqlite3"
    create_tenant(path, "tenant-alpha")
    service = EnterpriseContextService(path)
    oversized = entity()
    oversized["attributes"] = {"large": "x" * 70000}
    with pytest.raises(ContextValidationError, match="64 KiB"):
        service.create_entity(oversized, "tenant-alpha", "test-user")
    invalid = entity()
    invalid["attributes"] = {"bad": float("nan")}
    with pytest.raises(ContextValidationError):
        service.create_entity(invalid, "tenant-alpha", "test-user")


def test_context_api_requires_existing_oidc_tenant_and_explicit_grants(tmp_path):
    app = create_app(str(tmp_path / "api-deny.sqlite3"))
    app.state.tenants.create("test-tenant", "Test Tenant", "test-bootstrap")
    app.state.tenants.transition("test-tenant", "active", "test-bootstrap")
    from app.authentication import require_authenticated_principal
    from app.principal import Principal

    app.dependency_overrides[require_authenticated_principal] = lambda: Principal(
        "test-user", "user", "test-tenant"
    )
    response = TestClient(app).post(
        "/v1/enterprise-context/entities", json={"entity": entity()}
    )
    assert response.status_code == 422 or response.status_code == 403


def test_context_api_create_query_version_relationship_and_evidence(tmp_path):
    app = configure_test_access(create_app(str(tmp_path / "api.sqlite3")))
    client = TestClient(app)
    response = client.post(
        "/v1/enterprise-context/entities",
        json=entity(),
    )
    assert response.status_code == 201, response.text
    assert response.json()["tenant_id"] == "test-tenant"
    assert client.get(
        "/v1/enterprise-context/entities?entity_type=application"
    ).json()["items"][0]["entity_id"] == "app.alpha"

    db = entity("db.alpha", "database", "Alpha Database")
    assert client.post("/v1/enterprise-context/entities", json=db).status_code == 201

    versioned = entity(name="Alpha Application v2")
    response = client.post(
        "/v1/enterprise-context/entities/app.alpha/versions",
        json={"expected_version": 1, "entity": versioned},
    )
    assert response.status_code == 201, response.text
    assert response.json()["version"] == 2

    relation = relationship()
    response = client.post("/v1/enterprise-context/relationships", json=relation)
    assert response.status_code == 201, response.text
    assert client.get(
        "/v1/enterprise-context/relationships?entity_id=app.alpha"
    ).json()["items"][0]["relationship_id"] == "rel.alpha"

    ev = evidence()
    response = client.post("/v1/enterprise-context/evidence", json=ev)
    assert response.status_code == 201, response.text
    assert client.get(
        "/v1/enterprise-context/entities/app.alpha/evidence"
    ).json()["items"][0]["evidence_id"] == "evidence.alpha"
    assert len(client.get("/v1/enterprise-context/events").json()["items"]) == 4


def test_context_api_rejects_cross_tenant_entity_read(tmp_path):
    app = configure_test_access(create_app(str(tmp_path / "api-isolation.sqlite3")))
    client = TestClient(app)
    other = app.state.tenants
    other.create("tenant-other", "Other Tenant", "test-bootstrap")
    other.transition("tenant-other", "active", "test-bootstrap")
    app.state.enterprise_context.create_entity(entity(), "test-tenant", "test-user")
    from app.authentication import require_authenticated_principal
    from app.principal import Principal

    app.dependency_overrides[require_authenticated_principal] = lambda: Principal(
        "test-user", "user", "tenant-other"
    )
    response = client.get("/v1/enterprise-context/entities/app.alpha")
    assert response.status_code == 403
