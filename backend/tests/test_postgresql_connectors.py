from __future__ import annotations

import base64

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from app.enterprise_context import ContextConflictError, ContextNotFoundError, ContextValidationError
from app.postgresql_connectors import PostgreSQLConnectorRegistry


def public_key():
    key = Ed25519PrivateKey.generate().public_key()
    raw = key.public_bytes(Encoding.Raw, PublicFormat.Raw)
    return base64.b64encode(raw).decode("ascii"), raw


def test_connector_registration_is_tenant_scoped_and_key_is_persisted(tmp_path):
    path = tmp_path / "connectors.sqlite3"
    registry = PostgreSQLConnectorRegistry(path)
    encoded, raw = public_key()
    result = registry.register(
        "tenant-a", "warehouse-prod", "postgresql-catalog://warehouse/snapshot",
        "key-v1", encoded, "operator-a",
    )
    assert result["status"] == "active"
    assert registry.get_active_key(
        "tenant-a", "warehouse-prod", "key-v1",
        "postgresql-catalog://warehouse/snapshot",
    ) == raw
    with pytest.raises(ContextNotFoundError):
        registry.get_active_key(
            "tenant-b", "warehouse-prod", "key-v1",
            "postgresql-catalog://warehouse/snapshot",
        )
    with pytest.raises(ContextValidationError, match="source_ref does not match"):
        registry.get_active_key(
            "tenant-a", "warehouse-prod", "key-v1",
            "postgresql-catalog://other/snapshot",
        )
    registry.close()
    reopened = PostgreSQLConnectorRegistry(path)
    assert reopened.get_active_key(
        "tenant-a", "warehouse-prod", "key-v1",
        "postgresql-catalog://warehouse/snapshot",
    ) == raw


def test_key_rotation_keeps_old_key_until_explicit_revocation(tmp_path):
    registry = PostgreSQLConnectorRegistry(tmp_path / "rotation.sqlite3")
    first, first_raw = public_key()
    second, second_raw = public_key()
    registry.register(
        "tenant-a", "warehouse-prod", "postgresql-catalog://warehouse/snapshot",
        "key-v1", first, "operator-a",
    )
    registry.add_key("tenant-a", "warehouse-prod", "key-v2", second, "operator-b")
    assert registry.get_active_key(
        "tenant-a", "warehouse-prod", "key-v1",
        "postgresql-catalog://warehouse/snapshot",
    ) == first_raw
    assert registry.get_active_key(
        "tenant-a", "warehouse-prod", "key-v2",
        "postgresql-catalog://warehouse/snapshot",
    ) == second_raw
    registry.revoke_key("tenant-a", "warehouse-prod", "key-v1", "operator-a")
    with pytest.raises(ContextValidationError, match="unknown or revoked"):
        registry.get_active_key(
            "tenant-a", "warehouse-prod", "key-v1",
            "postgresql-catalog://warehouse/snapshot",
        )
    assert registry.get_active_key(
        "tenant-a", "warehouse-prod", "key-v2",
        "postgresql-catalog://warehouse/snapshot",
    ) == second_raw
    with pytest.raises(ContextConflictError, match="already revoked"):
        registry.revoke_key("tenant-a", "warehouse-prod", "key-v1", "operator-a")
    statuses = {row["key_id"]: row["key_status"] for row in registry.list_connectors("tenant-a")}
    assert statuses == {"key-v1": "revoked", "key-v2": "active"}
    assert [event["event_type"] for event in registry.events("tenant-a", "warehouse-prod")] == [
        "connector.registered", "connector.key_added", "connector.key_added",
        "connector.key_revoked",
    ]


def test_connector_registration_rejects_credentials_and_invalid_key_material(tmp_path):
    registry = PostgreSQLConnectorRegistry(tmp_path / "invalid.sqlite3")
    encoded, _ = public_key()
    with pytest.raises(ContextValidationError, match="normalized credential-free"):
        registry.register(
            "tenant-a", "warehouse-prod",
            "postgresql-catalog://user:secret@warehouse/snapshot",
            "key-v1", encoded, "operator-a",
        )
    with pytest.raises(ContextValidationError, match="exactly 32 bytes"):
        registry.register(
            "tenant-a", "warehouse-prod",
            "postgresql-catalog://warehouse/snapshot",
            "key-v1", base64.b64encode(b"short").decode(), "operator-a",
        )
