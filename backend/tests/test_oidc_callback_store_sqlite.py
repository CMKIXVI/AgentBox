from concurrent.futures import ThreadPoolExecutor

import pytest

from app.oidc_callback_contract import OidcCallbackTransaction
from app.oidc_callback_store_sqlite import SQLiteOidcCallbackTransactionStore


def transaction(transaction_id="txn-123", **overrides):
    values = {
        "transaction_id": transaction_id,
        "client_id": "agentbox-web",
        "redirect_uri": "https://console.example.test/auth/callback",
        "state_hash": "a" * 64,
        "nonce_hash": "b" * 64,
        "pkce_verifier_ref": "vault://agentbox/oidc/transactions/txn-123",
        "created_at_epoch": 1000,
        "expires_at_epoch": 1300,
    }
    values.update(overrides)
    return OidcCallbackTransaction(**values)


def test_saved_transaction_can_be_consumed_once(tmp_path):
    path = tmp_path / "oidc.sqlite3"
    writer = SQLiteOidcCallbackTransactionStore(path)
    reader = SQLiteOidcCallbackTransactionStore(path)
    expected = transaction()
    writer.save(expected)

    assert reader.consume_once("txn-123", now_epoch=1200) == expected
    assert writer.consume_once("txn-123", now_epoch=1200) is None


def test_expired_transaction_is_rejected_and_removed(tmp_path):
    store = SQLiteOidcCallbackTransactionStore(tmp_path / "oidc.sqlite3")
    store.save(transaction())
    assert store.consume_once("txn-123", now_epoch=1300) is None
    assert store.consume_once("txn-123", now_epoch=1200) is None


def test_duplicate_transaction_id_is_rejected(tmp_path):
    store = SQLiteOidcCallbackTransactionStore(tmp_path / "oidc.sqlite3")
    store.save(transaction())
    with pytest.raises(ValueError, match="already exists"):
        store.save(transaction())


def test_invalid_transaction_is_not_persisted(tmp_path):
    store = SQLiteOidcCallbackTransactionStore(tmp_path / "oidc.sqlite3")
    with pytest.raises(ValueError, match="Invalid OIDC"):
        store.save(transaction(state_hash="not-a-hash"))


def test_only_one_concurrent_consumer_wins(tmp_path):
    path = tmp_path / "oidc.sqlite3"
    SQLiteOidcCallbackTransactionStore(path).save(transaction())

    store = SQLiteOidcCallbackTransactionStore(path)

    def consume(_):
        return store.consume_once("txn-123", now_epoch=1200)

    with ThreadPoolExecutor(max_workers=12) as executor:
        results = list(executor.map(consume, range(24)))

    assert sum(result is not None for result in results) == 1


def test_expiry_purge_removes_only_expired_rows(tmp_path):
    store = SQLiteOidcCallbackTransactionStore(tmp_path / "oidc.sqlite3")
    store.save(transaction("expired", expires_at_epoch=1100))
    store.save(transaction("live", expires_at_epoch=1300))

    assert store.purge_expired(now_epoch=1100) == 1
    assert store.consume_once("expired", now_epoch=1000) is None
    assert store.consume_once("live", now_epoch=1200) is not None


def test_consume_rejects_boolean_clock(tmp_path):
    store = SQLiteOidcCallbackTransactionStore(tmp_path / "oidc.sqlite3")
    with pytest.raises(TypeError, match="integer epoch"):
        store.consume_once("txn-123", now_epoch=True)


def test_in_memory_database_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="durable SQLite file path"):
        SQLiteOidcCallbackTransactionStore(":memory:")
