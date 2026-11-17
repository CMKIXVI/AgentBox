from app.workflow_contract import validate_workflow


def valid_workflow():
    return {
        "schema_version": "1.0.0",
        "workflow_id": "lead-triage",
        "version": "1.0.0",
        "name": "Lead triage",
        "entry_node_id": "start",
        "nodes": [
            {"node_id": "start", "type": "trigger", "name": "Start"},
            {"node_id": "qualify", "type": "agent", "name": "Qualify", "agent_ref": "agent:qualifier@1.0.0"},
            {"node_id": "approve", "type": "human_approval", "name": "Approve", "approval_action": "lead.convert"},
        ],
        "edges": [
            {"edge_id": "e1", "source_node_id": "start", "target_node_id": "qualify", "kind": "default"},
            {"edge_id": "e2", "source_node_id": "qualify", "target_node_id": "approve", "kind": "default"},
        ],
        "provenance": {"origin": "authored", "created_at": "2026-11-12T00:00:00Z"},
    }


def test_valid_workflow_passes():
    assert validate_workflow(valid_workflow()) == []


def test_duplicate_node_ids_are_rejected():
    workflow = valid_workflow()
    workflow["nodes"].append(dict(workflow["nodes"][1]))
    assert any("node_id values must be unique" in error["message"] for error in validate_workflow(workflow))


def test_missing_edge_target_is_rejected():
    workflow = valid_workflow()
    workflow["edges"][0]["target_node_id"] = "missing"
    assert any("Target node does not exist" in error["message"] for error in validate_workflow(workflow))


def test_decision_requires_both_branches():
    workflow = valid_workflow()
    workflow["nodes"][1] = {"node_id": "qualify", "type": "decision", "name": "Qualified?"}
    errors = validate_workflow(workflow)
    assert any("true and false" in error["message"] for error in errors)


def test_unbounded_loop_is_rejected():
    workflow = valid_workflow()
    workflow["nodes"][1] = {"node_id": "qualify", "type": "loop", "name": "Retry"}
    errors = validate_workflow(workflow)
    assert any("bounded max_iterations" in error["message"] for error in errors)


def test_cycle_without_explicit_loop_back_is_rejected():
    workflow = valid_workflow()
    workflow["edges"].append({
        "edge_id": "e3", "source_node_id": "approve", "target_node_id": "qualify", "kind": "default"
    })
    assert any("Cycles are only permitted" in error["message"] for error in validate_workflow(workflow))


def test_tool_node_requires_capability_reference():
    workflow = valid_workflow()
    workflow["nodes"][1] = {"node_id": "qualify", "type": "tool", "name": "CRM lookup"}
    errors = validate_workflow(workflow)
    assert any("capability_ref" in error["message"] for error in errors)


def test_entry_must_be_trigger():
    workflow = valid_workflow()
    workflow["nodes"][0]["type"] = "agent"
    assert any("Entry node must be a trigger" in error["message"] for error in validate_workflow(workflow))


def test_unreachable_nodes_are_rejected():
    workflow = valid_workflow()
    workflow["nodes"].append({"node_id": "orphan", "type": "trigger", "name": "Orphan"})
    errors = validate_workflow(workflow)
    assert any("unreachable" in error["message"] for error in errors)
