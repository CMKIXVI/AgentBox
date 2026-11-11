"""Manifest validation using the repository's authoritative JSON Schema."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError


def schema_path() -> Path:
    configured = os.getenv("AGENTBOX_SCHEMA_PATH")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[2] / "schemas" / "agent-manifest-v1.schema.json"


def load_validator() -> Draft202012Validator:
    path = schema_path()
    if not path.is_file():
        raise RuntimeError(f"Agent manifest schema not found: {path}")
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


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
