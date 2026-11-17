import sqlite3

import pytest

from app.authorization_audit import AuthorizationAuditStore
from app.principal import Principal


def test_decisions_are_recorded_and_readable(tmp_path):
    store = AuthorizationAuditStore(tmp_path / "audit.sqlite")
    event = store.append(
        Principal("user-1", "user", "tenant-1"), "crm.contact.read",
        "crm.contact.read", "contact-1",
        {"allowed": False, "reason": "no_matching_allow_policy", "matched_policy_ids": []},
    )
    assert store.list_events()[0]["event_id"] == event["event_id"]
    assert store.list_events()[0]["allowed"] is False


def test_audit_records_cannot_be_updated_or_deleted(tmp_path):
    store = AuthorizationAuditStore(tmp_path / "audit.sqlite")
    store.append(None, "capability.read", "read", "resource-1", {"allowed": False})
    with pytest.raises(sqlite3.IntegrityError), store._connect() as connection:
        connection.execute("UPDATE authorization_decisions SET reason='changed'")
    with pytest.raises(sqlite3.IntegrityError), store._connect() as connection:
        connection.execute("DELETE FROM authorization_decisions")
