import sqlite3

import pytest

from app.tenant_registry import TenantRegistry


def test_audit_is_append_only(tmp_path):
    path = tmp_path / "tenants.sqlite3"
    registry = TenantRegistry(path)
    registry.create("tenant-1", "Tenant One", "system-admin")
    registry.transition("tenant-1", "active", "system-admin")
    events = registry.audit_events("tenant-1")
    assert [event["new_status"] for event in events] == ["pending", "active"]
    connection = sqlite3.connect(path)
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute("UPDATE tenant_audit SET actor_id = 'forged' WHERE audit_id = 1")
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute("DELETE FROM tenant_audit WHERE audit_id = 1")
    connection.close()
