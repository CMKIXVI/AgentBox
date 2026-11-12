from __future__ import annotations

import base64
import copy
import hashlib
import json
import os
import sqlite3
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.evaluation import EvaluationService
from app.execution import DeterministicFakeProvider, ExecutionService
from app.registry import AgentRegistry
from app.tenant_backup import (
    BackupConflictError,
    BackupError,
    BackupFormatError,
    BackupKeyError,
    EnvironmentBackupKeyProvider,
    TenantBackupService,
    _aad,
    _canonical,
)
from app.tenant_registry import TenantRegistry

ROOT = Path(__file__).resolve().parents[2]
AGENT = json.loads((ROOT / "examples" / "agent-manifest-v1.json").read_text())
PROFILE = json.loads((ROOT / "examples" / "evaluation-profile-v1.json").read_text())


class StaticKeyProvider:
    def __init__(self, key_id="test-key-v1", key=b"A" * 32):
        self.key_id = key_id
        self.key = key

    def active_key(self):
        return self.key_id, self.key

    def key_for(self, key_id):
        if key_id != self.key_id:
            raise BackupKeyError("unknown test key")
        return self.key


def initialized_database(path: Path, tenant_id: str, *, populate: bool = False):
    registry = AgentRegistry(path)
    evaluations = EvaluationService(path)
    executions = ExecutionService(path, registry, [DeterministicFakeProvider()])
    tenants = TenantRegistry(path)
    tenants.create(tenant_id, f"Tenant {tenant_id}", "test-operator", {"region": "ap-south"})
    tenants.transition(tenant_id, "active", "test-operator")
    if populate:
        manifest = copy.deepcopy(AGENT)
        manifest["agent_id"] = "backup.agent"
        manifest["model_binding"]["provider_id"] = "provider.fake"
        manifest["tools"] = []
        registry.create(manifest, tenant_id=tenant_id)
        profile = copy.deepcopy(PROFILE)
        evaluations.create_profile(profile, tenant_id=tenant_id)
        executions.execute(
            manifest["agent_id"], manifest["version"], {"hello": "world"},
            "backup-idempotency", tenant_id=tenant_id,
        )
        evaluations.create_run(
            manifest["agent_id"], manifest["version"], profile["profile_id"],
            profile["version"], [], tenant_id,
        )
    return registry, evaluations, executions, tenants


def test_encrypted_backup_round_trip_restores_all_tenant_records(tmp_path):
    source = tmp_path / "source.sqlite3"
    target = tmp_path / "target.sqlite3"
    registry, _evaluations, executions, tenants = initialized_database(
        source, "tenant-alpha", populate=True
    )
    destination = tmp_path / "backups" / "tenant-alpha.agb"
    service = TenantBackupService(source, StaticKeyProvider())
    result = service.export_encrypted("tenant-alpha", destination)

    assert result["algorithm"] == "AES-256-GCM"
    assert destination.stat().st_mode & 0o777 == 0o600
    raw = destination.read_bytes()
    assert b"backup.agent" not in raw
    assert b"Tenant tenant-alpha" not in raw

    restored_registry, restored_evaluations, restored_executions, restored_tenants = (
        initialized_database(target, "tenant-alpha")
    )
    counts = TenantBackupService(target, StaticKeyProvider()).restore_encrypted(
        "tenant-alpha", destination
    )
    assert counts["agent_versions"] == 1
    assert counts["evaluation_profiles"] == 1
    assert counts["executions"] == 1
    assert counts["evaluation_runs"] == 1
    assert counts["tenant_audit"] == 2
    assert restored_registry.get("backup.agent", "1.0.0", "tenant-alpha")
    assert restored_evaluations.get_profile(
        PROFILE["profile_id"], PROFILE["version"], "tenant-alpha"
    )
    assert restored_executions.get(
        executions.execute(
            "backup.agent", "1.0.0", {"hello": "world"},
            "backup-idempotency", tenant_id="tenant-alpha",
        )["execution_id"],
        "tenant-alpha",
    )
    assert len(restored_tenants.audit_events("tenant-alpha")) == 4
    assert tenants.get("tenant-alpha").status == "active"
    assert registry.get("backup.agent", "1.0.0", "tenant-alpha")


