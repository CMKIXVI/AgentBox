"""Deterministic, evidence-aware assembly of tenant enterprise context snapshots."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from .enterprise_context import (
    ContextNotFoundError,
    ContextValidationError,
    EnterpriseContextService,
)

MAX_SNAPSHOT_BYTES = 48 * 1024
MAX_ENTITIES = 12
MAX_RELATIONSHIPS = 24
MAX_EVIDENCE = 36
ALLOWED_ASSERTIONS = {"observed_fact", "human_validated"}
INFERRED_ASSERTIONS = {"inferred"}


class ContextAssemblyError(Exception):
    """Base context assembly failure."""


class ContextAssemblyValidationError(ContextAssemblyError):
    """The requested context cannot be assembled within policy or size bounds."""


class ContextAssemblyService:
    """Build a minimized context packet from the existing tenant context authority."""

    def __init__(self, enterprise_context: EnterpriseContextService):
        self.enterprise_context = enterprise_context

    @staticmethod
    def _canonical(value: Any) -> str:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        )

    @staticmethod
    def _currently_valid(record: dict[str, Any], now: datetime) -> bool:
        start = record.get("valid_from")
        end = record.get("valid_to")
        if start and datetime.fromisoformat(start) > now:
            return False
        if end and datetime.fromisoformat(end) < now:
            return False
        return True

    def assemble(
        self,
        tenant_id: str,
        entity_ids: list[str] | None = None,
        search: str | None = None,
        include_inferences: bool = False,
        limit: int = 8,
    ) -> dict[str, Any]:
        if type(limit) is not int or not 1 <= limit <= MAX_ENTITIES:
            raise ContextAssemblyValidationError(f"limit must be 1-{MAX_ENTITIES}")
        if type(include_inferences) is not bool:
            raise ContextAssemblyValidationError("include_inferences must be boolean")
        if entity_ids is not None:
            if not isinstance(entity_ids, list) or not 1 <= len(entity_ids) <= MAX_ENTITIES:
                raise ContextAssemblyValidationError(
                    f"entity_ids must contain 1-{MAX_ENTITIES} identifiers"
                )
            if any(not isinstance(item, str) or not item.strip() or len(item) > 128 for item in entity_ids):
                raise ContextAssemblyValidationError("entity_ids contains an invalid identifier")
            if len(set(entity_ids)) != len(entity_ids):
                raise ContextAssemblyValidationError("entity_ids must not contain duplicates")
            entities = [
                self.enterprise_context.get_entity(entity_id, tenant_id)
                for entity_id in entity_ids
            ]
        else:
            entities = self.enterprise_context.query_entities(
                tenant_id, search=search, limit=limit
            )
        now = datetime.now(UTC)
        allowed = ALLOWED_ASSERTIONS | (INFERRED_ASSERTIONS if include_inferences else set())
        selected = [
            entity for entity in entities
            if entity["assertion_class"] in allowed and self._currently_valid(entity, now)
        ][:limit]
        if not selected:
            raise ContextAssemblyValidationError(
                "No currently valid entities meet the context assertion policy"
            )

        entity_ids_selected = {item["entity_id"] for item in selected}
        entities_out = [
            {
                "entity_id": item["entity_id"],
                "version": item["version"],
                "entity_type": item["entity_type"],
                "name": item["name"],
                "description": item["description"][:1000],
                "assertion_class": item["assertion_class"],
                "confidence": item["confidence"],
                "content_hash": item["content_hash"],
                "valid_from": item.get("valid_from"),
                "valid_to": item.get("valid_to"),
            }
            for item in selected
        ]
        relationships: dict[tuple[str, int], dict[str, Any]] = {}
        evidence: dict[str, dict[str, Any]] = {}
        for entity_id in sorted(entity_ids_selected):
            for relation in self.enterprise_context.query_relationships(
                tenant_id, entity_id=entity_id, limit=MAX_RELATIONSHIPS
            ):
                if (
                    relation["source_entity_id"] in entity_ids_selected
                    and relation["target_entity_id"] in entity_ids_selected
                    and relation["assertion_class"] in allowed
                    and self._currently_valid(relation, now)
                ):
                    relationships[(relation["relationship_id"], relation["version"])] = {
                        "relationship_id": relation["relationship_id"],
                        "version": relation["version"],
                        "relationship_type": relation["relationship_type"],
                        "source_entity_id": relation["source_entity_id"],
                        "source_version": relation["source_version"],
                        "target_entity_id": relation["target_entity_id"],
                        "target_version": relation["target_version"],
                        "assertion_class": relation["assertion_class"],
                        "confidence": relation["confidence"],
                        "content_hash": relation["content_hash"],
                    }
            for item in self.enterprise_context.query_evidence(
                entity_id, tenant_id, limit=MAX_EVIDENCE
            ):
                if item["validation_status"] == "validated":
                    evidence[item["evidence_id"]] = {
                        "evidence_id": item["evidence_id"],
                        "entity_id": item["entity_id"],
                        "entity_version": item["entity_version"],
                        "source_kind": item["source_kind"],
                        "source_ref": item["source_ref"],
                        "source_hash": item.get("source_hash"),
                        "observed_at": item["observed_at"],
                        "confidence": item["confidence"],
                        "validation_status": "validated",
                    }
        packet = {
            "schema_version": "1.0.0",
            "tenant_id": tenant_id,
            "policy": {
                "assertion_classes": sorted(allowed),
                "evidence_status": "validated_only",
                "rejected_evidence_included": False,
                "raw_attributes_included": False,
            },
            "entities": sorted(entities_out, key=lambda item: (item["entity_type"], item["entity_id"])),
            "relationships": sorted(
                relationships.values(), key=lambda item: (item["relationship_id"], item["version"])
            )[:MAX_RELATIONSHIPS],
            "evidence": sorted(evidence.values(), key=lambda item: item["evidence_id"])[:MAX_EVIDENCE],
        }
        canonical = self._canonical(packet)
        if len(canonical.encode("utf-8")) > MAX_SNAPSHOT_BYTES:
            raise ContextAssemblyValidationError("Assembled context exceeds the 48 KiB limit")
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return {
            "snapshot_ref": f"context-snapshot:{digest}",
            "content_hash": digest,
            "byte_length": len(canonical.encode("utf-8")),
            "packet": packet,
        }
