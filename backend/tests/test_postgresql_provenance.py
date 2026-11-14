from __future__ import annotations

import base64
from datetime import UTC, datetime

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from app.enterprise_context import ContextValidationError
from app.postgresql_provenance import PostgreSQLProvenanceVerifier


def signed_fixture():
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    snapshot = {
        "contract_version": "1.0.0",
        "source_kind": "postgresql_catalog",
        "discovered_at": datetime.now(UTC).isoformat(),
        "snapshot_hash": "a" * 64,
    }
    signed_at = datetime.now(UTC).isoformat()
    payload = PostgreSQLProvenanceVerifier.signing_payload(
        tenant_id="tenant-alpha", source_ref="postgresql-catalog://warehouse/snapshot",
        snapshot=snapshot, key_id="warehouse-key-v1", signed_at=signed_at,
    )
    attestation = {
        "algorithm": "Ed25519",
        "key_id": "warehouse-key-v1",
        "signed_at": signed_at,
        "signature": base64.urlsafe_b64encode(private.sign(payload)).decode().rstrip("="),
    }
    return public, snapshot, attestation


def test_valid_signature_binds_tenant_source_and_snapshot_hash():
    public, snapshot, attestation = signed_fixture()
    verifier = PostgreSQLProvenanceVerifier({"warehouse-key-v1": public})
    result = verifier.verify(
        attestation, snapshot, "tenant-alpha",
        "postgresql-catalog://warehouse/snapshot",
    )
    assert result == {
        "algorithm": "Ed25519",
        "key_id": "warehouse-key-v1",
        "signed_at": attestation["signed_at"],
        "verified_snapshot_hash": snapshot["snapshot_hash"],
    }
    with pytest.raises(ContextValidationError, match="signature verification failed"):
        verifier.verify(
            attestation, snapshot, "tenant-beta",
            "postgresql-catalog://warehouse/snapshot",
        )
    with pytest.raises(ContextValidationError, match="signature verification failed"):
        verifier.verify(
            attestation, snapshot, "tenant-alpha",
            "postgresql-catalog://other/snapshot",
        )


def test_unknown_key_tampered_signature_and_stale_attestation_fail_closed():
    public, snapshot, attestation = signed_fixture()
    verifier = PostgreSQLProvenanceVerifier({"another-key": public})
    with pytest.raises(ContextValidationError, match="not trusted"):
        verifier.verify(attestation, snapshot, "tenant-alpha", "postgresql-catalog://warehouse/snapshot")
    verifier = PostgreSQLProvenanceVerifier({"warehouse-key-v1": public})
    tampered = dict(attestation, signature="A" * 86)
    with pytest.raises(ContextValidationError, match="signature verification failed"):
        verifier.verify(tampered, snapshot, "tenant-alpha", "postgresql-catalog://warehouse/snapshot")
    stale = dict(attestation, signed_at="2020-01-01T00:00:00+00:00")
    with pytest.raises(ContextValidationError, match="validity window"):
        verifier.verify(stale, snapshot, "tenant-alpha", "postgresql-catalog://warehouse/snapshot")


def test_attestation_rejects_naive_timestamps_and_unknown_fields():
    public, snapshot, attestation = signed_fixture()
    verifier = PostgreSQLProvenanceVerifier({"warehouse-key-v1": public})
    naive = dict(attestation, signed_at="2026-11-14T10:00:00")
    with pytest.raises(ContextValidationError, match="timezone-aware"):
        verifier.verify(naive, snapshot, "tenant-alpha", "postgresql-catalog://warehouse/snapshot")
    malformed = dict(attestation, trusted=True)
    with pytest.raises(ContextValidationError, match="exactly"):
        verifier.verify(malformed, snapshot, "tenant-alpha", "postgresql-catalog://warehouse/snapshot")
