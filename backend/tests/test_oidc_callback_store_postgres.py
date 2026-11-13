import os
from concurrent.futures import ThreadPoolExecutor
import hashlib
from uuid import uuid4

import psycopg
import pytest

from app.oidc_callback_contract import OidcCallbackTransaction
from app.oidc_callback_store_postgres import PostgresOidcCallbackTransactionStore

DSN = os.environ.get("AGENTBOX_TEST_POSTGRES_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="PostgreSQL integration DSN not configured")


def transaction(transaction_id=None, **overrides):
    identifier = transaction_id or f"txn-{uuid4().hex}"
    values = {
        "transaction_id": identifier,
        "client_id": "agentbox-web",
        "redirect_uri": "https://console.example.test/auth/callback",
        "state_hash": hashlib.sha256(identifier.encode()).hexdigest(),
        "nonce_hash": "b" * 64,
        "pkce_verifier_ref": f"vault://agentbox/oidc/transactions/{identifier}",
        "created_at_epoch": 1000,
        "expires_at_epoch": 1300,
    }
    values.update(overrides)
    return OidcCallbackTransaction(**values)


@pytest.fixture
def store():
    instance = PostgresOidcCallbackTransactionStore(DSN)
    instance.initialize()
    yield instance
    with psycopg.connect(DSN) as connection:
        connection.execute("DELETE FROM oidc_callback_transactions")


def test_saved_transaction_can_be_consumed_once(store):
    expected = transaction()
    store.save(expected)
    assert store.consume_once(expected.transaction_id, now_epoch=1200) == expected
    assert store.consume_once(expected.transaction_id, now_epoch=1200) is None


def test_expired_transaction_is_rejected_and_removed(store):
    item = transaction(expires_at_epoch=1100)
    store.save(item)
    assert store.consume_once(item.transaction_id, now_epoch=1100) is None
    assert store.consume_once(item.transaction_id, now_epoch=1050) is None


def test_duplicate_transaction_id_is_rejected(store):
    item = transaction()
    store.save(item)
    with pytest.raises(psycopg.errors.UniqueViolation):
        store.save(item)


def test_invalid_transaction_is_not_persisted(store):
    with pytest.raises(ValueError, match="Invalid OIDC"):
        store.save(transaction(state_hash="not-a-hash"))


def test_only_one_concurrent_consumer_wins_across_connections(store):
    item = transaction()
    store.save(item)

    def consume(_):
        return PostgresOidcCallbackTransactionStore(DSN).consume_once(
            item.transaction_id, now_epoch=1200
        )

    with ThreadPoolExecutor(max_workers=12) as executor:
        results = list(executor.map(consume, range(24)))
    assert sum(result is not None for result in results) == 1


def test_expiry_purge_removes_only_expired_rows(store):
    expired = transaction(expires_at_epoch=1100)
    live = transaction(expires_at_epoch=1300)
    store.save(expired)
    store.save(live)
    assert store.purge_expired(now_epoch=1100) >= 1
    assert store.consume_once(expired.transaction_id, now_epoch=1000) is None
    assert store.consume_once(live.transaction_id, now_epoch=1200) == live


def test_state_hash_consumption_is_single_use(store):
    item = transaction()
    store.save(item)
    assert store.consume_by_state_hash(item.state_hash, now_epoch=1200) == item
    assert store.consume_by_state_hash(item.state_hash, now_epoch=1200) is None


def test_state_hash_consumption_has_one_concurrent_winner(store):
    item = transaction()
    store.save(item)

    def consume(_):
        return PostgresOidcCallbackTransactionStore(DSN).consume_by_state_hash(
            item.state_hash, now_epoch=1200
        )

    with ThreadPoolExecutor(max_workers=12) as executor:
        results = list(executor.map(consume, range(24)))
    assert sum(result is not None for result in results) == 1


def test_consume_rejects_boolean_clock(store):
    with pytest.raises(TypeError, match="integer epoch"):
        store.consume_once("unused", now_epoch=True)
