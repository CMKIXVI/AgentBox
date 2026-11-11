"""AgentBox API: manifest registry and versioned evaluation service."""
from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from .authentication import require_authenticated_principal
from .authorization import authorize_capability
from .authorization_policy import validate_authorization_policy
from .evaluation import (
    EvaluationProfileConflictError,
    EvaluationProfileNotFoundError,
    EvaluationRunNotFoundError,
    EvaluationService,
)
from .execution import (
    DeterministicFakeProvider,
    ExecutionConflictError,
    ExecutionNotFoundError,
    ExecutionPolicyError,
    ExecutionService,
)
from .principal import Principal
from .registry import AgentNotFoundError, AgentRegistry, VersionConflictError
from .validation import validate_evaluation_profile, validate_manifest

AUTHENTICATED_PRINCIPAL = Depends(require_authenticated_principal)


class ManifestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    manifest: dict[str, Any]


class EvaluationProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile: dict[str, Any]


class CloneRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    new_version: str = Field(
        pattern=r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
    )
    overrides: dict[str, Any] = Field(default_factory=dict)


class ExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    input: Any
    max_output_tokens: int = Field(default=1024, ge=1, le=8192)


class EvaluationCaseSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str = Field(min_length=1, max_length=128)
    output: Any
    latency_ms: float = Field(ge=0)
    cost_usd: float = Field(ge=0)


class EvaluationRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile_id: str = Field(min_length=3, max_length=128)
    profile_version: str = Field(min_length=1, max_length=128)
    results: list[EvaluationCaseSubmission] = Field(max_length=500)


MUTABLE_MANIFEST_FIELDS = {
    "name", "description", "purpose", "behavior", "model_binding", "tools",
    "workflow_ref", "memory", "knowledge_sources", "permissions", "policy_refs",
    "dependencies", "runtime_targets", "evaluation_profile_refs", "tags",
}


