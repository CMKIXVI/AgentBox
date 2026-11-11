"""Schema validation for AgentBox authorization policy artifacts."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError


def validate_authorization_policy(policy: dict[str, Any]) -> list[dict[str, str]]:
    configured = os.getenv("AGENTBOX_AUTHORIZATION_SCHEMA_PATH")
    path = Path(configured) if configured else (
        Path(__file__).resolve().parents[2] / "schemas" / "authorization-policy-v1.schema.json"
    )
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
    except (OSError, json.JSONDecodeError, SchemaError) as exc:
        raise RuntimeError(f"Unable to load AgentBox authorization schema: {exc}") from exc
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(policy), key=lambda e: (list(map(str, e.absolute_path)), e.message))
    return [
        {"path": "/" + "/".join(str(part) for part in error.absolute_path), "message": error.message}
        for error in errors
    ]
