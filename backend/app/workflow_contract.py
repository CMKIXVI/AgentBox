"""Structural validation for declarative AgentBox workflow graphs.

This module validates graph contracts only. It does not execute nodes, expressions,
tools, agents, or workflow edges.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError


def _load_workflow_validator() -> Draft202012Validator:
    configured = os.getenv("AGENTBOX_WORKFLOW_SCHEMA_PATH")
    path = Path(configured) if configured else (
        Path(__file__).resolve().parents[2] / "schemas" / "workflow-v1.schema.json"
    )
    if not path.is_file():
        raise RuntimeError(f"AgentBox workflow schema not found: {path}")
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate_workflow(workflow: dict[str, Any]) -> list[dict[str, str]]:
    """Return deterministic schema and graph-invariant errors."""
    try:
        validator = _load_workflow_validator()
    except (OSError, json.JSONDecodeError, SchemaError) as exc:
        raise RuntimeError(f"Unable to load AgentBox workflow schema: {exc}") from exc

    errors = sorted(
        validator.iter_errors(workflow),
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

    nodes = workflow["nodes"]
    edges = workflow["edges"]
    node_ids = [node["node_id"] for node in nodes]
    edge_ids = [edge["edge_id"] for edge in edges]
    if len(node_ids) != len(set(node_ids)):
        result.append({"path": "/nodes", "message": "node_id values must be unique."})
    if len(edge_ids) != len(set(edge_ids)):
        result.append({"path": "/edges", "message": "edge_id values must be unique."})
    if result:
        return result

    by_id = {node["node_id"]: node for node in nodes}
    entry_id = workflow["entry_node_id"]
    if entry_id not in by_id:
        result.append({"path": "/entry_node_id", "message": "Entry node does not exist."})
        return result
    if by_id[entry_id]["type"] != "trigger":
        result.append({"path": "/entry_node_id", "message": "Entry node must be a trigger."})

    outgoing: dict[str, list[dict[str, Any]]] = {node_id: [] for node_id in node_ids}
    adjacency: dict[str, list[str]] = {node_id: [] for node_id in node_ids}
    for index, edge in enumerate(edges):
        source = edge["source_node_id"]
        target = edge["target_node_id"]
        if source not in by_id:
            result.append({"path": f"/edges/{index}/source_node_id", "message": "Source node does not exist."})
            continue
        if target not in by_id:
            result.append({"path": f"/edges/{index}/target_node_id", "message": "Target node does not exist."})
            continue
        outgoing[source].append(edge)
        if edge["kind"] == "loop_back":
            if by_id[source]["type"] != "loop":
                result.append({"path": f"/edges/{index}/kind", "message": "Only a loop node may emit a loop_back edge."})
        else:
            adjacency[source].append(target)

    if result:
        return sorted(result, key=lambda item: (item["path"], item["message"]))

    for index, node in enumerate(nodes):
        node_type = node["type"]
        if node_type == "agent" and "agent_ref" not in node:
            result.append({"path": f"/nodes/{index}/agent_ref", "message": "Agent nodes require an agent_ref."})
        if node_type == "tool" and "capability_ref" not in node:
            result.append({"path": f"/nodes/{index}/capability_ref", "message": "Tool nodes require a capability_ref."})
        if node_type == "human_approval" and "approval_action" not in node:
            result.append({"path": f"/nodes/{index}/approval_action", "message": "Approval nodes require an approval_action."})
        if node_type == "loop" and "max_iterations" not in node:
            result.append({"path": f"/nodes/{index}/max_iterations", "message": "Loop nodes require bounded max_iterations."})
        if node_type == "decision":
            branch_kinds = {edge["kind"] for edge in outgoing[node["node_id"]]}
            if not {"true", "false"}.issubset(branch_kinds):
                result.append({"path": f"/nodes/{index}", "message": "Decision nodes require true and false outgoing edges."})

    # Removing explicit loop-back edges must leave an acyclic execution graph.
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str) -> None:
        if node_id in visiting:
            result.append({"path": "/edges", "message": "Cycles are only permitted through explicit loop_back edges."})
            return
        if node_id in visited:
            return
        visiting.add(node_id)
        for child in adjacency[node_id]:
            visit(child)
        visiting.remove(node_id)
        visited.add(node_id)

    for node_id in node_ids:
        visit(node_id)

    # Every declared node must be reachable from the entry point.
    reachable: set[str] = set()
    pending = [entry_id]
    while pending:
        current = pending.pop()
        if current in reachable:
            continue
        reachable.add(current)
        pending.extend(edge["target_node_id"] for edge in outgoing[current])
    for index, node in enumerate(nodes):
        if node["node_id"] not in reachable:
            result.append({"path": f"/nodes/{index}", "message": "Node is unreachable from the entry node."})

    return sorted(result, key=lambda item: (item["path"], item["message"]))
