from app.tenant_contract import validate_tenant_contract


def test_tenant_contract_accepts_valid_record():
    value = {
        "schema_version": "1.0",
        "tenant_id": "tenant-1",
        "display_name": "Tenant One",
        "status": "active",
        "created_at": "2026-11-12T00:00:00Z",
        "updated_at": "2026-11-12T00:00:00Z",
        "metadata": {"region": "ap-south"},
    }
    assert validate_tenant_contract(value) == []


def test_tenant_contract_rejects_unknown_fields_and_unsafe_id():
    value = {
        "schema_version": "1.0",
        "tenant_id": "__legacy_unassigned__",
        "display_name": "Tenant",
        "status": "active",
        "created_at": "2026-11-12T00:00:00Z",
        "updated_at": "2026-11-12T00:00:00Z",
        "unexpected": True,
    }
    assert len(validate_tenant_contract(value)) >= 2
