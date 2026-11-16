from datetime import UTC, datetime

from app.authentication import require_authenticated_principal
from app.principal import Principal


def configure_test_access(app):
    app.state.tenants.create("test-tenant", "Test Tenant", "test-bootstrap")
    app.state.tenants.transition("test-tenant", "active", "test-bootstrap")
    app.dependency_overrides[require_authenticated_principal] = lambda: Principal(
        "test-user", "user", "test-tenant"
    )
    resources = [
        "research.summarizer", "runtime.test", "quality.research-summary",
        "tenant-context", "tenant-experience", "app.alpha", "db.alpha", "rel.alpha", "evidence.alpha", "tenant-connectors", "connector.alpha", "warehouse-prod", "research.summarizer",
    ]
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
        ("enterprise.context", "context.entity.create"),
        ("enterprise.context", "context.entity.update"),
        ("enterprise.context", "context.entity.read"),
        ("enterprise.context", "context.relationship.create"),
        ("enterprise.context", "context.relationship.read"),
        ("enterprise.context", "context.evidence.create"),
        ("enterprise.context", "context.evidence.read"),
        ("enterprise.context", "context.evidence.review"),
        ("enterprise.context", "context.event.read"),
        ("enterprise.discovery", "discovery.snapshot.ingest"),
        ("enterprise.discovery", "connector.register"),
        ("enterprise.discovery", "connector.read"),
        ("enterprise.discovery", "connector.rotate_key"),
        ("enterprise.discovery", "connector.revoke_key"),
        ("agent.experience", "experience.create"),
        ("agent.experience", "experience.read"),
        ("agent.experience", "lesson.create"),
        ("agent.experience", "lesson.read"),
        ("agent.experience", "fitness.select"),
        ("agent.experiment", "experiment.compare"),
        ("agent.experiment", "experiment.read"),
        ("agent.cognition", "cognition.run.create"),
        ("agent.cognition", "cognition.run.read"),
        ("agent.cognition", "cognition.event.append"),
        ("agent.cognition", "cognition.context.assemble"),
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
