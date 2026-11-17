import hashlib
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.oidc_authorization_flow import VerifiedOidcIdentity
from app.oidc_session_contract import OidcApplicationSession
from app.oidc_session_store_sqlite import SQLiteOidcApplicationSessionStore
from app.oidc_sessions import OidcSessionService


def identity():
    return VerifiedOidcIdentity(
        subject_id="user-42",
        tenant_id="tenant-7",
        issuer="https://identity.example.test/",
        client_id="agentbox-web",
    )


def test_issue_persists_only_hashes_and_returns_opaque_credentials(tmp_path):
    path = tmp_path / "sessions.sqlite3"
    store = SQLiteOidcApplicationSessionStore(path)
    service = OidcSessionService(store, ttl_seconds=3600)
    issued = service.issue(identity(), now_epoch=1000)

    assert len(issued.session_token) >= 43
    assert len(issued.csrf_token) >= 43
    assert issued.expires_at_epoch == 4600
    session = service.authenticate(issued.session_token, now_epoch=1001)
    assert session is not None
    assert session.subject_id == "user-42"
    assert session.tenant_id == "tenant-7"
    assert session.token_hash == hashlib.sha256(
        issued.session_token.encode()
    ).hexdigest()
    assert service.validate_csrf(session, issued.csrf_token)
    assert not service.validate_csrf(session, "attacker-token")

    with sqlite3.connect(path) as connection:
        stored = connection.execute(
            "SELECT token_hash, csrf_token_hash FROM oidc_application_sessions"
        ).fetchone()
    assert issued.session_token not in str(stored)
    assert issued.csrf_token not in str(stored)


def test_expired_session_is_not_authenticated(tmp_path):
    store = SQLiteOidcApplicationSessionStore(tmp_path / "sessions.sqlite3")
    service = OidcSessionService(store, ttl_seconds=60)
    issued = service.issue(identity(), now_epoch=1000)
    assert service.authenticate(issued.session_token, now_epoch=1059) is not None
    assert service.authenticate(issued.session_token, now_epoch=1060) is None


def test_revoked_session_cannot_be_reused(tmp_path):
    store = SQLiteOidcApplicationSessionStore(tmp_path / "sessions.sqlite3")
    service = OidcSessionService(store)
    issued = service.issue(identity(), now_epoch=1000)
    assert service.revoke(issued.session_token, now_epoch=1001)
    assert not service.revoke(issued.session_token, now_epoch=1002)
    assert service.authenticate(issued.session_token, now_epoch=1002) is None


def test_concurrent_revocation_has_one_winner(tmp_path):
    store = SQLiteOidcApplicationSessionStore(tmp_path / "sessions.sqlite3")
    service = OidcSessionService(store)
    issued = service.issue(identity(), now_epoch=1000)

    def revoke(_):
        return service.revoke(issued.session_token, now_epoch=1001)

    with ThreadPoolExecutor(max_workers=12) as executor:
        results = list(executor.map(revoke, range(24)))
    assert sum(results) == 1


def test_purge_removes_revoked_and_expired_sessions(tmp_path):
    store = SQLiteOidcApplicationSessionStore(tmp_path / "sessions.sqlite3")
    service = OidcSessionService(store, ttl_seconds=60)
    expired = service.issue(identity(), now_epoch=1000)
    revoked = service.issue(identity(), now_epoch=1000)
    assert service.revoke(revoked.session_token, now_epoch=1001)
    assert store.purge(now_epoch=1060) == 2
    assert service.authenticate(expired.session_token, now_epoch=1000) is None


def test_session_ttl_is_bounded():
    with pytest.raises(ValueError, match="between 1 and 43200"):
        OidcSessionService(object(), ttl_seconds=43_201)


def test_invalid_session_record_is_not_stored(tmp_path):
    store = SQLiteOidcApplicationSessionStore(tmp_path / "sessions.sqlite3")
    invalid = OidcApplicationSession(
        token_hash="not-a-hash",
        csrf_token_hash="b" * 64,
        subject_id="user-42",
        tenant_id="tenant-7",
        issuer="https://identity.example.test/",
        client_id="agentbox-web",
        created_at_epoch=1000,
        expires_at_epoch=1300,
    )
    with pytest.raises(ValueError, match="Invalid OIDC application session"):
        store.create(invalid)


def test_memory_database_is_rejected():
    with pytest.raises(ValueError, match="durable SQLite file path"):
        SQLiteOidcApplicationSessionStore(":memory:")
