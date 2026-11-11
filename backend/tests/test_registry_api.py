from __future__ import annotations

import copy
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.registry import AgentRegistry


ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = json.loads((ROOT / "examples" / "agent-manifest-v1.json").read_text(encoding="utf-8"))


def client_for(tmp_path: Path) -> TestClient:
    return TestClient(create_app(str(tmp_path / "test.sqlite3")))


def test_health_and_openapi(tmp_path: Path) -> None:
    client = client_for(tmp_path)
    assert client.get("/health").json()["status"] == "ok"
    schema = client.get("/openapi.json").json()
    assert schema["info"]["title"] == "AgentBox API"


def test_authoritative_schema_accepts_repository_example(tmp_path: Path) -> None:
    response = client_for(tmp_path).post("/v1/agents/validate", json={"manifest": EXAMPLE})
    assert response.status_code == 200
    assert response.json() == {"valid": True, "errors": []}


def test_schema_rejects_unknown_field_and_embedded_secret(tmp_path: Path) -> None:
    invalid = copy.deepcopy(EXAMPLE)
    invalid["api_key"] = "do-not-accept"
    response = client_for(tmp_path).post("/v1/agents/validate", json={"manifest": invalid})
    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert any("api_key" in error["message"] for error in response.json()["errors"])


def test_schema_rejects_invalid_limits_and_credential_reference(tmp_path: Path) -> None:
    invalid = copy.deepcopy(EXAMPLE)
    invalid["behavior"]["max_steps"] = 1000
    invalid["model_binding"]["credential_ref"] = "plain-api-key"
    result = client_for(tmp_path).post("/v1/agents/validate", json={"manifest": invalid}).json()
    assert result["valid"] is False
    assert len(result["errors"]) >= 2


def test_create_get_list_and_idempotent_replay(tmp_path: Path) -> None:
    client = client_for(tmp_path)
    first = client.post("/v1/agents", json={"manifest": EXAMPLE})
    assert first.status_code == 201
    assert first.json()["created"] is True
    replay = client.post("/v1/agents", json={"manifest": EXAMPLE})
    assert replay.status_code == 201
    assert replay.json()["created"] is False
    fetched = client.get("/v1/agents/research.summarizer/versions/1.0.0")
    assert fetched.status_code == 200
    assert fetched.json()["content_hash"] == first.json()["content_hash"]
    listed = client.get("/v1/agents/research.summarizer/versions")
    assert len(listed.json()["items"]) == 1


def test_immutable_version_conflict(tmp_path: Path) -> None:
    client = client_for(tmp_path)
    assert client.post("/v1/agents", json={"manifest": EXAMPLE}).status_code == 201
    changed = copy.deepcopy(EXAMPLE)
    changed["purpose"] = "Changed purpose under the same immutable version."
    response = client.post("/v1/agents", json={"manifest": changed})
    assert response.status_code == 409


def test_clone_creates_derived_version_with_parent_lineage(tmp_path: Path) -> None:
    client = client_for(tmp_path)
    assert client.post("/v1/agents", json={"manifest": EXAMPLE}).status_code == 201
    clone = client.post(
        "/v1/agents/research.summarizer/versions/1.0.0/clone",
        json={"new_version": "1.1.0"},
    )
    assert clone.status_code == 201
    payload = clone.json()
    assert payload["version"] == "1.1.0"
    assert payload["parent_artifact_id"] == "research.summarizer@1.0.0"
    assert payload["manifest"]["provenance"]["origin"] == "derived"


def test_clone_is_idempotent_and_preserves_immutable_parent_lineage(tmp_path: Path) -> None:
    client = client_for(tmp_path)
    assert client.post("/v1/agents", json={"manifest": EXAMPLE}).status_code == 201
    endpoint = "/v1/agents/research.summarizer/versions/1.0.0/clone"
    first = client.post(endpoint, json={"new_version": "1.1.0"})
    second = client.post(endpoint, json={"new_version": "1.1.0"})
    assert first.status_code == second.status_code == 201
    assert first.json()["created"] is True
    assert second.json()["created"] is False
    assert first.json()["content_hash"] == second.json()["content_hash"]
    assert first.json()["parent_artifact_id"] == "research.summarizer@1.0.0"


def test_create_rejects_invalid_manifest_with_422(tmp_path: Path) -> None:
    invalid = copy.deepcopy(EXAMPLE)
    invalid["behavior"]["timeout_seconds"] = 99999
    response = client_for(tmp_path).post("/v1/agents", json={"manifest": invalid})
    assert response.status_code == 422


def test_in_memory_registry_survives_per_operation_connections() -> None:
    registry = AgentRegistry(":memory:")
    created, was_created = registry.create(EXAMPLE)
    fetched = registry.get("research.summarizer", "1.0.0")
    assert was_created is True
    assert fetched.content_hash == created.content_hash
