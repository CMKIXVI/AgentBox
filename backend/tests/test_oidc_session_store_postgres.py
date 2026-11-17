import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import psycopg
import pytest

from app.oidc_session_contract import OidcApplicationSession
from app.oidc_session_store_postgres import PostgresOidcApplicationSessionStore

DSN = os.environ.get("AGENTBOX_TEST_POSTGRES_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="PostgreSQL integration DSN not configured")


def session_record(**overrides):
    values = {
        "token_hash": uuid4().hex + uuid4().hex,
        "csrf_token_hash": "b" * 64,
        "subject_id": "user-42",
        "tenant_id": "tenant-7",
        "issuer": "https://identity.example.test/",
        "client_id": "agentbox-web",
        "created_at_epoch": 1000,
        "expires_at_epoch": 1300,
    }
    values.update(overrides)
    return OidcApplicationSession(**values)


@pytest.fixture
def store():
    instance = PostgresOidcApplicationSessionStore(DSN)
    instance.initialize()
    yield instance
    with psycopg.connect(DSN) as connection:
        connection.execute("DELETE FROM oidc_application_sessions")


def test_session_can_be_loaded_and_revoked(store):
    item = session_record()
    store.create(item)
    assert store.get_live(item.token_hash, now_epoch=1200) == item
    assert store.revoke(item.token_hash, now_epoch=1201)
    assert not store.revoke(item.token_hash, now_epoch=1202)
    assert store.get_live(item.token_hash, now_epoch=1202) is None


def test_expired_session_is_not_loaded(store):
    item = session_record(expires_at_epoch=1100)
    store.create(item)
    assert store.get_live(item.token_hash, now_epoch=1100) is None


def test_duplicate_session_hash_is_rejected(store):
    item = session_record()
    store.create(item)
    with pytest.raises(psycopg.errors.UniqueViolation):
        store.create(item)


def test_concurrent_revocation_has_one_winner(store):
    item = session_record()
    store.create(item)

    def revoke(_):
        return PostgresOidcApplicationSessionStore(DSN).revoke(
            item.token_hash, now_epoch=1100
        )

    with ThreadPoolExecutor(max_workers=12) as executor:
        results = list(executor.map(revoke, range(24)))
    assert sum(results) == 1


def test_purge_removes_expired_and_revoked_sessions(store):
    expired = session_record(expires_at_epoch=1100)
    revoked = session_record(token_hash="c" * 64)
    store.create(expired)
    store.create(revoked)
    assert store.revoke(revoked.token_hash, now_epoch=1050)
    assert store.purge(now_epoch=1100) == 2
