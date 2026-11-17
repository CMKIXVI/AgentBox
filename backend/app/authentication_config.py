"""Validation for versioned AgentBox authentication configuration artifacts."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError


def validate_authentication_config(config: dict[str, Any]) -> list[dict[str, str]]:
    schema_path = (
        Path(__file__).resolve().parents[2]
        / "schemas"
        / "authentication-config-v1.schema.json"
    )
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
    except (OSError, json.JSONDecodeError, SchemaError) as exc:
        raise RuntimeError(f"Unable to load AgentBox authentication schema: {exc}") from exc
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(
        validator.iter_errors(config),
        key=lambda error: (list(map(str, error.absolute_path)), error.message),
    )
    return [
        {
            "path": "/" + "/".join(str(part) for part in error.absolute_path),
            "message": error.message,
        }
        for error in errors
    ]
