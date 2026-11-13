import json
from pathlib import Path

from app.main import app


def test_route_inventory_matches_fastapi_openapi():
    inventory_path = (
        Path(__file__).resolve().parents[2]
        / "contracts"
        / "api"
        / "agentbox-route-inventory-v1.json"
    )
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    openapi = app.openapi()

    expected = {
        (route["method"].lower(), route["path"])
        for route in inventory["routes"]
    }
    actual = {
        (method.lower(), path)
        for path, operations in openapi["paths"].items()
        for method in operations
        if method.lower() in {"get", "post", "put", "patch", "delete"}
    }

    assert actual == expected


def test_inventory_marks_only_health_and_validation_routes_public():
    inventory_path = (
        Path(__file__).resolve().parents[2]
        / "contracts"
        / "api"
        / "agentbox-route-inventory-v1.json"
    )
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    public_routes = {
        (route["method"], route["path"])
        for route in inventory["routes"]
        if not route["auth_required"]
    }

    assert public_routes == {
        ("GET", "/health"),
        ("POST", "/v1/agents/validate"),
        ("POST", "/v1/evaluation-profiles/validate"),
    }
