import pytest

from app.tenant_registry import TenantConflictError, TenantNotFoundError, TenantRegistry


def test_create_tenant_starts_pending_and_is_audited(tmp_path):
    registry = TenantRegistry(tmp_path / "tenants.sqlite3")
    record = registry.create("tenant-1", "Tenant One", "system-admin", {"region": "ap-south"})
    assert record.status == "pending"
    assert record.is_accessible is False
    assert registry.audit_events("tenant-1")[0]["action"] == "tenant.created"


def test_duplicate_and_unknown_tenants_are_rejected(tmp_path):
    registry = TenantRegistry(tmp_path / "tenants.sqlite3")
    registry.create("tenant-1", "Tenant One", "system-admin")
    with pytest.raises(TenantConflictError):
        registry.create("tenant-1", "Duplicate", "system-admin")
    with pytest.raises(TenantNotFoundError):
        registry.get("missing-tenant")


def test_tenant_registry_persists_across_instances(tmp_path):
    path = tmp_path / "tenants.sqlite3"
    TenantRegistry(path).create("tenant-1", "Tenant One", "system-admin")
    assert TenantRegistry(path).get("tenant-1").display_name == "Tenant One"


def test_metadata_and_pagination_are_bounded(tmp_path):
    registry = TenantRegistry(tmp_path / "tenants.sqlite3")
    registry.create("tenant-1", "Tenant One", "system-admin", {"tier": "standard"})
    registry.create("tenant-2", "Tenant Two", "system-admin")
    assert [item.tenant_id for item in registry.list(limit=1)] == ["tenant-1"]
    with pytest.raises(ValueError):
        registry.list(limit=501)
    with pytest.raises(ValueError):
        registry.create("tenant-3", "Tenant Three", "system-admin", {"bad": []})
