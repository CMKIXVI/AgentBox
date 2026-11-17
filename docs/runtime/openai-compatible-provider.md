# OpenAI-compatible provider adapter

AgentBox now includes an optional HTTP adapter for chat-completions-compatible
providers. The adapter is implemented with Python's standard library and is
registered only when a provider key is configured.

## Configuration

Set these values in the API and worker process environments (or inject them
through the deployment secret manager):

- `AGENTBOX_OPENAI_API_KEY`: provider credential. `OPENAI_API_KEY` is accepted
  as a compatibility fallback.
- `AGENTBOX_OPENAI_BASE_URL`: API base URL; defaults to
  `https://api.openai.com/v1`. HTTP(S) only; embedded credentials, query and
  fragment are rejected.
- `AGENTBOX_OPENAI_INPUT_USD_PER_MILLION`: optional input-token price.
- `AGENTBOX_OPENAI_OUTPUT_USD_PER_MILLION`: optional output-token price.

The model binding in the agent manifest must use provider ID
`provider.openai` and a model ID supported by the configured endpoint. Do not
place credentials in manifests, source control, or client requests.

If no key is configured, the provider is not registered and provider execution
fails closed. A missing price rate is represented as `cost_usd: null`; AgentBox
does not invent a price. Cost is calculated only when both rates are explicitly
configured.

## Runtime safeguards

- HTTPS is the default; an explicitly configured HTTP endpoint is permitted for
  controlled local/private gateways and must be protected by deployment network
  policy.
- Request timeout is inherited from the manifest behavior and bounded to
  1–3600 seconds by the adapter.
- Serialized provider request bodies are limited to 1 MiB.
- Provider response bodies are limited to 4 MiB.
- Bearer credentials are marked as unredirected headers so urllib does not forward them to a redirect target.
- HTTP, transport and malformed-response errors are converted to sanitized
  provider errors; response bodies and authorization headers are not logged or
  returned to tenants.
- Provider usage token counts are returned when the provider supplies them.
- This adapter currently supports the OpenAI chat-completions request/response
  shape, not every provider-specific API extension.

## Interrupted synchronous executions

The synchronous execution store is SQLite single-instance. On exclusive process
startup, any execution still marked `running` is changed to `interrupted` with
error code `execution_interrupted_ambiguous_outcome`. This is intentionally
conservative: a process may have died after the provider completed the request,
so an idempotent API replay returns the interrupted record and does not invoke
the provider again. Operators must reconcile the provider-side outcome before
submitting a new request with a new idempotency key.

Do not run multiple API processes against this SQLite execution store. Startup
recovery assumes the previous process has stopped; a multi-instance deployment
requires a database-backed lease/ownership design before enabling this behavior.

## Verification boundary

CI uses mocked HTTP responses; it does not contact a live provider, validate
credentials, establish model availability, verify current provider pricing, or
prove production latency/retry behavior. No API key is stored in the repository.
