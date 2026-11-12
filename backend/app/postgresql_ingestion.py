"""Ingest read-only PostgreSQL catalog snapshots into the tenant context store."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any
from urllib.parse import urlsplit

from .enterprise_context import ContextConflictError, ContextNotFoundError, ContextValidationError

MAX_INGEST_ENTITIES = 5000
MAX_INGEST_RELATIONSHIPS = 10000
MAX_SNAPSHOT_BYTES = 8 * 1024 * 1024
HASH_PATTERN = re.compile(r"^[a-f0-9]{64}$")


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _identifier(kind: str, *parts: str) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:32]
    return f"pg.{kind}.{digest}"


class PostgreSQLSnapshotIngestion:
    """Convert catalog metadata into immutable, evidence-backed ECE records."""

    def __init__(self, context_service: Any):
        self.context = context_service

    @staticmethod
    def _validate_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(snapshot, dict):
            raise ContextValidationError("snapshot must be an object")
        if snapshot.get("contract_version") != "1.0.0":
            raise ContextValidationError("Unsupported PostgreSQL catalog snapshot contract")
        if snapshot.get("source_kind") != "postgresql_catalog":
            raise ContextValidationError("snapshot source_kind must be postgresql_catalog")
        if snapshot.get("data_rows_read") != 0 or snapshot.get("writes_performed") != 0:
            raise ContextValidationError("Only metadata-only, read-only snapshots can be ingested")
        try:
            snapshot_bytes = len(_canonical(snapshot).encode("utf-8"))
        except (TypeError, ValueError) as exc:
            raise ContextValidationError("snapshot must contain finite JSON values only") from exc
        if snapshot_bytes > MAX_SNAPSHOT_BYTES:
            raise ContextValidationError("snapshot exceeds the 8 MiB ingestion limit")
        supplied_hash = snapshot.get("snapshot_hash")
        if not isinstance(supplied_hash, str) or not HASH_PATTERN.fullmatch(supplied_hash):
            raise ContextValidationError("snapshot_hash must be a lowercase SHA-256 digest")
        unsigned = dict(snapshot)
        unsigned.pop("snapshot_hash")
        if _digest(unsigned) != supplied_hash:
            raise ContextValidationError("snapshot_hash does not match snapshot content")
        limits = {"schemas": 100, "relations": 2000, "columns": 20000, "indexes": 10000, "constraints": 10000}
        for key, limit in limits.items():
            if not isinstance(snapshot.get(key), list):
                raise ContextValidationError(f"snapshot.{key} must be an array")
            if len(snapshot[key]) > limit:
                raise ContextValidationError(f"snapshot.{key} exceeds {limit} records")
            if key != "schemas" and any(not isinstance(row, dict) for row in snapshot[key]):
                raise ContextValidationError(f"snapshot.{key} records must be objects")
        if sum(len(snapshot[key]) for key in limits) > MAX_INGEST_ENTITIES:
            raise ContextValidationError(f"Snapshot exceeds the {MAX_INGEST_ENTITIES} entity ingestion limit")
        if any(not isinstance(name, str) or not name for name in snapshot["schemas"]):
            raise ContextValidationError("snapshot.schemas must contain non-empty strings")
        if not isinstance(snapshot.get("discovered_at"), str):
            raise ContextValidationError("snapshot.discovered_at must be a timestamp")
        return snapshot

    @staticmethod
    def _validate_source_ref(source_ref: str) -> str:
        if not isinstance(source_ref, str) or not 1 <= len(source_ref) <= 1024:
            raise ContextValidationError("source_ref must contain 1-1024 characters")
        try:
            locator = urlsplit(source_ref)
        except ValueError as exc:
            raise ContextValidationError("source_ref is not a valid URI") from exc
        if locator.scheme != "postgresql-catalog" or not locator.netloc or locator.username or locator.password or locator.query or locator.fragment:
            raise ContextValidationError("source_ref must be a credential-free postgresql-catalog URI without query or fragment")
        return source_ref.rstrip("/")

    def _create_or_version_entity(self, payload: dict[str, Any], tenant_id: str, actor_id: str) -> tuple[bool, int]:
        try:
            existing = self.context.get_entity(payload["entity_id"], tenant_id)
        except ContextNotFoundError:
            try:
                self.context.create_entity(payload, tenant_id, actor_id)
                return True, 1
            except ContextConflictError:
                existing = self.context.get_entity(payload["entity_id"], tenant_id)
        expected_hash = _digest(payload)
        if existing["content_hash"] == expected_hash:
            return False, existing["version"]
        try:
            record = self.context.version_entity(
                payload, tenant_id, actor_id, expected_version=existing["version"]
            )
            return True, record["version"]
        except ContextConflictError:
            latest = self.context.get_entity(payload["entity_id"], tenant_id)
            if latest["content_hash"] == expected_hash:
                return False, latest["version"]
            raise

    def _create_or_reuse_relationship(self, payload: dict[str, Any], tenant_id: str, actor_id: str) -> bool:
        try:
            existing = self.context.get_relationship(payload["relationship_id"], tenant_id)
        except ContextNotFoundError:
            try:
                self.context.create_relationship(payload, tenant_id, actor_id)
                return True
            except ContextConflictError:
                existing = self.context.get_relationship(payload["relationship_id"], tenant_id)
        if existing["content_hash"] != _digest(payload):
            raise ContextConflictError(f"Discovered relationship ID conflicts with existing context: {payload['relationship_id']}")
        return False

    def _create_or_reuse_evidence(self, payload: dict[str, Any], tenant_id: str, actor_id: str) -> bool:
        try:
            existing = self.context.get_evidence(payload["evidence_id"], tenant_id)
        except ContextNotFoundError:
            try:
                self.context.create_evidence(payload, tenant_id, actor_id)
                return True
            except ContextConflictError:
                existing = self.context.get_evidence(payload["evidence_id"], tenant_id)
        fields = ("entity_id", "entity_version", "source_ref", "source_hash", "observed_at", "confidence", "validation_status", "metadata")
        if any(existing.get(key) != payload.get(key) for key in fields):
            raise ContextConflictError(f"Discovered evidence ID conflicts with existing context: {payload['evidence_id']}")
        return False

    def ingest(self, snapshot: dict[str, Any], tenant_id: str, actor_id: str, source_ref: str) -> dict[str, Any]:
        data = self._validate_snapshot(snapshot)
        source_ref = self._validate_source_ref(source_ref)
        snapshot_hash, observed_at = data["snapshot_hash"], data["discovered_at"]
        entity_payloads: list[dict[str, Any]] = []
        entity_ids: dict[tuple[str, ...], str] = {}

        def add_entity(kind: str, key: tuple[str, ...], name: str, attributes: dict[str, Any]) -> str:
            entity_id = _identifier(kind, source_ref, *key)
            entity_payloads.append({
                "entity_id": entity_id,
                "entity_type": f"database_{kind}",
                "name": name,
                "description": f"Discovered PostgreSQL {kind.replace('_', ' ')} metadata",
                "attributes": attributes,
                "assertion_class": "inferred",
                "confidence": 0.85,
            })
            entity_ids[key] = entity_id
            return entity_id

        for schema_name in data["schemas"]:
            if not isinstance(schema_name, str) or not schema_name:
                raise ContextValidationError("Schema names must be non-empty strings")
            add_entity("schema", (schema_name,), schema_name, {"schema_name": schema_name})

        relation_ids: dict[tuple[str, str], str] = {}
        for row in data["relations"]:
            schema_name, relation_name = row.get("schema_name"), row.get("relation_name")
            if not isinstance(schema_name, str) or not isinstance(relation_name, str) or not schema_name or not relation_name:
                raise ContextValidationError("Relation records require schema_name and relation_name")
            key = (schema_name, relation_name)
            relation_ids[key] = add_entity("relation", key, relation_name, {
                "schema_name": schema_name, "relation_name": relation_name,
                "relation_kind": row.get("relation_kind"), "comment": row.get("comment"),
            })

        column_ids: list[tuple[str, str, str]] = []
        for row in data["columns"]:
            schema_name, relation_name, column_name = row.get("schema_name"), row.get("relation_name"), row.get("column_name")
            if not all(isinstance(value, str) and value for value in (schema_name, relation_name, column_name)):
                raise ContextValidationError("Column records require schema, relation and column names")
            entity_id = add_entity("column", (schema_name, relation_name, column_name), column_name, {
                "schema_name": schema_name, "relation_name": relation_name,
                "ordinal_position": row.get("ordinal_position"), "data_type": row.get("data_type"),
                "is_nullable": row.get("is_nullable"), "comment": row.get("comment"),
            })
            column_ids.append((schema_name, relation_name, entity_id))

        index_ids: list[tuple[str, str, str]] = []
        for row in data["indexes"]:
            schema_name, relation_name, index_name = row.get("schema_name"), row.get("relation_name"), row.get("index_name")
            if not all(isinstance(value, str) and value for value in (schema_name, relation_name, index_name)):
                raise ContextValidationError("Index records require schema, relation and index names")
            entity_id = add_entity("index", (schema_name, relation_name, index_name), index_name, {
                "schema_name": schema_name, "relation_name": relation_name,
                "is_primary": row.get("is_primary"), "is_unique": row.get("is_unique"),
                "definition": row.get("definition"),
            })
            index_ids.append((schema_name, relation_name, entity_id))

        constraint_ids: list[tuple[dict[str, Any], str]] = []
        for row in data["constraints"]:
            schema_name, relation_name, constraint_name = row.get("schema_name"), row.get("relation_name"), row.get("constraint_name")
            if not all(isinstance(value, str) and value for value in (schema_name, relation_name, constraint_name)):
                raise ContextValidationError("Constraint records require schema, relation and constraint names")
            entity_id = add_entity("constraint", (schema_name, relation_name, constraint_name), constraint_name, {
                "schema_name": schema_name, "relation_name": relation_name,
                "constraint_kind": row.get("constraint_kind"), "definition": row.get("definition"),
                "referenced_schema": row.get("referenced_schema"), "referenced_relation": row.get("referenced_relation"),
            })
            constraint_ids.append((row, entity_id))

        created_entities = reused_entities = created_evidence = reused_evidence = 0
        entity_versions: dict[str, int] = {}
        for payload in entity_payloads:
            created, entity_version = self._create_or_version_entity(payload, tenant_id, actor_id)
            entity_versions[payload["entity_id"]] = entity_version
            if created:
                created_entities += 1
            else:
                reused_entities += 1
            evidence_payload = {
                "evidence_id": _identifier("evidence", source_ref, snapshot_hash, payload["entity_id"]),
                "entity_id": payload["entity_id"], "entity_version": entity_version,
                "source_kind": "database_metadata", "source_ref": source_ref,
                "source_hash": snapshot_hash, "observed_at": observed_at, "confidence": 0.85,
                "validation_status": "unverified",
                "metadata": {"snapshot_hash": snapshot_hash, "entity_type": payload["entity_type"], "entity_attributes_hash": _digest(payload["attributes"])},
            }
            if self._create_or_reuse_evidence(evidence_payload, tenant_id, actor_id):
                created_evidence += 1
            else:
                reused_evidence += 1

        relationship_payloads: list[dict[str, Any]] = []

        def add_relationship(kind: str, source_id: str, target_id: str, attributes: dict[str, Any]) -> None:
            source_version = entity_versions[source_id]
            target_version = entity_versions[target_id]
            relationship_payloads.append({
                "relationship_id": _identifier(
                    "edge", source_ref, kind, source_id, str(source_version),
                    target_id, str(target_version), _digest(attributes)
                ),
                "relationship_type": kind, "source_entity_id": source_id, "source_version": source_version,
                "target_entity_id": target_id, "target_version": target_version, "attributes": attributes,
                "assertion_class": "inferred", "confidence": 0.8,
            })

        for schema_name in data["schemas"]:
            schema_id = entity_ids[(schema_name,)]
            for (candidate_schema, _), relation_id in relation_ids.items():
                if candidate_schema == schema_name:
                    add_relationship("contains_relation", schema_id, relation_id, {})
        for schema_name, relation_name, column_id in column_ids:
            relation_id = relation_ids.get((schema_name, relation_name))
            if relation_id:
                add_relationship("contains_column", relation_id, column_id, {})
        for schema_name, relation_name, index_id in index_ids:
            relation_id = relation_ids.get((schema_name, relation_name))
            if relation_id:
                add_relationship("has_index", relation_id, index_id, {})
        for row, constraint_id in constraint_ids:
            relation_id = relation_ids.get((row["schema_name"], row["relation_name"]))
            if relation_id:
                add_relationship("has_constraint", relation_id, constraint_id, {})
            if row.get("constraint_kind") == "foreign_key":
                target_id = relation_ids.get((row.get("referenced_schema"), row.get("referenced_relation")))
                if relation_id and target_id and relation_id != target_id:
                    add_relationship("references_relation", relation_id, target_id, {"constraint_name": row["constraint_name"]})

        if len(relationship_payloads) > MAX_INGEST_RELATIONSHIPS:
            raise ContextValidationError(f"Snapshot exceeds the {MAX_INGEST_RELATIONSHIPS} relationship ingestion limit")
        created_relationships = reused_relationships = 0
        for payload in relationship_payloads:
            if self._create_or_reuse_relationship(payload, tenant_id, actor_id):
                created_relationships += 1
            else:
                reused_relationships += 1

        return {
            "tenant_id": tenant_id, "snapshot_hash": snapshot_hash,
            "entities": {"created": created_entities, "reused": reused_entities},
            "relationships": {"created": created_relationships, "reused": reused_relationships},
            "evidence": {"created": created_evidence, "reused": reused_evidence},
            "source_rows_read": 0, "source_writes_performed": 0,
            "validation_status": "unverified",
        }
