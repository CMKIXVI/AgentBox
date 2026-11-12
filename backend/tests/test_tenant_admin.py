import json

import pytest

from app.main import create_app
from app.tenant_admin import local_operator_actor_id, main
from app.tenant_registry import TenantRegistry


def invoke(database, *arguments):
    create_app(str(database))
    return main(["--database", str(database), *arguments])


def test_local_operator_identity_is_os_derived():
    actor = local_operator_actor_id()
    assert actor.startswith("os-user:")
    assert len(actor) <= 256


def test_cli_create_starts_pending_then_activate_and_suspend(tmp_path, capsys):
    database = tmp_path / "agentbox.sqlite3"
    assert invoke(database, "create", "--tenant-id", "tenant-cli", "--display-name", "CLI Tenant") == 0
    created = json.loads(capsys.readouterr().out)
    assert created["status"] == "pending"
    assert created["metadata"] == {}

    assert invoke(database, "active", "--tenant-id", "tenant-cli") == 0
    activated = json.loads(capsys.readouterr().out)
    assert activated["status"] == "active"

    assert invoke(database, "suspended", "--tenant-id", "tenant-cli") == 0
    suspended = json.loads(capsys.readouterr().out)
    assert suspended["status"] == "suspended"


def test_cli_create_accepts_bounded_scalar_metadata(tmp_path, capsys):
    database = tmp_path / "agentbox.sqlite3"
    metadata = json.dumps({"region": "ap-south", "seat_limit": 12, "enabled": True})
    assert invoke(
        database, "create", "--tenant-id", "tenant-meta",
        "--display-name", "Metadata Tenant", "--metadata-json", metadata
    ) == 0
    record = json.loads(capsys.readouterr().out)
    assert record["metadata"] == {"region": "ap-south", "seat_limit": 12, "enabled": True}


def test_cli_list_and_audit_are_read_only_views(tmp_path, capsys):
    database = tmp_path / "agentbox.sqlite3"
    registry = TenantRegistry(database)
    registry.create("tenant-view", "View Tenant", "test-operator")
    assert invoke(database, "list", "--limit", "10") == 0
    records = json.loads(capsys.readouterr().out)
    assert [item["tenant_id"] for item in records] == ["tenant-view"]

    assert invoke(database, "audit", "--tenant-id", "tenant-view") == 0
    events = json.loads(capsys.readouterr().out)
    assert len(events) == 1
    assert events[0]["action"] == "tenant.created"
    assert registry.get("tenant-view").status == "pending"


def test_cli_decommission_is_terminal(tmp_path, capsys):
    database = tmp_path / "agentbox.sqlite3"
    assert invoke(database, "create", "--tenant-id", "tenant-retire", "--display-name", "Retire") == 0
    capsys.readouterr()
    assert invoke(database, "decommissioned", "--tenant-id", "tenant-retire") == 0
    retired = json.loads(capsys.readouterr().out)
    assert retired["status"] == "decommissioned"
    assert invoke(database, "active", "--tenant-id", "tenant-retire") == 2
    assert "Invalid AgentBox tenant lifecycle transition" in capsys.readouterr().err


@pytest.mark.parametrize(
    "metadata",
    ["[]", '"not-an-object"', '{"nested":{"secret":"value"}}', '{"nan":NaN}'],
)
def test_cli_rejects_non_object_or_unsafe_metadata(tmp_path, capsys, metadata):
    database = tmp_path / "agentbox.sqlite3"
    result = invoke(
        database, "create", "--tenant-id", "tenant-bad",
        "--display-name", "Bad Metadata", "--metadata-json", metadata
    )
    assert result == 2
    assert capsys.readouterr().err


def test_cli_rejects_invalid_json_and_duplicate_tenant(tmp_path, capsys):
    database = tmp_path / "agentbox.sqlite3"
    args = ("create", "--tenant-id", "tenant-dup", "--display-name", "Duplicate")
    assert invoke(database, *args, "--metadata-json", "{") == 2
    assert invoke(database, *args) == 0
    capsys.readouterr()
    assert invoke(database, *args) == 2
    assert "already exists" in capsys.readouterr().err


def test_cli_missing_tenant_returns_operator_error(tmp_path, capsys):
    database = tmp_path / "agentbox.sqlite3"
    assert invoke(database, "suspended", "--tenant-id", "missing-tenant") == 2
    assert "missing-tenant" in capsys.readouterr().err



def test_cli_refuses_to_create_or_use_a_missing_database(tmp_path, capsys):
    database = tmp_path / "missing.sqlite3"
    result = main(["--database", str(database), "list"])
    assert result == 2
    assert not database.exists()
    assert "does not exist" in capsys.readouterr().err


def test_cli_refuses_an_unrelated_or_empty_sqlite_database(tmp_path, capsys):
    import sqlite3

    database = tmp_path / "unrelated.sqlite3"
    sqlite3.connect(database).close()
    result = main(["--database", str(database), "list"])
    assert result == 2
    assert "not an initialized AgentBox database" in capsys.readouterr().err
