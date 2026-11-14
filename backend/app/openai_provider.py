"""OpenAI-compatible chat-completions provider adapter using the Python standard library."""
from __future__ import annotations

import json
import math
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .execution import ProviderError, ProviderRequest, ProviderResponse


class OpenAICompatibleProvider:
    """Bounded HTTP adapter for providers exposing the OpenAI chat-completions API."""

    provider_id = "provider.openai"
    MAX_REQUEST_BYTES = 1024 * 1024
    MAX_RESPONSE_BYTES = 4 * 1024 * 1024

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        *,
        input_cost_per_million: float | None = None,
        output_cost_per_million: float | None = None,
    ) -> None:
        if not api_key or not api_key.strip():
            raise ValueError("A provider API key is required")
        parsed = urlsplit(base_url)
        if (
            parsed.scheme not in {"https", "http"}
            or not parsed.netloc
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Provider base URL must be an HTTP(S) origin/path without credentials or query")
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.input_cost_per_million = self._validate_rate(input_cost_per_million)
        self.output_cost_per_million = self._validate_rate(output_cost_per_million)

    @staticmethod
    def _validate_rate(value: float | None) -> float | None:
        if value is None:
            return None
        if isinstance(value, bool):
            raise TypeError("Provider token rates must be numeric, not boolean")
        rate = float(value)
        if not math.isfinite(rate) or rate < 0:
            raise ValueError("Provider token rates must be finite non-negative numbers")
        return rate

    @classmethod
    def from_environment(cls) -> OpenAICompatibleProvider | None:
        """Load provider configuration from process environment; never persist credentials."""
        api_key = os.getenv("AGENTBOX_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None
        base_url = os.getenv("AGENTBOX_OPENAI_BASE_URL", "https://api.openai.com/v1")
        input_rate = os.getenv("AGENTBOX_OPENAI_INPUT_USD_PER_MILLION")
        output_rate = os.getenv("AGENTBOX_OPENAI_OUTPUT_USD_PER_MILLION")
        return cls(
            api_key,
            base_url,
            input_cost_per_million=float(input_rate) if input_rate is not None else None,
            output_cost_per_million=float(output_rate) if output_rate is not None else None,
        )

    def invoke(self, request: ProviderRequest, timeout_seconds: int) -> ProviderResponse:
        if (
            type(timeout_seconds) is not int
            or not 1 <= timeout_seconds <= 3600
        ):
            raise ProviderError("Provider timeout is outside the supported range")
        try:
            user_content = (
                request.user_input
                if isinstance(request.user_input, str)
                else json.dumps(
                    request.user_input, ensure_ascii=False, allow_nan=False, separators=(",", ":")
                )
            )
        except (TypeError, ValueError, RecursionError):
            raise ProviderError("Provider input could not be serialized") from None
        payload = {
            "model": request.model_id,
            "messages": [
                {"role": "system", "content": request.objective},
                {"role": "user", "content": user_content},
            ],
            "max_tokens": request.max_output_tokens,
        }
        try:
            body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        except (TypeError, ValueError, UnicodeEncodeError, RecursionError):
            raise ProviderError("Provider request could not be encoded") from None
        if len(body) > self.MAX_REQUEST_BYTES:
            raise ProviderError("Provider request exceeded the configured size limit")
        http_request = Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        # urllib deliberately omits unredirected headers when constructing a
        # redirected request. Never forward bearer credentials to another host.
        http_request.add_unredirected_header(
            "Authorization", f"Bearer {self.api_key}"
        )
        try:
            with urlopen(http_request, timeout=timeout_seconds) as response:
                raw = response.read(self.MAX_RESPONSE_BYTES + 1)
                if len(raw) > self.MAX_RESPONSE_BYTES:
                    raise ProviderError("Provider response exceeded the configured size limit")
                document = json.loads(
                    raw,
                    parse_constant=lambda _value: (_ for _ in ()).throw(
                        ValueError("non-standard JSON numeric constant")
                    ),
                )
        except HTTPError as exc:
            # Do not include response bodies or request headers; they can contain secrets.
            raise ProviderError(f"Provider returned HTTP status {exc.code}") from None
        except (URLError, TimeoutError, OSError):
            raise ProviderError("Provider request failed or timed out") from None
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            raise ProviderError("Provider returned invalid JSON") from None

        if not isinstance(document, dict):
            raise ProviderError("Provider response did not match the chat-completions contract")
        choices = document.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            raise ProviderError("Provider response did not match the chat-completions contract")
        message = choices[0].get("message")
        if not isinstance(message, dict):
            raise ProviderError("Provider response did not match the chat-completions contract")
        output = message.get("content")
        usage = document.get("usage", {})
        if usage is None:
            usage = {}
        if not isinstance(usage, dict):
            raise ProviderError("Provider response did not match the chat-completions contract")
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        if not isinstance(output, str):
            raise ProviderError("Provider returned invalid message content")
        if (
            type(input_tokens) is not int
            or type(output_tokens) is not int
            or input_tokens < 0
            or output_tokens < 0
        ):
            raise ProviderError("Provider returned invalid token usage")

        cost_usd: float | None = None
        if self.input_cost_per_million is not None and self.output_cost_per_million is not None:
            try:
                cost_usd = (
                    input_tokens * self.input_cost_per_million
                    + output_tokens * self.output_cost_per_million
                ) / 1_000_000
            except OverflowError:
                raise ProviderError(
                    "Provider returned usage that exceeds supported cost bounds"
                ) from None
            if not math.isfinite(cost_usd):
                raise ProviderError("Provider returned usage that exceeds supported cost bounds")
        return ProviderResponse(
            output=output,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
        )
