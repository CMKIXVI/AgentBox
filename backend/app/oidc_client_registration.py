"""Validation for provider-neutral OIDC client registration artifacts.

This validates deployment metadata only. It does not register clients with an
identity provider, resolve secrets, perform redirects, or implement OAuth.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "schemas"
    / "oidc-client-registration-v1.schema.json"
)
_CUSTOM_SCHEME_DENYLIST = {"data", "file", "ftp", "javascript", "mailto", "ws", "wss"}
_SCHEME_PATTERN = re.compile(r"^[a-z][a-z0-9+.-]*$")


def _uri_error(uri: str, platform: str, path: str) -> dict[str, str] | None:
    parsed = urlsplit(uri)
    scheme = parsed.scheme.lower()
    if (
        not _SCHEME_PATTERN.fullmatch(scheme)
        or parsed.fragment
        or parsed.username is not None
        or parsed.password is not None
        or "*" in uri
    ):
        return {"path": path, "message": "URI contains an unsafe or ambiguous component"}
    if scheme == "https":
        if not parsed.hostname:
            return {"path": path, "message": "HTTPS redirect URI must include a host"}
        return None
    if platform == "web":
        return {"path": path, "message": "Web redirect URIs must use HTTPS"}
    if scheme in _CUSTOM_SCHEME_DENYLIST or not parsed.netloc:
        return {
            "path": path,
            "message": "Native redirect URI must use HTTPS or a registered custom app scheme",
        }
    return None


def validate_oidc_client_registration(
    registration: dict[str, Any],
) -> list[dict[str, str]]:
    """Return stable schema and semantic errors for OIDC client registrations."""
    try:
        schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
    except (OSError, json.JSONDecodeError, SchemaError) as exc:
        raise RuntimeError(f"Unable to load OIDC client registration schema: {exc}") from exc

    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = [
        {
            "path": "/" + "/".join(str(part) for part in error.absolute_path),
            "message": error.message,
        }
        for error in validator.iter_errors(registration)
    ]
    if errors:
        return sorted(errors, key=lambda item: (item["path"], item["message"]))

    seen_client_ids: set[str] = set()
    clients = registration["clients"]
    for index, client in enumerate(clients):
        prefix = f"/clients/{index}"
        client_id = client["client_id"]
        if client_id in seen_client_ids:
            errors.append({
                "path": f"{prefix}/client_id",
                "message": "client_id must be unique within the registration",
            })
        seen_client_ids.add(client_id)

        platform = client["platform"]
        client_type = client["client_type"]
        auth_method = client["token_endpoint_auth_method"]
        secret_ref = client.get("client_secret_ref")

        if platform == "native" and (
            client_type != "public" or auth_method != "none" or secret_ref is not None
        ):
            errors.append({
                "path": prefix,
                "message": "Native clients must be public and must not contain client credentials",
            })
        if platform == "web" and (
            client_type != "confidential"
            or auth_method == "none"
            or not secret_ref
        ):
            errors.append({
                "path": prefix,
                "message": "Web BFF clients must be confidential and reference a server-side secret",
            })

        uri_fields = (
            ("redirect_uris", client["redirect_uris"]),
            ("post_logout_redirect_uris", client.get("post_logout_redirect_uris", [])),
        )
        for field, uris in uri_fields:
            for uri_index, uri in enumerate(uris):
                issue = _uri_error(uri, platform, f"{prefix}/{field}/{uri_index}")
                if issue:
                    errors.append(issue)

    return sorted(errors, key=lambda item: (item["path"], item["message"]))