def merge_overrides(target: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    for key, value in overrides.items():
        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            target[key] = merge_overrides(copy.deepcopy(target[key]), value)
        else:
            target[key] = copy.deepcopy(value)
    return target


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



def load_authorization_policies() -> list[dict[str, Any]]:
    """Load validated explicit policies; an absent file means deny all."""
    configured = os.getenv("AGENTBOX_AUTHORIZATION_POLICIES_PATH")
    if not configured:
        return []
    try:
        import json

        policies = json.loads(Path(configured).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RuntimeError("Unable to load AgentBox authorization policies") from exc
    if not isinstance(policies, list):
        raise TypeError("AgentBox authorization policy document must be a JSON array")
    for index, policy in enumerate(policies):
        if not isinstance(policy, dict):
            raise TypeError(f"AgentBox authorization policy at index {index} is not an object")
        errors = validate_authorization_policy(policy)
        if errors:
            raise RuntimeError(
                f"Invalid AgentBox authorization policy at index {index}: {errors}"
            )
    return policies


def enforce_authorization(
    app: FastAPI,
    principal: Principal,
    capability_id: str,
    action: str,
    resource_id: str,
) -> None:
    decision = authorize_capability(
        principal,
        capability_id,
        action,
        resource_id,
        app.state.authorization_policies,
    )
    if not decision["allowed"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "Access denied", "reason": decision["reason"]},
        )


def create_app(database_path: str | None = None) -> FastAPI:
    app = FastAPI(
        title="AgentBox API",
        version="0.2.0",
        description=(
            "Frontend-independent API for versioned agent manifests and "
            "deterministic evaluation of submitted agent outputs."
        ),
    )
    db_path = database_path or os.getenv(
        "AGENTBOX_DATABASE_PATH",
        str(Path(__file__).resolve().parents[1] / "data" / "agentbox.sqlite3"),
    )
    app.state.authorization_policies = load_authorization_policies()
    app.state.registry = AgentRegistry(db_path)
    app.state.evaluations = EvaluationService(db_path)
    app.state.executions = ExecutionService(
        db_path, app.state.registry, providers=[DeterministicFakeProvider()]
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "agentbox-api"}

    @app.post("/v1/agents/validate")
    def validate(request: ManifestRequest) -> dict[str, Any]:
        errors = validate_manifest(request.manifest)
        return {"valid": not errors, "errors": errors}

    @app.post("/v1/agents", status_code=status.HTTP_201_CREATED)
    def create_agent(
        request: ManifestRequest,
        principal: Principal = AUTHENTICATED_PRINCIPAL,
    ) -> dict[str, Any]:
        enforce_authorization(app, principal, "agent.registry", "agent.create", request.manifest.get("agent_id", ""))
        errors = validate_manifest(request.manifest)
        if errors:
            raise HTTPException(
                status_code=422,
                detail={"message": "Manifest validation failed", "errors": errors},
            )
        try:
            record, created = app.state.registry.create(request.manifest, tenant_id=principal.tenant_id)
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
        principal: Principal = AUTHENTICATED_PRINCIPAL,
    ) -> dict[str, Any]:
        enforce_authorization(app, principal, "agent.registry", "agent.read", agent_id)
        records = app.state.registry.list(agent_id, limit=limit, offset=offset, tenant_id=principal.tenant_id)
        return {
            "agent_id": agent_id,
            "items": [record_response(item) for item in records],
            "limit": limit,
            "offset": offset,
        }

    @app.get("/v1/agents/{agent_id}/versions/{version}")
    def get_version(
        agent_id: str, version: str,
        principal: Principal = AUTHENTICATED_PRINCIPAL,
    ) -> dict[str, Any]:
        enforce_authorization(app, principal, "agent.registry", "agent.read", agent_id)
        try:
            return record_response(app.state.registry.get(agent_id, version, principal.tenant_id))
        except AgentNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post(
        "/v1/agents/{agent_id}/versions/{version}/clone",
        status_code=status.HTTP_201_CREATED,
    )
    def clone_version(
        agent_id: str, version: str, request: CloneRequest,
        principal: Principal = AUTHENTICATED_PRINCIPAL,
    ) -> dict[str, Any]:
        enforce_authorization(app, principal, "agent.registry", "agent.clone", agent_id)
        try:
            source = app.state.registry.get(agent_id, version)
        except AgentNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        candidate = copy.deepcopy(source.manifest)
        forbidden = sorted(set(request.overrides) - MUTABLE_MANIFEST_FIELDS)
        if forbidden:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Clone overrides contain immutable or unknown fields",
                    "fields": forbidden,
                },
            )
        candidate["version"] = request.new_version
        candidate = merge_overrides(candidate, request.overrides)
        candidate["provenance"] = copy.deepcopy(candidate["provenance"])
        candidate["provenance"]["origin"] = "derived"
        parent_ref = f"{agent_id}@{version}"
        source_refs = candidate["provenance"].setdefault("source_refs", [])
        if parent_ref not in source_refs:
            source_refs.append(parent_ref)
        errors = validate_manifest(candidate)
        if errors:
            raise HTTPException(
                status_code=422,
                detail={"message": "Cloned manifest is invalid", "errors": errors},
            )
        try:
            record, created = app.state.registry.create(
                candidate, parent_artifact_id=parent_ref, tenant_id=principal.tenant_id
            )
        except VersionConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        response = record_response(record)
        response["created"] = created
        return response

    @app.post(
        "/v1/agents/{agent_id}/versions/{version}/executions",
        status_code=status.HTTP_201_CREATED,
    )
    def execute_agent(
        agent_id: str, version: str, request: ExecutionRequest,
        idempotency_key: str = Header(alias="Idempotency-Key"),
        principal: Principal = AUTHENTICATED_PRINCIPAL,
    ) -> dict[str, Any]:
        enforce_authorization(app, principal, "agent.execution", "agent.execute", agent_id)
        try:
            return app.state.executions.execute(
                agent_id, version, request.input, idempotency_key, request.max_output_tokens, principal.tenant_id
            )
        except AgentNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ExecutionPolicyError as exc:
            code = 503 if "Provider is not configured" in str(exc) else 403
            raise HTTPException(status_code=code, detail=str(exc)) from exc
        except ExecutionConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/v1/executions/{execution_id}")
    def get_execution(
        execution_id: str,
        principal: Principal = AUTHENTICATED_PRINCIPAL,
    ) -> dict[str, Any]:
        try:
            record = app.state.executions.get(execution_id, principal.tenant_id)
            enforce_authorization(app, principal, "agent.execution", "execution.read", record["agent_id"])
            return record
        except ExecutionNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/v1/evaluation-profiles/validate")
    def validate_profile(request: EvaluationProfileRequest) -> dict[str, Any]:
        errors = validate_evaluation_profile(request.profile)
        return {"valid": not errors, "errors": errors}

    @app.post("/v1/evaluation-profiles", status_code=status.HTTP_201_CREATED)
    def create_profile(
        request: EvaluationProfileRequest,
        principal: Principal = AUTHENTICATED_PRINCIPAL,
    ) -> dict[str, Any]:
        enforce_authorization(app, principal, "evaluation.profile", "profile.create", request.profile.get("profile_id", ""))
        errors = validate_evaluation_profile(request.profile)
        if errors:
            raise HTTPException(
                status_code=422,
                detail={"message": "Evaluation profile validation failed", "errors": errors},
            )
        try:
            record, created = app.state.evaluations.create_profile(request.profile, principal.tenant_id)
        except EvaluationProfileConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        record["created"] = created
        return record

    @app.get("/v1/evaluation-profiles/{profile_id}/versions")
    def list_profile_versions(
        profile_id: str,
        principal: Principal = AUTHENTICATED_PRINCIPAL,
    ) -> dict[str, Any]:
        enforce_authorization(app, principal, "evaluation.profile", "profile.read", profile_id)
        records = app.state.evaluations.list_profile_versions(profile_id, principal.tenant_id)
        return {"profile_id": profile_id, "items": records}

    @app.get("/v1/evaluation-profiles/{profile_id}/versions/{profile_version}")
    def get_profile(
        profile_id: str, profile_version: str,
        principal: Principal = AUTHENTICATED_PRINCIPAL,
    ) -> dict[str, Any]:
        enforce_authorization(app, principal, "evaluation.profile", "profile.read", profile_id)
        try:
            return app.state.evaluations.get_profile(profile_id, profile_version, principal.tenant_id)
        except EvaluationProfileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post(
        "/v1/agents/{agent_id}/versions/{version}/evaluations",
        status_code=status.HTTP_201_CREATED,
    )
    def evaluate_agent_version(
        agent_id: str, version: str, request: EvaluationRunRequest,
        principal: Principal = AUTHENTICATED_PRINCIPAL,
    ) -> dict[str, Any]:
        enforce_authorization(app, principal, "agent.evaluation", "evaluation.create", agent_id)
        enforce_authorization(app, principal, "evaluation.profile", "profile.read", request.profile_id)
        try:
            app.state.registry.get(agent_id, version)
        except AgentNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        try:
            return app.state.evaluations.create_run(
                agent_id,
                version,
                request.profile_id,
                request.profile_version,
                [item.model_dump() for item in request.results],
                principal.tenant_id,
            )
        except EvaluationProfileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/v1/evaluations/{run_id}")
    def get_evaluation_run(
        run_id: str,
        principal: Principal = AUTHENTICATED_PRINCIPAL,
    ) -> dict[str, Any]:
        try:
            record = app.state.evaluations.get_run(run_id, principal.tenant_id)
            enforce_authorization(app, principal, "agent.evaluation", "evaluation.read", record["agent_id"])
            return record
        except EvaluationRunNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/v1/agents/{agent_id}/versions/{version}/evaluations")
    def list_evaluations(
        agent_id: str, version: str,
        principal: Principal = AUTHENTICATED_PRINCIPAL,
    ) -> dict[str, Any]:
        enforce_authorization(app, principal, "agent.evaluation", "evaluation.read", agent_id)
        try:
            app.state.registry.get(agent_id, version)
        except AgentNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        runs = app.state.evaluations.list_agent_runs(agent_id, version, principal.tenant_id)
        return {"agent_id": agent_id, "agent_version": version, "items": runs}

    return app


app = create_app()
