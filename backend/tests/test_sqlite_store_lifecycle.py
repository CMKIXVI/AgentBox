from __future__ import annotations

import sqlite3

import pytest

from app.authorization_audit import AuthorizationAuditStore
from app.cognitive_runtime import CognitiveRunService
from app.enterprise_context import EnterpriseContextService
from app.evaluation import EvaluationService
from app.execution import ExecutionService
from app.execution_jobs import DurableExecutionJobService
from app.experience import ExecutionExperienceService
from app.registry import AgentRegistry
from app.tenant_registry import TenantRegistry


def test_all_sqlite_stores_release_in_memory_keepers_on_close():
    registry_for_execution = AgentRegistry(":memory:")
    stores = [
        DurableExecutionJobService(":memory:"),
        ExecutionService(":memory:", registry_for_execution),
        registry_for_execution,
        AgentRegistry(":memory:"),
        EvaluationService(":memory:"),
        TenantRegistry(":memory:"),
        ExecutionExperienceService(":memory:"),
        EnterpriseContextService(":memory:"),
        AuthorizationAuditStore(":memory:"),
        CognitiveRunService(":memory:"),
    ]

    try:
        keepers = [store._keeper for store in stores]
        assert all(keeper is not None for keeper in keepers)

        for store in stores:
            store.close()
            store.close()

        for store, keeper in zip(stores, keepers, strict=True):
            with pytest.raises(sqlite3.ProgrammingError, match="closed"):
                keeper.execute("SELECT 1")
            with pytest.raises(RuntimeError, match="closed"):
                store._connect()
    finally:
        for store in stores:
            store.close()
