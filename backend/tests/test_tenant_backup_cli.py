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
    key_id = "operator_test_v1"
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