def test_restore_is_idempotent_and_does_not_overwrite_tenant_lifecycle(tmp_path):
    source = tmp_path / "source.sqlite3"
    target = tmp_path / "target.sqlite3"
    initialized_database(source, "tenant-alpha", populate=True)
    backup = tmp_path / "tenant.agb"
    TenantBackupService(source, StaticKeyProvider()).export_encrypted("tenant-alpha", backup)
    _, _, _, target_tenants = initialized_database(target, "tenant-alpha")
    target_tenants.transition("tenant-alpha", "suspended", "operator")
    restore = TenantBackupService(target, StaticKeyProvider())
    first = restore.restore_encrypted("tenant-alpha", backup)
    second = restore.restore_encrypted("tenant-alpha", backup)
    assert first["agent_versions"] == 1
    assert second["agent_versions"] == 0
    assert second["tenant_audit"] == 0
    assert target_tenants.get("tenant-alpha").status == "suspended"


def test_backup_requires_external_32_byte_key_and_key_identifier():
    provider = EnvironmentBackupKeyProvider({})
    with pytest.raises(BackupKeyError):
        provider.active_key()
    values = {
        "AGENTBOX_BACKUP_KEY_ID": "KEY_2026_01",
        "AGENTBOX_BACKUP_KEY_KEY_2026_01": base64.b64encode(b"K" * 32).decode(),
    }
    key_id, key = EnvironmentBackupKeyProvider(values).active_key()
    assert key_id == "KEY_2026_01"
    assert key == b"K" * 32
    values["AGENTBOX_BACKUP_KEY_KEY_2026_01"] = base64.b64encode(b"short").decode()
    with pytest.raises(BackupKeyError):
        EnvironmentBackupKeyProvider(values).active_key()


def test_wrong_key_or_tampered_ciphertext_is_rejected(tmp_path):
    source = tmp_path / "source.sqlite3"
    initialized_database(source, "tenant-alpha")
    backup = tmp_path / "tenant.agb"
    TenantBackupService(source, StaticKeyProvider()).export_encrypted("tenant-alpha", backup)
    with pytest.raises(BackupFormatError):
        TenantBackupService(source, StaticKeyProvider(key=b"B" * 32)).restore_encrypted(
            "tenant-alpha", backup
        )
    envelope = json.loads(backup.read_text())
    ciphertext = bytearray(base64.b64decode(envelope["ciphertext"]))
    ciphertext[-1] ^= 1
    envelope["ciphertext"] = base64.b64encode(ciphertext).decode()
    backup.write_text(json.dumps(envelope))
    with pytest.raises(BackupFormatError):
        TenantBackupService(source, StaticKeyProvider()).restore_encrypted(
            "tenant-alpha", backup
        )


def test_backup_cannot_be_restored_under_another_tenant_id(tmp_path):
    source = tmp_path / "source.sqlite3"
    initialized_database(source, "tenant-alpha", populate=True)
    backup = tmp_path / "tenant.agb"
    TenantBackupService(source, StaticKeyProvider()).export_encrypted("tenant-alpha", backup)
    target = tmp_path / "target.sqlite3"
    initialized_database(target, "tenant-beta")
    with pytest.raises(BackupFormatError):
        TenantBackupService(target, StaticKeyProvider()).restore_encrypted(
            "tenant-beta", backup
        )


def test_restore_requires_preprovisioned_target_tenant(tmp_path):
    source = tmp_path / "source.sqlite3"
    initialized_database(source, "tenant-alpha")
    backup = tmp_path / "tenant.agb"
    TenantBackupService(source, StaticKeyProvider()).export_encrypted("tenant-alpha", backup)
    target = tmp_path / "target.sqlite3"
    AgentRegistry(target)
    EvaluationService(target)
    ExecutionService(target, AgentRegistry(target), [DeterministicFakeProvider()])
    TenantRegistry(target)
    with pytest.raises(BackupError, match="must be provisioned"):
        TenantBackupService(target, StaticKeyProvider()).restore_encrypted("tenant-alpha", backup)


def test_backup_destination_is_never_overwritten(tmp_path):
    source = tmp_path / "source.sqlite3"
    initialized_database(source, "tenant-alpha")
    destination = tmp_path / "tenant.agb"
    destination.write_bytes(b"existing")
    with pytest.raises(BackupError, match="already exists"):
        TenantBackupService(source, StaticKeyProvider()).export_encrypted(
            "tenant-alpha", destination
        )
    assert destination.read_bytes() == b"existing"


