from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import pytest

from app.context_assembly import ContextAssemblyService, ContextAssemblyValidationError
from app.enterprise_context import ContextNotFoundError, EnterpriseContextService
from app.tenant_registry import TenantRegistry


def entity(entity_id, assertion_class="observed_fact", name=None):
    return {
        "entity_id": entity_id,
        "entity_type": "application",
        "name": name or entity_id,
        "description": f"Description for {entity_id}",
        "attributes": {"environment": "production", "owner": "platform"},
        "assertion_class": assertion_class,
        "confidence": 0.95,
    }


def make_services(tmp_path):
    path = tmp_path / "context-assembly.sqlite3"
    tenants = TenantRegistry(path)
    for tenant_id in ("tenant-alpha", "tenant-beta"):
        tenants.create(tenant_id, tenant_id, "test")
        tenants.transition(tenant_id, "active", "test")
    context = EnterpriseContextService(path)
    return ContextAssemblyService(context), context, tenants


def test_assembly_is_deterministic_minimized_and_excludes_raw_attributes(tmp_path):
    assembler, context, tenants = make_services(tmp_path)
    context.create_entity(entity("app.alpha"), "tenant-alpha", "user-1")
    first = assembler.assemble("tenant-alpha", entity_ids=["app.alpha"])
    second = assembler.assemble("tenant-alpha", entity_ids=["app.alpha"])
    assert first["content_hash"] == second["content_hash"]
    assert first["snapshot_ref"] == f"context-snapshot:{first['content_hash']}"
    assert first["packet"] == second["packet"]
    assert first["packet"]["entities"][0]["entity_id"] == "app.alpha"
    assert "attributes" not in first["packet"]["entities"][0]
    assert "tenant_id" not in first["packet"]
    assert first["packet"]["policy"]["raw_attributes_included"] is False
    assert first["byte_length"] <= 48 * 1024
    context.close()
    tenants.close()


def test_assembly_excludes_inferred_and_hypothesis_records_by_default(tmp_path):
    assembler, context, tenants = make_services(tmp_path)
    context.create_entity(entity("app.observed"), "tenant-alpha", "user-1")
    context.create_entity(
        entity("app.inferred", "inferred"), "tenant-alpha", "user-1"
    )
    context.create_entity(
        entity("app.hypothesis", "ai_hypothesis"), "tenant-alpha", "user-1"
    )
    default = assembler.assemble("tenant-alpha")
    assert [item["entity_id"] for item in default["packet"]["entities"]] == ["app.observed"]
    with_inferences = assembler.assemble("tenant-alpha", include_inferences=True)
    assert {item["entity_id"] for item in with_inferences["packet"]["entities"]} == {
        "app.observed", "app.inferred"
    }
    assert "ai_hypothesis" not in with_inferences["packet"]["policy"]["assertion_classes"]
    context.close()
    tenants.close()


def test_assembly_includes_only_relationships_with_both_selected_endpoints(tmp_path):
    assembler, context, tenants = make_services(tmp_path)
    context.create_entity(entity("app.alpha"), "tenant-alpha", "user-1")
    context.create_entity(entity("app.beta"), "tenant-alpha", "user-1")
    context.create_entity(entity("app.gamma"), "tenant-alpha", "user-1")
    context.create_relationship(
        {
            "relationship_id": "rel.alpha-beta",
            "relationship_type": "depends_on",
            "source_entity_id": "app.alpha",
            "source_version": 1,
            "target_entity_id": "app.beta",
            "target_version": 1,
            "attributes": {"detail": "not copied"},
            "assertion_class": "observed_fact",
            "confidence": 0.9,
        },
        "tenant-alpha", "user-1",
    )
    packet = assembler.assemble(
        "tenant-alpha", entity_ids=["app.alpha", "app.beta"]
    )["packet"]
    assert [item["relationship_id"] for item in packet["relationships"]] == ["rel.alpha-beta"]
    assert "attributes" not in packet["relationships"][0]
    context.close()
    tenants.close()


def test_assembly_hides_cross_tenant_entities_and_rejects_empty_context(tmp_path):
    assembler, context, tenants = make_services(tmp_path)
    context.create_entity(entity("app.alpha"), "tenant-alpha", "user-1")
    with pytest.raises(ContextNotFoundError):
        assembler.assemble("tenant-beta", entity_ids=["app.alpha"])
    with pytest.raises(ContextAssemblyValidationError, match="No currently valid"):
        assembler.assemble("tenant-beta")
    context.close()
    tenants.close()


def test_assembly_rejects_invalid_limits_duplicate_ids_and_ambiguous_selection(tmp_path):
    assembler, context, tenants = make_services(tmp_path)
    with pytest.raises(ContextAssemblyValidationError, match="limit"):
        assembler.assemble("tenant-alpha", limit=13)
    with pytest.raises(ContextAssemblyValidationError, match="duplicates"):
        assembler.assemble("tenant-alpha", entity_ids=["app.alpha", "app.alpha"])
    with pytest.raises(ContextAssemblyValidationError, match="not both"):
        assembler.assemble("tenant-alpha", entity_ids=["app.alpha"], search="alpha")
    with pytest.raises(ContextAssemblyValidationError, match="requested limit"):
        assembler.assemble("tenant-alpha", entity_ids=["app.alpha", "app.beta"], limit=1)
    context.close()
    tenants.close()


def test_unverified_evidence_is_never_promoted_into_context_proof(tmp_path):
    assembler, context, tenants = make_services(tmp_path)
    context.create_entity(entity("app.alpha"), "tenant-alpha", "user-1")
    recorded = context.create_evidence(
        {
            "evidence_id": "evidence.alpha",
            "entity_id": "app.alpha",
            "entity_version": 1,
            "source_kind": "database_metadata",
            "source_ref": "postgres://catalog/public/applications",
            "source_hash": hashlib.sha256(b"catalog snapshot").hexdigest(),
            "observed_at": datetime.now(UTC).isoformat(),
            "confidence": 1.0,
            "metadata": {"connector": "read-only-catalog"},
        },
        "tenant-alpha", "user-1",
    )
    packet = assembler.assemble("tenant-alpha", entity_ids=["app.alpha"])["packet"]
    assert recorded["validation_status"] == "unverified"
    assert packet["evidence"] == []
    assert packet["policy"]["evidence_status"] == "validated_only"
    context.close()
    tenants.close()
