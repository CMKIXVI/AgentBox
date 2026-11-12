from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from auth_helpers import configure_test_access
from app.main import create_app


def catalog_snapshot():
    payload = {
        "contract_version": "1.0.0",
        "source_kind": "postgresql_catalog",
        "discovered_at": datetime.now(UTC).isoformat(),
        "schemas": ["public"],
        "relations": [
            {"schema_name": "public", "relation_name": "customers", "relation_kind": "table", "comment": None},
            {"schema_name": "public", "relation_name": "orders", "relation_kind": "table", "comment": None},
        ],
        "columns": [
            {"schema_name": "public", "relation_name": "customers", "ordinal_position": 1, "column_name": "id", "data_type": "bigint", "is_nullable": False, "comment": None},
            {"schema_name": "public", "relation_name": "orders", "ordinal_position": 2, "column_name": "customer_id", "data_type": "bigint", "is_nullable": False, "comment": None},
        ],
        "indexes": [
            {"schema_name": "public", "relation_name": "customers", "index_name": "customers_pkey", "is_primary": True, "is_unique": True, "definition": "CREATE UNIQUE INDEX customers_pkey"},
        ],
        "constraints": [
            {"schema_name": "public", "relation_name": "orders", "constraint_name": "orders_customer_fk", "constraint_kind": "foreign_key", "definition": "FOREIGN KEY (customer_id) REFERENCES customers(id)", "referenced_schema": "public", "referenced_relation": "customers"},
        ],
        "data_rows_read": 0,
        "writes_performed": 0,
    }
    payload["snapshot_hash"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest()
    return payload


def test_catalog_snapshot_ingests_entities_relationships_and_unverified_evidence(tmp_path):
    app = configure_test_access(create_app(str(tmp_path / "discovery-ingest.sqlite3")))
    client = TestClient(app)
    response = client.post(
        "/v1/enterprise-discovery/postgresql/snapshots/ingest",
        json={
            "source_ref": "postgresql-catalog://warehouse-prod/snapshot",
            "snapshot": catalog_snapshot(),
        },
    )
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["entities"] == {"created": 7, "reused": 0}
    assert result["relationships"] == {"created": 7, "reused": 0}
    assert result["evidence"] == {"created": 7, "reused": 0}
    assert result["source_rows_read"] == 0
    assert result["source_writes_performed"] == 0
    assert result["validation_status"] == "unverified"

    relations = client.get("/v1/enterprise-context/entities?entity_type=database_relation").json()["items"]
    assert {item["name"] for item in relations} == {"customers", "orders"}
    edges = client.get("/v1/enterprise-context/relationships?limit=200").json()["items"]
    assert {item["relationship_type"] for item in edges} == {
        "contains_relation", "contains_column", "has_index", "has_constraint", "references_relation"
    }
    evidence = client.get(
        f"/v1/enterprise-context/entities/{relations[0]['entity_id']}/evidence"
    ).json()["items"]
    assert evidence[0]["validation_status"] == "unverified"


def test_catalog_snapshot_ingestion_is_idempotent(tmp_path):
    app = configure_test_access(create_app(str(tmp_path / "discovery-repeat.sqlite3")))
    client = TestClient(app)
    request = {
        "source_ref": "postgresql-catalog://warehouse-prod/snapshot",
        "snapshot": catalog_snapshot(),
    }
    first = client.post("/v1/enterprise-discovery/postgresql/snapshots/ingest", json=request)
    second = client.post("/v1/enterprise-discovery/postgresql/snapshots/ingest", json=request)
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    result = second.json()
    assert result["entities"] == {"created": 0, "reused": 7}
    assert result["relationships"] == {"created": 0, "reused": 7}
    assert result["evidence"] == {"created": 0, "reused": 7}


def test_catalog_snapshot_ingestion_requires_explicit_discovery_grant(tmp_path):
    app = configure_test_access(create_app(str(tmp_path / "discovery-deny.sqlite3")))
    app.state.authorization_policies = [
        policy for policy in app.state.authorization_policies
        if policy["capability_id"] != "enterprise.discovery"
    ]
    response = TestClient(app).post(
        "/v1/enterprise-discovery/postgresql/snapshots/ingest",
        json={
            "source_ref": "postgresql-catalog://warehouse-prod/snapshot",
            "snapshot": catalog_snapshot(),
        },
    )
    assert response.status_code == 403


def test_catalog_snapshot_ingestion_rejects_tampering_and_unsafe_source_refs(tmp_path):
    app = configure_test_access(create_app(str(tmp_path / "discovery-invalid.sqlite3")))
    client = TestClient(app)
    tampered = catalog_snapshot()
    tampered["relations"][0]["relation_name"] = "changed"
    response = client.post(
        "/v1/enterprise-discovery/postgresql/snapshots/ingest",
        json={"source_ref": "postgresql-catalog://warehouse-prod/snapshot", "snapshot": tampered},
    )
    assert response.status_code == 422
    for source_ref in (
        "postgresql://user:password@db.example/catalog",
        "postgresql-catalog://warehouse-prod/snapshot?token=secret",
        "postgresql-catalog://warehouse-prod/snapshot#fragment",
    ):
        response = client.post(
            "/v1/enterprise-discovery/postgresql/snapshots/ingest",
            json={"source_ref": source_ref, "snapshot": catalog_snapshot()},
        )
        assert response.status_code == 422
