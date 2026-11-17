from __future__ import annotations

import pytest

from app.enterprise_context import ContextValidationError
from app.postgresql_connection import (
    PostgreSQLConnectionConfig,
    PostgreSQLConnectionFactory,
)


class SecretProvider:
    def __init__(self, value="host=db.example user=reader password=do-not-log"):
        self.value = value
        self.references = []

    def resolve(self, secret_ref):
        self.references.append(secret_ref)
        return self.value


class FakeConnection:
    pass


def test_connection_resolves_secret_at_call_time_and_enforces_tls():
    provider = SecretProvider()
    calls = []

    def connect(conninfo, **kwargs):
        calls.append((conninfo, kwargs))
        return FakeConnection()

    factory = PostgreSQLConnectionFactory(
        config=PostgreSQLConnectionConfig(
            secret_ref="vault://prod/agentbox/catalog",
            connect_timeout_seconds=7,
            application_name="agentbox-catalog-test",
            sslrootcert="/etc/ssl/certs/db-ca.pem",
        ),
        secret_provider=provider,
        connect=connect,
    )

    result = factory()

    assert isinstance(result, FakeConnection)
    assert provider.references == ["vault://prod/agentbox/catalog"]
    assert calls == [(
        "host=db.example user=reader password=do-not-log",
        {
            "sslmode": "verify-full",
            "connect_timeout": 7,
            "application_name": "agentbox-catalog-test",
            "sslrootcert": "/etc/ssl/certs/db-ca.pem",
        },
    )]


def test_secret_is_resolved_for_each_new_connection():
    provider = SecretProvider()
    calls = []
    factory = PostgreSQLConnectionFactory(
        config=PostgreSQLConnectionConfig(secret_ref="prod/postgres/catalog"),
        secret_provider=provider,
        connect=lambda conninfo, **kwargs: calls.append(conninfo) or FakeConnection(),
    )

    factory()
    provider.value = "host=db-rotated.example user=reader password=new-secret"
    factory()

    assert len(provider.references) == 2
    assert len(calls) == 2
    assert calls[1] == provider.value


@pytest.mark.parametrize("secret_ref", ["", "postgresql://user:password@host/db", "../secret", "x" * 257])
def test_invalid_secret_reference_is_rejected(secret_ref):
    with pytest.raises(ValueError):
        PostgreSQLConnectionConfig(secret_ref=secret_ref)


@pytest.mark.parametrize("timeout", [True, 0, 31, 1.5, "10"])
def test_invalid_connect_timeout_is_rejected(timeout):
    with pytest.raises(ValueError):
        PostgreSQLConnectionConfig(
            secret_ref="prod/postgres/catalog",
            connect_timeout_seconds=timeout,
        )


def test_secret_resolution_failure_is_sanitized():
    provider = SecretProvider()
    provider.resolve = lambda _ref: (_ for _ in ()).throw(
        RuntimeError("password=super-secret host=private-db")
    )
    factory = PostgreSQLConnectionFactory(
        config=PostgreSQLConnectionConfig(secret_ref="prod/postgres/catalog"),
        secret_provider=provider,
        connect=lambda *_args, **_kwargs: FakeConnection(),
    )

    with pytest.raises(ContextValidationError) as error:
        factory()

    assert "super-secret" not in str(error.value)
    assert "private-db" not in str(error.value)


def test_driver_failure_is_sanitized():
    provider = SecretProvider()
    factory = PostgreSQLConnectionFactory(
        config=PostgreSQLConnectionConfig(secret_ref="prod/postgres/catalog"),
        secret_provider=provider,
        connect=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("password=do-not-leak")
        ),
    )

    with pytest.raises(ContextValidationError) as error:
        factory()

    assert "do-not-leak" not in str(error.value)
