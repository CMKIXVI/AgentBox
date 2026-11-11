"""AgentBox API: schema validation and immutable agent registry."""
from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from .registry import AgentNotFoundError, AgentRegistry, VersionConflictError
from .validation import validate_manifest


class ManifestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    manifest: dict[str, Any]


class CloneRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    new_version: str = Field(pattern=r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")


def record_response(record: Any) -> dict[str, Any]:
    return {
        "agent_id": record.agent_id,
        "version": record.version,
        "content_hash": record.content_hash,
        "manifest": record.manifest,
        "parent_artifact_id": record.parent_artifact_id,
        "created_at": record.created_at,
        "artifact_id": f"{record.agent_id}@{record.version}",
    }


def create_app(database_path: str | None = None) -> FastAPI:
    app = FastAPI(
        title="AgentBox API",
        version="0.1.0",
        description="Frontend-independent API for validating and managing versioned agent manifests.",
    )
    db_path = database_path or os.getenv(
        "AGENTBOX_DATABASE_PATH",
        str(Path(__file__).resolve().parents[1] / "data" / "agentbox.sqlite3"),
    )
    app.state.registry = AgentRegistry(db_path)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "agentbox-api"}

    @app.post("/v1/agents/validate")
    def validate(request: ManifestRequest) -> dict[str, Any]:
        errors = validate_manifest(request.manifest)
        return {"valid": not errors, "errors": errors}

    @app.post("/v1/agents", status_code=status.HTTP_201_CREATED)
    def create_agent(request: ManifestRequest) -> dict[str, Any]:
        errors = validate_manifest(request.manifest)
        if errors:
            raise HTTPException(status_code=422, detail={"message": "Manifest validation failed", "errors": errors})
        try:
            record, created = app.state.registry.create(request.manifest)
        except VersionConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        response = record_response(record)
        response["created"] = created
        return response

    @app.get("/v1/agents/{agent_id}/versions")
    def list_versions(
        agent_id: str,
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, Any]:
        records = app.state.registry.list(agent_id, limit=limit, offset=offset)
        return {"agent_id": agent_id, "items": [record_response(item) for item in records],
                "limit": limit, "offset": offset}

    @app.get("/v1/agents/{agent_id}/versions/{version}")
    def get_version(agent_id: str, version: str) -> dict[str, Any]:
        try:
            return record_response(app.state.registry.get(agent_id, version))
        except AgentNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/v1/agents/{agent_id}/versions/{version}/clone", status_code=status.HTTP_201_CREATED)
    def clone_version(agent_id: str, version: str, request: CloneRequest) -> dict[str, Any]:
        try:
            source = app.state.registry.get(agent_id, version)
        except AgentNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        candidate = copy.deepcopy(source.manifest)
        candidate["version"] = request.new_version
        candidate["provenance"] = copy.deepcopy(candidate["provenance"])
        candidate["provenance"]["origin"] = "derived"
        errors = validate_manifest(candidate)
        if errors:
            raise HTTPException(status_code=422, detail={"message": "Cloned manifest is invalid", "errors": errors})
        try:
            record, created = app.state.registry.create(
                candidate, parent_artifact_id=f"{agent_id}@{version}"
            )
        except VersionConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        response = record_response(record)
        response["created"] = created
        return response

    return app


app = create_app()
