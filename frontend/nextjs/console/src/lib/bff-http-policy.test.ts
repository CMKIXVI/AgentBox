import assert from "node:assert/strict";
import test from "node:test";
import {
  buildBffFetchPolicy,
  buildBffPolicyError,
  createBffRequestId,
  filterBffResponseHeaders,
  isBffUpstreamResponseAllowed,
  MAX_BFF_REQUEST_BYTES,
  MAX_BFF_RESPONSE_BYTES,
  validateBffRequestEnvelope,
} from "./bff-http-policy.ts";

const webOrigin = "https://console.agentbox.example";

function request(method: string, headers: Record<string, string> = {}) {
  return new Request(webOrigin + "/api/agents", {
    method,
    headers: new Headers(headers),
  });
}

test("CSRF metadata is checked before request body policy", () => {
  const result = validateBffRequestEnvelope({
    request: request("POST", { "content-type": "application/json", "content-length": "2" }),
    hasBody: true,
    configuredWebOrigin: webOrigin,
  });
  assert.deepEqual(result, { allowed: false, reason: "csrf" });
});

test("state-changing requests require exact origin and acceptable fetch metadata", () => {
  const headers = {
    origin: webOrigin,
    "sec-fetch-site": "same-origin",
    "content-type": "application/json",
    "content-length": "2",
  };
  assert.deepEqual(validateBffRequestEnvelope({
    request: request("POST", headers), hasBody: true, configuredWebOrigin: webOrigin,
  }), { allowed: true });
  assert.deepEqual(validateBffRequestEnvelope({
    request: request("POST", { ...headers, "sec-fetch-site": "cross-site" }),
    hasBody: true, configuredWebOrigin: webOrigin,
  }), { allowed: false, reason: "csrf" });
});

test("body-bearing requests require JSON and a declared bounded length", () => {
  const base = { origin: webOrigin, "content-type": "application/json", "content-length": "12" };
  assert.deepEqual(validateBffRequestEnvelope({
    request: request("POST", base), hasBody: true, configuredWebOrigin: webOrigin,
  }), { allowed: true });
  assert.deepEqual(validateBffRequestEnvelope({
    request: request("POST", { ...base, "content-length": String(MAX_BFF_REQUEST_BYTES + 1) }),
    hasBody: true, configuredWebOrigin: webOrigin,
  }), { allowed: false, reason: "content-length" });
  assert.deepEqual(validateBffRequestEnvelope({
    request: request("POST", { origin: webOrigin, "content-type": "text/plain", "content-length": "12" }),
    hasBody: true, configuredWebOrigin: webOrigin,
  }), { allowed: false, reason: "content-type" });
  assert.deepEqual(validateBffRequestEnvelope({
    request: request("POST", { ...base, "content-length": "12x" }),
    hasBody: true, configuredWebOrigin: webOrigin,
  }), { allowed: false, reason: "content-length" });
});

test("bodyless safe reads do not require CSRF metadata or a content length", () => {
  assert.deepEqual(validateBffRequestEnvelope({
    request: request("GET"), hasBody: false, configuredWebOrigin: webOrigin,
  }), { allowed: true });
});

test("upstream redirects are never relayed", () => {
  for (const status of [300, 301, 302, 303, 307, 308]) {
    assert.equal(isBffUpstreamResponseAllowed(status, "application/json", "0"), false);
  }
});

test("upstream responses accept JSON and problem JSON only", () => {
  assert.equal(isBffUpstreamResponseAllowed(200, "application/json; charset=utf-8", "10"), true);
  assert.equal(isBffUpstreamResponseAllowed(422, "application/problem+json", "10"), true);
  assert.equal(isBffUpstreamResponseAllowed(200, "text/html", "10"), false);
  assert.equal(isBffUpstreamResponseAllowed(200, null, "10"), false);
});

test("upstream response declared lengths are bounded and well formed", () => {
  assert.equal(isBffUpstreamResponseAllowed(200, "application/json", String(MAX_BFF_RESPONSE_BYTES)), true);
  assert.equal(isBffUpstreamResponseAllowed(200, "application/json", String(MAX_BFF_RESPONSE_BYTES + 1)), false);
  assert.equal(isBffUpstreamResponseAllowed(200, "application/json", "unknown"), false);
});

test("bodyless no-content responses are supported", () => {
  assert.equal(isBffUpstreamResponseAllowed(204, null, null), true);
  assert.equal(isBffUpstreamResponseAllowed(204, null, "0"), true);
  assert.equal(isBffUpstreamResponseAllowed(204, null, "1"), false);
});

test("response headers discard cookies, cache directives, and infrastructure details", () => {
  const filtered = filterBffResponseHeaders(new Headers({
    "content-type": "application/json",
    "set-cookie": "session=secret",
    "cache-control": "public, max-age=3600",
    server: "internal",
    "x-powered-by": "framework",
    location: "https://internal.example",
  }));
  assert.equal(filtered.get("content-type"), "application/json");
  assert.equal(filtered.get("cache-control"), "no-store, max-age=0");
  assert.equal(filtered.get("pragma"), "no-cache");
  assert.equal(filtered.get("x-content-type-options"), "nosniff");
  for (const name of ["set-cookie", "server", "x-powered-by", "location"]) {
    assert.equal(filtered.has(name), false);
  }
});

test("fetch policy disables caches, redirects, and ambient credentials", () => {
  assert.deepEqual(buildBffFetchPolicy(), {
    cache: "no-store", redirect: "manual", credentials: "omit",
  });
});

test("request IDs are generated server-side in UUID form", () => {
  assert.match(createBffRequestId(), /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i);
});

test("policy errors have a stable non-sensitive no-store JSON envelope", async () => {
  const response = buildBffPolicyError(413, "request_too_large", "req-123");
  assert.equal(response.status, 413);
  assert.match(response.headers.get("cache-control") ?? "", /no-store/);
  assert.deepEqual(await response.json(), {
    error: { code: "request_too_large", requestId: "req-123" },
  });
});
