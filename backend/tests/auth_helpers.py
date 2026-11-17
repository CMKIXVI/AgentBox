from datetime import UTC, datetime

from app.authentication import require_authenticated_principal
from app.principal import Principal


def configure_test_access(app):
    app.dependency_overrides[require_authenticated_principal] = lambda: Principal(
        "test-user", "user", "test-tenant"
    )
    resources = ["research.summarizer", "runtime.test", "quality.research-summary"]
    grants = [
        ("agent.registry", "agent.create"),
        ("agent.registry", "agent.read"),
        ("agent.registry", "agent.clone"),
        ("agent.execution", "agent.execute"),
        ("agent.execution", "execution.read"),
        ("evaluation.profile", "profile.create"),
        ("evaluation.profile", "profile.read"),
        ("agent.evaluation", "evaluation.create"),
        ("agent.evaluation", "evaluation.read"),
    ]
    created_at = datetime(2026, 11, 12, tzinfo=UTC).isoformat()
    app.state.authorization_policies = [
        {
            "schema_version": "1.0.0",
            "policy_id": f"test.grant.{index}",
            "version": "1.0.0",
            "active": True,
            "effect": "allow",
            "capability_id": capability,
            "principal_scope": "user",
            "principal_ids": ["test-user"],
            "tenant_ids": ["test-tenant"],
            "actions": [action],
            "resource_ids": resources,
            "created_at": created_at,
        }
        for index, (capability, action) in enumerate(grants, start=1)
    ]
    return app
