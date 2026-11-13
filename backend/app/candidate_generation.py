"""Deterministic, bounded candidate generation for immutable AgentBox agents.

Only explicitly registered behavioural operators are supported. Identity, tenant,
permissions, credentials, tools and runtime security boundaries are never mutated.
"""
from __future__ import annotations

import copy
import random
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable

from .registry import AgentNotFoundError, AgentRegistry, VersionConflictError
from .validation import validate_manifest

VERSION_PATTERN = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)
MAX_OPERATORS_PER_CANDIDATE = 5
MAX_SEED = (2**32) - 1
OPERATOR_VERSION = "1.0.0"


class CandidateGenerationError(Exception):
    """Base candidate-generation error."""


class CandidateValidationError(CandidateGenerationError):
    """A candidate request or generated manifest violates the contract."""


class CandidateConflictError(CandidateGenerationError):
    """The requested immutable candidate version already exists."""


@dataclass(frozen=True)
class MutationOperator:
    operator_id: str
    path: str
    apply: Callable[[dict[str, Any]], None]


def _step_limit(delta: int) -> Callable[[dict[str, Any]], None]:
    def apply(manifest: dict[str, Any]) -> None:
        current = manifest["behavior"]["max_steps"]
        manifest["behavior"]["max_steps"] = max(1, min(100, current + delta))
    return apply


def _timeout_limit(delta: int) -> Callable[[dict[str, Any]], None]:
    def apply(manifest: dict[str, Any]) -> None:
        current = manifest["behavior"]["timeout_seconds"]
        manifest["behavior"]["timeout_seconds"] = max(1, min(3600, current + delta))
    return apply


def _model_parameter(name: str, delta: float, minimum: float, maximum: float) -> Callable[[dict[str, Any]], None]:
    def apply(manifest: dict[str, Any]) -> None:
        parameters = manifest["model_binding"].setdefault("parameters", {})
        current = parameters.get(name, 0.7 if name == "temperature" else 1.0)
        if isinstance(current, bool) or not isinstance(current, (int, float)):
            raise CandidateValidationError(f"model parameter {name} must be numeric")
        parameters[name] = round(max(minimum, min(maximum, float(current) + delta)), 4)
    return apply


OPERATORS: dict[str, MutationOperator] = {
    "behavior.max_steps.decrement": MutationOperator(
        "behavior.max_steps.decrement", "/behavior/max_steps", _step_limit(-1)
    ),
    "behavior.max_steps.increment": MutationOperator(
        "behavior.max_steps.increment", "/behavior/max_steps", _step_limit(1)
    ),
    "behavior.timeout_seconds.decrement": MutationOperator(
        "behavior.timeout_seconds.decrement", "/behavior/timeout_seconds", _timeout_limit(-5)
    ),
    "behavior.timeout_seconds.increment": MutationOperator(
        "behavior.timeout_seconds.increment", "/behavior/timeout_seconds", _timeout_limit(5)
    ),
    "model.parameters.temperature.lower": MutationOperator(
        "model.parameters.temperature.lower", "/model_binding/parameters/temperature",
        _model_parameter("temperature", -0.1, 0.0, 2.0)
    ),
    "model.parameters.temperature.higher": MutationOperator(
        "model.parameters.temperature.higher", "/model_binding/parameters/temperature",
        _model_parameter("temperature", 0.1, 0.0, 2.0)
    ),
    "model.parameters.top_p.lower": MutationOperator(
        "model.parameters.top_p.lower", "/model_binding/parameters/top_p",
        _model_parameter("top_p", -0.05, 0.0, 1.0)
    ),
    "model.parameters.top_p.higher": MutationOperator(
        "model.parameters.top_p.higher", "/model_binding/parameters/top_p",
        _model_parameter("top_p", 0.05, 0.0, 1.0)
    ),
}


def _value_at(manifest: dict[str, Any], path: str) -> Any:
    value: Any = manifest
    for segment in path.strip("/").split("/"):
        value = value.get(segment) if isinstance(value, dict) else None
    return value


