"""Validation for versioned AgentBox tenant artifacts."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


def validate_tenant_contract(value: dict[str, Any]) -> list[dict[str, str]]:
    schema_path = Path(__file__).resolve().parents[2] / "schemas" / "tenant-v1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(value), key=lambda error: (list(map(str, error.absolute_path)), error.message))
    return [
        {"path": "/" + "/".join(str(part) for part in error.absolute_path), "message": error.message}
        for error in errors
    ]
