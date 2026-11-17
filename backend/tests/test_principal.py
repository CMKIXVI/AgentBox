import pytest

from app.principal import Principal


def test_valid_user_principal():
    assert Principal("user-1", "user", "tenant-1").subject_id == "user-1"


def test_tenant_principal_identity_is_consistent():
    with pytest.raises(ValueError):
        Principal("tenant-a", "tenant", "tenant-b")


def test_inactive_principal_is_representable_for_explicit_denial():
    assert Principal("user-1", "user", "tenant-1", active=False).active is False


def test_reserved_legacy_tenant_cannot_authenticate():
    with pytest.raises(ValueError):
        Principal("user-1", "user", "__legacy_unassigned__")
