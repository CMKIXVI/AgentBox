"""Manifest validation using the repository's authoritative JSON Schema."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError


def _load_validator(path: Path, label: str) -> Draft202012Validator:
    if not path.is_file():
        raise RuntimeError(f"{label} schema not found: {path}")
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def load_validator() -> Draft202012Validator:
    configured = os.getenv("AGENTBOX_SCHEMA_PATH")
    path = Path(configured) if configured else (
        Path(__file__).resolve().parents[2] / "schemas" / "agent-manifest-v1.schema.json"
    )
    return _load_validator(path, "Agent manifest")


def load_evaluation_validator() -> Draft202012Validator:
    configured = os.getenv("AGENTBOX_EVALUATION_SCHEMA_PATH")
    path = Path(configured) if configured else (
        Path(__file__).resolve().parents[2] / "schemas" / "evaluation-profile-v1.schema.json"
    )
    return _load_validator(path, "Evaluation profile")


def validate_manifest(manifest: dict[str, Any]) -> list[dict[str, str]]:
    try:
        validator = load_validator()
    except (OSError, json.JSONDecodeError, SchemaError) as exc:
        raise RuntimeError(f"Unable to load AgentBox manifest schema: {exc}") from exc

    errors = sorted(
        validator.iter_errors(manifest),
        key=lambda error: (list(map(str, error.absolute_path)), error.message),
    )
    return [
        {
            "path": "/" + "/".join(str(part) for part in error.absolute_path),
            "message": error.message,
        }
        for error in errors
    ]


def validate_evaluation_profile(profile: dict[str, Any]) -> list[dict[str, str]]:
    try:
        validator = load_evaluation_validator()
    except (OSError, json.JSONDecodeError, SchemaError) as exc:
        raise RuntimeError(f"Unable to load evaluation profile schema: {exc}") from exc

    errors = sorted(
        validator.iter_errors(profile),
        key=lambda error: (list(map(str, error.absolute_path)), error.message),
    )
    result = [
        {
            "path": "/" + "/".join(str(part) for part in error.absolute_path),
            "message": error.message,
        }
        for error in errors
    ]
    if not errors and profile:
        weights = profile["scoring"]
        total_weight = (
            weights["correctness_weight"] + weights["latency_weight"] + weights["cost_weight"]
        )
        if abs(total_weight - 1.0) > 1e-9:
            result.append({
                "path": "/scoring",
                "message": "Scoring weights must sum to exactly 1.0 (within 1e-9).",
            })
        case_ids = [case["case_id"] for case in profile["cases"]]
        if len(case_ids) != len(set(case_ids)):
            result.append({
                "path": "/cases",
                "message": "case_id values must be unique within an evaluation profile.",
            })
    return result
