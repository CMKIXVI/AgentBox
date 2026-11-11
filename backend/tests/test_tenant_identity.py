import pytest

from app.tenant import validate_tenant_id, validate_transition


@pytest.mark.parametrize("value", ["tenant-1", "acme.eu", "A_2"])
def test_valid_tenant_identifiers(value):
    assert validate_tenant_id(value) == value


@pytest.mark.parametrize("value", ["", "x", "__legacy_unassigned__", "../tenant", "tenant/one", "a" * 129])
def test_invalid_tenant_identifiers(value):
    with pytest.raises(ValueError):
        validate_tenant_id(value)


def test_lifecycle_transition_table_is_explicit():
    validate_transition("pending", "active")
    validate_transition("active", "suspended")
    validate_transition("suspended", "active")
    validate_transition("suspended", "decommissioned")
    with pytest.raises(ValueError):
        validate_transition("decommissioned", "active")
    with pytest.raises(ValueError):
        validate_transition("active", "pending")
