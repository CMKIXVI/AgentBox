import pytest

from app.oidc_client_registration import validate_oidc_client_registration


def web_client(**overrides):
    value = {
        "client_id": "agentbox-web",
        "platform": "web",
        "client_type": "confidential",
        "token_endpoint_auth_method": "private_key_jwt",
        "client_secret_ref": "vault://agentbox/oidc/web-client",
        "redirect_uris": ["https://console.example.test/auth/callback"],
        "post_logout_redirect_uris": ["https://console.example.test/"],
        "response_type": "code",
        "pkce_method": "S256",
    }
    value.update(overrides)
    return value


def native_client(**overrides):
    value = {
        "client_id": "agentbox-mobile",
        "platform": "native",
        "client_type": "public",
        "token_endpoint_auth_method": "none",
        "redirect_uris": ["com.example.agentbox://oauth/callback"],
        "post_logout_redirect_uris": ["com.example.agentbox://logout/callback"],
        "response_type": "code",
        "pkce_method": "S256",
    }
    value.update(overrides)
    return value


def registration(*clients):
    return {"schema_version": "1.0", "protocol": "oidc", "clients": list(clients)}


def test_valid_web_and_native_clients_are_accepted():
    assert validate_oidc_client_registration(
        registration(web_client(), native_client())
    ) == []


def test_missing_client_registration_is_rejected():
    assert validate_oidc_client_registration(
        {"schema_version": "1.0", "protocol": "oidc", "clients": []}
    )


def test_unknown_fields_reject_inline_client_secrets():
    client = web_client(client_secret="do-not-store")
    assert validate_oidc_client_registration(registration(client))


def test_duplicate_client_ids_are_rejected():
    assert any(
        "unique" in error["message"]
        for error in validate_oidc_client_registration(
            registration(native_client(), native_client())
        )
    )


@pytest.mark.parametrize(
    "uri",
    [
        "http://console.example.test/callback",
        "https://console.example.test/callback#fragment",
        "https://user:password@console.example.test/callback",
        "https://*.example.test/callback",
        "https:///missing-host",
    ],
)
def test_unsafe_web_redirect_uris_are_rejected(uri):
    errors = validate_oidc_client_registration(
        registration(web_client(redirect_uris=[uri]))
    )
    assert errors


def test_native_client_cannot_be_confidential_or_contain_secret_reference():
    client = native_client(
        client_type="confidential",
        token_endpoint_auth_method="client_secret_basic",
        client_secret_ref="vault://agentbox/mobile",
    )
    assert validate_oidc_client_registration(registration(client))


def test_native_client_rejects_dangerous_custom_schemes():
    client = native_client(redirect_uris=["javascript://callback"])
    assert validate_oidc_client_registration(registration(client))


def test_native_client_rejects_custom_uri_without_authority():
    client = native_client(redirect_uris=["agentbox:/callback"])
    assert validate_oidc_client_registration(registration(client))


def test_web_client_requires_server_side_secret_reference():
    client = web_client(client_secret_ref=None)
    assert validate_oidc_client_registration(registration(client))


def test_implicit_flow_and_plain_pkce_are_rejected_by_schema():
    client = web_client(response_type="token", pkce_method="plain")
    assert validate_oidc_client_registration(registration(client))


def test_logout_redirect_uris_are_validated_too():
    client = web_client(post_logout_redirect_uris=["https://console.example.test/#fragment"])
    assert validate_oidc_client_registration(registration(client))
