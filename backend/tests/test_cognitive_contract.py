from copy import deepcopy

from app.cognitive_contract import validate_cognitive_event, validate_stage_transition


def valid_event():
    return {
        "schema_version": "1.0.0",
        "event_id": "8a6df7b4-9b0d-4b22-a6d6-2a7b2d2a87d0",
        "run_id": "run-001",
        "trace_id": "trace-001",
        "tenant_id": "tenant-alpha",
        "sequence": 1,
        "stage": "intent",
        "event_type": "intent.accepted",
        "actor": {"kind": "user", "id": "user-1"},
        "occurred_at": "2026-11-14T10:00:00Z",
        "evidence_status": "not_applicable",
        "input_refs": ["request:123"],
        "payload": {"goal_ref": "goal:lead-triage@1.0.0"},
    }


def test_valid_lifecycle_event_passes():
    assert validate_cognitive_event(valid_event()) == []


def test_event_type_must_match_lifecycle_stage():
    event = valid_event()
    event["event_type"] = "execution.completed"
    assert validate_cognitive_event(event)


def test_verification_requires_verified_evidence():
    event = valid_event()
    event.update({
        "stage": "verification",
        "event_type": "verification.passed",
        "evidence_status": "unverified",
        "evidence_refs": ["evaluation:run-1"],
    })
    assert any("verified evidence" in item["message"] for item in validate_cognitive_event(event))


def test_memory_acceptance_requires_verified_evidence():
    event = valid_event()
    event.update({
        "stage": "memory",
        "event_type": "memory.accepted",
        "evidence_status": "verified",
    })
    assert any("verified evidence" in item["message"] for item in validate_cognitive_event(event))


def test_authorization_decision_requires_audit_reference():
    event = valid_event()
    event.update({
        "stage": "responsibility",
        "event_type": "responsibility.authorized",
    })
    assert any("authorization decision reference" in item["message"] for item in validate_cognitive_event(event))


def test_capability_selection_requires_versioned_reference():
    event = valid_event()
    event.update({"stage": "capability", "event_type": "capability.selected"})
    assert any("versioned capability reference" in item["message"] for item in validate_cognitive_event(event))


def test_unknown_fields_and_non_object_events_fail_closed():
    event = deepcopy(valid_event())
    event["execute"] = "python"
    assert validate_cognitive_event(event)
    assert validate_cognitive_event("not-an-object")


def test_stage_transition_allows_same_or_next_stage_only():
    assert validate_stage_transition("cognition", "cognition") == []
    assert validate_stage_transition("cognition", "capability") == []
    assert validate_stage_transition("cognition", "execution")
    assert validate_stage_transition("verification", "cognition")


def test_unknown_stage_transition_fails_closed():
    assert validate_stage_transition("unknown", "intent")
