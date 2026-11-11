from app.authorization_policy import validate_authorization_policy


def valid_policy():
    return {
        "schema_version": "1.0.0", "policy_id": "crm-read-user1", "version": "1.0.0",
        "active": True, "effect": "allow", "capability_id": "crm.contact.read",
        "principal_scope": "user", "principal_ids": ["user-1"], "tenant_ids": ["tenant-1"],
        "actions": ["crm.contact.read"], "resource_ids": ["contact-1"],
        "created_at": "2026-11-12T00:00:00Z"
    }


def test_valid_policy_passes():
    assert validate_authorization_policy(valid_policy()) == []


def test_empty_resource_set_is_rejected():
    policy = valid_policy()
    policy["resource_ids"] = []
    assert validate_authorization_policy(policy)


def test_unknown_policy_fields_are_rejected():
    policy = valid_policy()
    policy["wildcard"] = True
    assert validate_authorization_policy(policy)
