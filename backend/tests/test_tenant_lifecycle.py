import pytest

from app.tenant_registry import TenantRegistry


def test_tenant_lifecycle_and_access_state(tmp_path):
    registry = TenantRegistry(tmp_path / "tenants.sqlite3")
    created = registry.create("tenant-1", "Tenant One", "system-admin")
    assert created.status == "pending"
    active = registry.transition("tenant-1", "active", "system-admin")
    assert active.is_accessible is True
    suspended = registry.transition("tenant-1", "suspended", "system-admin")
    assert suspended.is_accessible is False
    reactivated = registry.transition("tenant-1", "active", "system-admin")
    assert reactivated.is_accessible is True
    retired = registry.transition("tenant-1", "decommissioned", "system-admin")
    assert retired.is_accessible is False
    with pytest.raises(ValueError):
        registry.transition("tenant-1", "active", "system-admin")


def test_invalid_transition_does_not_change_state_or_audit(tmp_path):
    registry = TenantRegistry(tmp_path / "tenants.sqlite3")
    registry.create("tenant-1", "Tenant One", "system-admin")
    with pytest.raises(ValueError):
        registry.transition("tenant-1", "pending", "system-admin")
    assert registry.get("tenant-1").status == "pending"
    assert len(registry.audit_events("tenant-1")) == 1
