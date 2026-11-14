from __future__ import annotations

import io
import json
from urllib.error import HTTPError, URLError

import pytest

from app.execution import ProviderError, ProviderRequest
from app.openai_provider import OpenAICompatibleProvider


def request():
    return ProviderRequest(
        provider_id="provider.openai",
        model_id="example-model",
        objective="Answer accurately",
        user_input={"question": "hello"},
        max_output_tokens=64,
    )


class FakeHTTPResponse:
    def __init__(self, document: dict):
        self.body = json.dumps(document).encode()
    def __enter__(self):
        return self
    def __exit__(self, *_args):
        return None
    def read(self, size=-1):
        return self.body[:size]


def test_invokes_chat_completions_and_reports_usage_and_configured_cost(monkeypatch):
    captured = {}
    def fake_urlopen(http_request, timeout):
        captured["url"] = http_request.full_url
        captured["headers"] = dict(http_request.header_items())
        captured["timeout"] = timeout
        captured["body"] = json.loads(http_request.data)
        return FakeHTTPResponse({
            "choices": [{"message": {"content": "Hello from provider"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        })
    monkeypatch.setattr("app.openai_provider.urlopen", fake_urlopen)
    adapter = OpenAICompatibleProvider(
        "secret-token",
        input_cost_per_million=2.0,
        output_cost_per_million=8.0,
    )
    result = adapter.invoke(request(), 12)
    assert captured["url"] == "https://api.openai.com/v1/chat/completions"
    assert captured["timeout"] == 12
    assert captured["headers"]["Authorization"] == "Bearer secret-token"
    assert captured["body"]["model"] == "example-model"
    assert captured["body"]["messages"][0]["content"] == "Answer accurately"
    assert captured["body"]["messages"][1]["content"] == '{"question":"hello"}'
    assert result.output == "Hello from provider"
    assert result.input_tokens == 10
    assert result.output_tokens == 5
    assert result.cost_usd == pytest.approx(0.00006)


def test_cost_is_unknown_when_rates_are_not_configured(monkeypatch):
    monkeypatch.setattr(
        "app.openai_provider.urlopen",
        lambda *_args, **_kwargs: FakeHTTPResponse({
            "choices": [{"message": {"content": "ok"}}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 2},
        }),
    )
    result = OpenAICompatibleProvider("secret").invoke(request(), 5)
    assert result.cost_usd is None


def test_http_error_is_sanitized_and_does_not_expose_response_body(monkeypatch):
    def fail(*_args, **_kwargs):
        raise HTTPError("https://example.test", 429, "rate limited", {}, io.BytesIO(b"secret"))
    monkeypatch.setattr("app.openai_provider.urlopen", fail)
    with pytest.raises(ProviderError, match="HTTP status 429") as error:
        OpenAICompatibleProvider("secret").invoke(request(), 5)
    assert "secret" not in str(error.value)


def test_transport_failure_is_reported_without_secret(monkeypatch):
    monkeypatch.setattr(
        "app.openai_provider.urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(URLError("network down")),
    )
    with pytest.raises(ProviderError, match="failed or timed out"):
        OpenAICompatibleProvider("secret").invoke(request(), 5)


def test_rejects_invalid_provider_urls_and_rates():
    with pytest.raises(ValueError):
        OpenAICompatibleProvider("secret", "file:///tmp/provider")
    with pytest.raises(ValueError):
        OpenAICompatibleProvider("secret", "https://user:pass@example.test/v1")
    with pytest.raises(ValueError):
        OpenAICompatibleProvider("secret", input_cost_per_million=-1)


def test_environment_configuration_is_optional_and_does_not_require_credentials(monkeypatch):
    monkeypatch.delenv("AGENTBOX_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert OpenAICompatibleProvider.from_environment() is None


def test_environment_configuration_loads_provider_without_printing_secret(monkeypatch):
    monkeypatch.setenv("AGENTBOX_OPENAI_API_KEY", "env-secret")
    monkeypatch.setenv("AGENTBOX_OPENAI_BASE_URL", "https://gateway.example/v1")
    adapter = OpenAICompatibleProvider.from_environment()
    assert adapter is not None
    assert adapter.base_url == "https://gateway.example/v1"
    assert adapter.api_key == "env-secret"


def test_rejects_timeout_outside_supported_bounds():
    adapter = OpenAICompatibleProvider("secret")
    with pytest.raises(ProviderError, match="timeout"):
        adapter.invoke(request(), 0)
