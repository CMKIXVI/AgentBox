from app.capability_contract import validate_capability


def valid_capability():
    return {
        "schema_version": "1.0.0",
        "capability_id": "crm.contact.read",
        "version": "1.0.0",
        "name": "Read CRM contact",
        "description": "Read a contact visible to the authorized principal.",
        "input_schema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {"contact_id": {"type": "string", "minLength": 1}},
            "required": ["contact_id"],
            "additionalProperties": False,
        },
        "output_schema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {"display_name": {"type": "string"}},
            "required": ["display_name"],
            "additionalProperties": False,
        },
        "auth_ref": "secret-ref:crm.readonly",
        "permission_profile": {"principal_scope": "tenant", "actions": ["crm.contact.read"]},
        "timeout_seconds": 15,
        "audit": {
            "required": True,
            "events": ["requested", "authorized", "denied", "completed", "failed"],
            "record_input": True,
            "record_output": False,
            "redaction_profile_ref": "redaction:crm-contact-v1",
        },
        "provenance": {"origin": "authored", "created_at": "2026-11-12T00:00:00Z"},
    }


def test_valid_capability_passes():
    assert validate_capability(valid_capability()) == []


def test_missing_auth_reference_is_rejected():
    capability = valid_capability()
    del capability["auth_ref"]
    assert any(error["path"] == "/" for error in validate_capability(capability))


def test_timeout_must_be_bounded():
    capability = valid_capability()
    capability["timeout_seconds"] = 99999
    assert any("timeout_seconds" in error["path"] for error in validate_capability(capability))


def test_audit_is_mandatory():
    capability = valid_capability()
    capability["audit"]["required"] = False
    assert validate_capability(capability)


def test_input_recording_requires_redaction_profile():
    capability = valid_capability()
    del capability["audit"]["redaction_profile_ref"]
    assert any("redaction_profile_ref" in error["path"] for error in validate_capability(capability))


def test_invalid_embedded_schema_is_rejected():
    capability = valid_capability()
    capability["input_schema"] = {"type": "not-a-json-schema-type"}
    assert any("Embedded JSON Schema is invalid" in error["message"] for error in validate_capability(capability))


def test_unknown_top_level_field_is_rejected():
    capability = valid_capability()
    capability["execute"] = "python"
    assert validate_capability(capability)
