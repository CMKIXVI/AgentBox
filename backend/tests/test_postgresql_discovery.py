from __future__ import annotations

import pytest

from app.postgresql_discovery import (
    PostgreSQLCatalogDiscovery,
    PostgreSQLDiscoveryError,
    PostgreSQLDiscoveryLimitError,
)


class FakeCursor:
    def __init__(self):
        self.description = []
        self.last_query = ""
        self.executed = []
        self.closed = False

    def execute(self, query, params=None):
        self.last_query = query
        self.executed.append((query, params))
        self.description = []

    def fetchall(self):
        if "agentbox:schemas" in self.last_query:
            return [("app",), ("audit",)]
        if "agentbox:relations" in self.last_query:
            return [("app", "customers", "table", "Customer records")]
        if "agentbox:columns" in self.last_query:
            return [("app", "customers", 1, "id", "bigint", False, None)]
        if "agentbox:indexes" in self.last_query:
            return [("app", "customers", "customers_pkey", True, True, "CREATE UNIQUE INDEX")]
        if "agentbox:constraints" in self.last_query:
            return [("app", "customers", "customers_pkey", "primary_key", "PRIMARY KEY (id)", None, None)]
        raise AssertionError("Unexpected catalog query")

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self):
        self.fake_cursor = FakeCursor()
        self.rolled_back = False
        self.closed = False

    def cursor(self):
        return self.fake_cursor

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def test_catalog_discovery_is_read_only_and_metadata_only():
    connection = FakeConnection()
    result = PostgreSQLCatalogDiscovery(lambda: connection).discover()

    assert result["schemas"] == ["app", "audit"]
    assert result["relations"][0]["relation_name"] == "customers"
    assert result["columns"][0]["column_name"] == "id"
    assert result["indexes"][0]["is_primary"] is True
    assert result["constraints"][0]["constraint_kind"] == "primary_key"
    assert result["data_rows_read"] == 0
    assert result["writes_performed"] == 0
    assert "snapshot_hash" in result
    assert connection.fake_cursor.executed[0][0] == "BEGIN TRANSACTION READ ONLY"
    assert all("SELECT" not in query.upper() or "pg_catalog" in query for query, _ in connection.fake_cursor.executed)
    assert connection.rolled_back and connection.closed and connection.fake_cursor.closed


def test_discovery_uses_exact_schema_allowlist():
    connection = FakeConnection()
    result = PostgreSQLCatalogDiscovery(lambda: connection).discover(["audit"])
    assert result["schemas"] == ["audit"]
    relation_query = next(item for item in connection.fake_cursor.executed if "agentbox:relations" in item[0])
    assert relation_query[1] == (["audit"],)


def test_discovery_rejects_missing_requested_schema():
    connection = FakeConnection()
    with pytest.raises(PostgreSQLDiscoveryError, match="do not exist"):
        PostgreSQLCatalogDiscovery(lambda: connection).discover(["missing"])


@pytest.mark.parametrize("schemas", [[], ["bad.schema"], ["x; DROP SCHEMA public"]])
def test_schema_allowlist_rejects_invalid_names(schemas):
    with pytest.raises(ValueError):
        PostgreSQLCatalogDiscovery(lambda: FakeConnection()).discover(schemas)


def test_statement_timeout_is_bounded():
    with pytest.raises(ValueError):
        PostgreSQLCatalogDiscovery(lambda: FakeConnection(), statement_timeout_ms=999999)


class OversizedCursor(FakeCursor):
    def fetchall(self):
        if "agentbox:schemas" in self.last_query:
            return [(f"schema_{i}",) for i in range(101)]
        return []


def test_schema_catalog_bound_is_enforced():
    connection = FakeConnection()
    connection.fake_cursor = OversizedCursor()
    with pytest.raises(PostgreSQLDiscoveryLimitError):
        PostgreSQLCatalogDiscovery(lambda: connection).discover()
    assert connection.rolled_back and connection.closed