def test_backup_rejects_symbolic_link_destinations_and_sources(tmp_path):
    source = tmp_path / "source.sqlite3"
    initialized_database(source, "tenant-alpha")
    backup = tmp_path / "tenant.agb"
    backup.symlink_to(tmp_path / "target.agb")
    service = TenantBackupService(source, StaticKeyProvider())
    with pytest.raises(BackupError):
        service.export_encrypted("tenant-alpha", backup)
    with pytest.raises(BackupError):
        service.restore_encrypted("tenant-alpha", backup)


def test_restore_conflict_rolls_back_all_prior_rows(tmp_path):
    source = tmp_path / "source.sqlite3"
    initialized_database(source, "tenant-alpha", populate=True)
    backup = tmp_path / "tenant.agb"
    TenantBackupService(source, StaticKeyProvider()).export_encrypted("tenant-alpha", backup)

    target = tmp_path / "target.sqlite3"
    _, target_evaluations, _, _ = initialized_database(target, "tenant-alpha")
    altered_profile = copy.deepcopy(PROFILE)
    altered_profile["description"] = "different profile content"
    target_evaluations.create_profile(altered_profile, tenant_id="tenant-alpha")
    with pytest.raises(BackupConflictError):
        TenantBackupService(target, StaticKeyProvider()).restore_encrypted(
            "tenant-alpha", backup
        )
    with sqlite3.connect(target) as connection:
        assert connection.execute(
            "SELECT count(*) FROM agent_versions WHERE tenant_id='tenant-alpha'"
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT count(*) FROM evaluation_profiles WHERE tenant_id='tenant-alpha'"
        ).fetchone()[0] == 1


def test_payload_validation_rejects_cross_tenant_rows(tmp_path):
    source = tmp_path / "source.sqlite3"
    initialized_database(source, "tenant-alpha", populate=True)
    backup = tmp_path / "tenant.agb"
    TenantBackupService(source, StaticKeyProvider()).export_encrypted("tenant-alpha", backup)
    envelope = json.loads(backup.read_text())
    key = StaticKeyProvider().key
    payload = json.loads(AESGCM(key).decrypt(
        base64.b64decode(envelope["nonce"]),
        base64.b64decode(envelope["ciphertext"]),
        _aad(envelope),
    ))
    payload["tables"]["agent_versions"][0]["tenant_id"] = "tenant-beta"
    unsigned = dict(payload)
    unsigned.pop("sha256")
    payload["sha256"] = hashlib.sha256(_canonical(unsigned)).hexdigest()
    nonce = os.urandom(12)
    envelope["nonce"] = base64.b64encode(nonce).decode()
    envelope["ciphertext"] = base64.b64encode(
        AESGCM(key).encrypt(nonce, _canonical(payload), _aad(envelope))
    ).decode()
    backup.write_text(json.dumps(envelope))
    with pytest.raises(BackupFormatError, match="Cross-tenant"):
        TenantBackupService(source, StaticKeyProvider()).restore_encrypted(
            "tenant-alpha", backup
        )



def test_historical_backup_key_remains_available_during_rotation(tmp_path):
    source = tmp_path / "source.sqlite3"
    initialized_database(source, "tenant-alpha", populate=True)
    backup = tmp_path / "old-key.agb"
    old_key = base64.b64encode(b"O" * 32).decode()
    new_key = base64.b64encode(b"N" * 32).decode()
    old_provider = EnvironmentBackupKeyProvider({
        "AGENTBOX_BACKUP_KEY_ID": "BACKUP_OLD",
        "AGENTBOX_BACKUP_KEY_BACKUP_OLD": old_key,
    })
    TenantBackupService(source, old_provider).export_encrypted("tenant-alpha", backup)

    rotated_provider = EnvironmentBackupKeyProvider({
        "AGENTBOX_BACKUP_KEY_ID": "BACKUP_NEW",
        "AGENTBOX_BACKUP_KEY_BACKUP_NEW": new_key,
        "AGENTBOX_BACKUP_KEY_BACKUP_OLD": old_key,
    })
    assert rotated_provider.active_key() == ("BACKUP_NEW", b"N" * 32)
    target = tmp_path / "target.sqlite3"
    initialized_database(target, "tenant-alpha")
    restored = TenantBackupService(target, rotated_provider).restore_encrypted(
        "tenant-alpha", backup
    )
    assert restored["agent_versions"] == 1