class CandidateGenerationService:
    """Create a new immutable manifest version from bounded deterministic mutations."""

    def __init__(self, registry: AgentRegistry):
        self.registry = registry

    def generate(
        self,
        agent_id: str,
        parent_version: str,
        candidate_version: str,
        operator_ids: list[str],
        seed: int,
        tenant_id: str,
        actor_id: str,
    ) -> dict[str, Any]:
        if not VERSION_PATTERN.fullmatch(candidate_version):
            raise CandidateValidationError("candidate_version must be valid semantic version text")
        if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= MAX_SEED:
            raise CandidateValidationError(f"seed must be an integer from 0 to {MAX_SEED}")
        if not isinstance(operator_ids, list) or not 1 <= len(operator_ids) <= MAX_OPERATORS_PER_CANDIDATE:
            raise CandidateValidationError(
                f"operator_ids must contain 1 to {MAX_OPERATORS_PER_CANDIDATE} operators"
            )
        if len(operator_ids) != len(set(operator_ids)):
            raise CandidateValidationError("operator_ids must be unique")
        unknown = sorted(set(operator_ids) - set(OPERATORS))
        if unknown:
            raise CandidateValidationError(f"Unsupported mutation operators: {unknown}")
        if not isinstance(actor_id, str) or not actor_id.strip() or len(actor_id) > 256:
            raise CandidateValidationError("actor_id must contain 1 to 256 characters")

        try:
            parent = self.registry.get(agent_id, parent_version, tenant_id)
        except AgentNotFoundError:
            raise

        try:
            self.registry.get(agent_id, candidate_version, tenant_id)
        except AgentNotFoundError:
            pass
        else:
            raise CandidateConflictError(
                f"{agent_id}@{candidate_version} already exists; immutable versions are never overwritten"
            )

        candidate = copy.deepcopy(parent.manifest)
        candidate["version"] = candidate_version
        ordered = [OPERATORS[item] for item in operator_ids]
        random.Random(seed).shuffle(ordered)
        for operator in ordered:
            operator.apply(candidate)

        comparable_candidate = copy.deepcopy(candidate)
        comparable_parent = copy.deepcopy(parent.manifest)
        for item in (comparable_candidate, comparable_parent):
            item.pop("version", None)
            item.pop("provenance", None)
        if comparable_candidate == comparable_parent:
            raise CandidateValidationError("The requested operators produced no candidate change")

        candidate["provenance"] = copy.deepcopy(candidate["provenance"])
        candidate["provenance"]["origin"] = "derived"
        candidate["provenance"]["created_at"] = datetime.now(UTC).isoformat()
        candidate["provenance"]["created_by"] = actor_id
        source_refs = candidate["provenance"].setdefault("source_refs", [])
        parent_ref = f"{agent_id}@{parent_version}"
        if parent_ref not in source_refs:
            source_refs.append(parent_ref)
        for operator in ordered:
            source_refs.append(
                f"agentbox:mutation/{operator.operator_id}@{OPERATOR_VERSION}?seed={seed}"
            )

        errors = validate_manifest(candidate)
        if errors:
            raise CandidateValidationError(f"Generated candidate failed manifest validation: {errors}")

        # Defence in depth: compare all security-sensitive fields with the immutable parent.
        for key in ("schema_version", "agent_id", "permissions", "tools"):
            if candidate.get(key) != parent.manifest.get(key):
                raise CandidateValidationError(f"Candidate mutation changed protected field: {key}")

        try:
            record, created = self.registry.create(
                candidate,
                parent_artifact_id=parent_ref,
                tenant_id=tenant_id,
            )
        except VersionConflictError as exc:
            raise CandidateConflictError(str(exc)) from exc

        return {
            "record": record,
            "created": created,
            "parent_artifact_id": parent_ref,
            "parent_content_hash": parent.content_hash,
            "candidate_content_hash": record.content_hash,
            "seed": seed,
            "operator_version": OPERATOR_VERSION,
            "operator_ids": [item.operator_id for item in ordered],
            "changed_paths": sorted({
                item.path for item in ordered
                if _value_at(parent.manifest, item.path) != _value_at(candidate, item.path)
            }),
            "trust_status": "unverified_candidate",
            "promotion_eligible": False,
        }
