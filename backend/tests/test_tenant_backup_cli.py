import json

from app.main import create_app
from app.tenant_admin import main


def invoke(database, *arguments):
    create_app(str(database))
    return main(["--database", str(database), *arguments])


def test_operator_cli_backup_and_restore_use_external_key_environment(tmp_path, monkeypatch, capsys):
    import base64

    from app.tenant_registry import TenantRegistry

    source = tmp_path / "source.sqlite3"
    invoke(source, "create", "--tenant-id", "tenant-cli-backup", "--display-name", "CLI Backup")
    capsys.readouterr()
    invoke(source, "active", "--tenant-id", "tenant-cli-backup")
    capsys.readouterr()
    key_id = "OPERATOR_TEST_V1"
    monkeypatch.setenv("AGENTBOX_BACKUP_KEY_ID", key_id)
    monkeypatch.setenv(
        "AGENTBOX_BACKUP_KEY_OPERATOR_TEST_V1",
        base64.b64encode(b"Z" * 32).decode(),
    )
    backup = tmp_path / "operator.agb"
    assert invoke(
        source, "backup", "--tenant-id", "tenant-cli-backup", "--output", str(backup)
    ) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["key_id"] == key_id
    assert backup.exists()

    target = tmp_path / "target.sqlite3"
    create_app(str(target))
    target_registry = TenantRegistry(target)
    target_registry.create("tenant-cli-backup", "CLI Backup", "test-operator")
    target_registry.transition("tenant-cli-backup", "active", "test-operator")
    assert invoke(
        target, "restore", "--tenant-id", "tenant-cli-backup", "--input", str(backup)
    ) == 0
    restored = json.loads(capsys.readouterr().out)
    assert restored["tenant_id"] == "tenant-cli-backup"


def test_operator_cli_backup_fails_closed_without_key(tmp_path, monkeypatch, capsys):
    source = tmp_path / "source.sqlite3"
    invoke(source, "create", "--tenant-id", "tenant-cli-no-key", "--display-name", "No Key")
    capsys.readouterr()
    monkeypatch.delenv("AGENTBOX_BACKUP_KEY_ID", raising=False)
    assert invoke(
        source, "backup", "--tenant-id", "tenant-cli-no-key",
        "--output", str(tmp_path / "no-key.agb")
    ) == 2
    assert "backup key" in capsys.readouterr().err.lower()


def test_operator_cli_closes_registry_after_success_and_failure(tmp_path, monkeypatch, capsys):
    from app import tenant_admin
    from app.tenant_registry import TenantRegistry as RealTenantRegistry

    created = []

    def tracking_registry(database_path):
        registry = RealTenantRegistry(database_path)
        created.append(registry)
        return registry

    monkeypatch.setattr(tenant_admin, "TenantRegistry", tracking_registry)
    database = tmp_path / "cli-lifecycle.sqlite3"
    create_app(str(database))
    assert main([
        "--database", str(database), "create", "--tenant-id", "tenant-cli-close",
        "--display-name", "CLI Close",
    ]) == 0
    capsys.readouterr()
    assert len(created) == 1
    assert created[0]._closed is True

    monkeypatch.delenv("AGENTBOX_BACKUP_KEY_ID", raising=False)
    assert main([
        "--database", str(database), "backup", "--tenant-id", "tenant-cli-close",
        "--output", str(tmp_path / "missing-key.agb"),
    ]) == 2
    capsys.readouterr()
    assert len(created) == 2
    assert created[1]._closed is True


def test_database_preflight_closes_read_only_connection(tmp_path, monkeypatch):
    import sqlite3

    from app import tenant_admin

    database = tmp_path / "empty.sqlite3"
    sqlite3.connect(database).close()
    connections = []
    real_connect = sqlite3.connect

    class TrackingConnection(sqlite3.Connection):
        was_closed = False

        def close(self):
            self.was_closed = True
            super().close()

    def tracking_connect(*args, **kwargs):
        kwargs["factory"] = TrackingConnection
        connection = real_connect(*args, **kwargs)
        connections.append(connection)
        return connection

    monkeypatch.setattr(tenant_admin.sqlite3, "connect", tracking_connect)
    try:
        tenant_admin._require_agentbox_database(str(database))
    except ValueError as exc:
        assert "not an initialized AgentBox database" in str(exc)
    else:
        raise AssertionError("empty SQLite database should be rejected")

    assert len(connections) == 1
    assert connections[0].was_closed is True
