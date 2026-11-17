"""Validation for declarative AgentBox capability contracts; never invokes capabilities."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError


def _load_validator() -> Draft202012Validator:
    configured = os.getenv("AGENTBOX_CAPABILITY_SCHEMA_PATH")
    path = Path(configured) if configured else (
        Path(__file__).resolve().parents[2] / "schemas" / "capability-v1.schema.json"
    )
    if not path.is_file():
        raise RuntimeError(f"AgentBox capability schema not found: {path}")
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate_capability(capability: dict[str, Any]) -> list[dict[str, str]]:
    """Return deterministic contract and embedded-payload-schema errors."""
    try:
        validator = _load_validator()
    except (OSError, json.JSONDecodeError, SchemaError) as exc:
        raise RuntimeError(f"Unable to load AgentBox capability schema: {exc}") from exc

    errors = sorted(
        validator.iter_errors(capability),
        key=lambda error: (list(map(str, error.absolute_path)), error.message),
    )
    result = [
        {
            "path": "/" + "/".join(str(part) for part in error.absolute_path),
            "message": error.message,
        }
        for error in errors
    ]
    if result:
        return result

    for field in ("input_schema", "output_schema"):
        try:
            Draft202012Validator.check_schema(capability[field])
        except SchemaError as exc:
            result.append({
                "path": f"/{field}",
                "message": f"Embedded JSON Schema is invalid: {exc.message}",
            })

    if capability["audit"]["record_input"] and not capability["audit"].get("redaction_profile_ref"):
        result.append({
            "path": "/audit/redaction_profile_ref",
            "message": "Recording input requires a redaction profile reference.",
        })
    return sorted(result, key=lambda item: (item["path"], item["message"]))
