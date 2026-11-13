import pytest

from app.oidc_callback_contract import (
    OidcCallbackTransaction,
    is_registered_redirect_uri,
    validate_callback_transaction,
)


@pytest.fixture
def registration():
    return {
        "clients": [
            {
                "client_id": "agentbox-web",
                "redirect_uris": ["https://console.example.test/auth/callback"],
                "post_logout_redirect_uris": ["https://console.example.test/"],
            },
            {
                "client_id": "agentbox-mobile",
                "redirect_uris": ["com.example.agentbox://oauth/callback"],
            },
        ]
    }


def test_redirect_uri_requires_exact_client_specific_match(registration):
    assert is_registered_redirect_uri(
        registration, "agentbox-web", "https://console.example.test/auth/callback"
    )
    assert not is_registered_redirect_uri(
        registration, "agentbox-web", "https://console.example.test/auth/callback/extra"
    )
    assert not is_registered_redirect_uri(
        registration, "agentbox-web", "https://CONSOLE.example.test/auth/callback"
    )
    assert not is_registered_redirect_uri(
        registration, "agentbox-mobile", "https://console.example.test/auth/callback"
    )


def test_logout_redirect_uses_separate_allowlist(registration):
    assert is_registered_redirect_uri(
        registration, "agentbox-web", "https://console.example.test/", post_logout=True
    )
    assert not is_registered_redirect_uri(
        registration, "agentbox-web", "https://console.example.test/auth/callback",
        post_logout=True,
    )


def test_unknown_or_duplicate_client_id_fails_closed(registration):
    assert not is_registered_redirect_uri(registration, "unknown", "https://x.test/cb")
    registration["clients"].append(registration["clients"][0])
    assert not is_registered_redirect_uri(
        registration, "agentbox-web", "https://console.example.test/auth/callback"
    )


def valid_transaction(**overrides):
    values = {
        "transaction_id": "txn-123",
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


def test_valid_short_lived_transaction_is_accepted():
    assert validate_callback_transaction(valid_transaction()) == []


@pytest.mark.parametrize(
    "changes",
    [
        {"state_hash": "raw-state-value"},
        {"nonce_hash": "A" * 64},
        {"pkce_verifier_ref": ""},
        {"expires_at_epoch": 1000},
        {"expires_at_epoch": 1601},
        {"client_id": ""},
        {"redirect_uri": ""},
    ],
)
def test_invalid_transaction_is_rejected(changes):
    assert validate_callback_transaction(valid_transaction(**changes))


def test_transaction_rejects_boolean_timestamps():
    assert validate_callback_transaction(valid_transaction(created_at_epoch=True))
