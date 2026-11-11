from datetime import UTC, datetime

from app.authorization import authorize_capability
from app.principal import Principal


def policy(effect="allow", **overrides):
    value = {
        "policy_id": "policy-1", "active": True, "effect": effect,
        "capability_id": "crm.contact.read", "principal_scope": "user",
        "principal_ids": ["user-1"], "tenant_ids": ["tenant-1"],
        "actions": ["crm.contact.read"], "resource_ids": ["contact-1"],
    }
    value.update(overrides)
    return value


def request(principal=None, policies=None, **overrides):
    args = {
        "principal": principal or Principal("user-1", "user", "tenant-1"),
        "capability_id": "crm.contact.read", "action": "crm.contact.read",
        "resource_id": "contact-1", "policies": policies or [policy()],
        "evaluated_at": datetime(2026, 11, 12, tzinfo=UTC),
    }
    args.update(overrides)
    return authorize_capability(**args)


def test_explicit_matching_allow():
    assert request()["allowed"] is True


def test_missing_principal_denied():
    assert request(principal=None, policies=[policy()])["reason"] == "missing_principal"


def test_inactive_principal_denied():
    result = request(principal=Principal("user-1", "user", "tenant-1", False))
    assert result["reason"] == "inactive_principal"


def test_no_policy_denies():
    assert request(policies=[])["allowed"] is False


def test_explicit_deny_overrides_allow():
    result = request(policies=[policy(), policy("deny", policy_id="deny-1")])
    assert result["reason"] == "explicit_deny"


def test_cross_tenant_access_denied():
    result = request(principal=Principal("user-1", "user", "tenant-2"))
    assert result["allowed"] is False


def test_wrong_resource_denied():
    assert request(resource_id="contact-2")["allowed"] is False


def test_wrong_action_denied():
    assert request(action="crm.contact.delete")["allowed"] is False


def test_expired_policy_denied():
    assert request(policies=[policy(expires_at="2026-11-11T23:59:59Z")])["allowed"] is False


def test_not_yet_active_policy_denied():
    assert request(policies=[policy(not_before="2026-11-13T00:00:00Z")])["allowed"] is False


def test_inactive_policy_denied():
    assert request(policies=[policy(active=False)])["allowed"] is False
