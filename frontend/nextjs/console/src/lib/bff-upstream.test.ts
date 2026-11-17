import assert from "node:assert/strict";
import test from "node:test";
import {
  filterBffForwardHeaders,
  isBffRequestBodyAllowed,
  parseBffBackendOrigin,
  resolveBffUpstreamTarget,
} from "./bff-upstream.ts";

const backend = "https://api.agentbox.example";

test("backend origin accepts HTTPS and local development origins", () => {
  assert.equal(parseBffBackendOrigin(backend), backend);
  assert.equal(parseBffBackendOrigin("http://localhost:8000"), "http://localhost:8000");
});

test("backend origin rejects arbitrary, credentialed, and non-origin URLs", () => {
  for (const value of [
    undefined,
    "",
    "http://api.agentbox.example",
    "https://user:secret@api.agentbox.example",
    "https://api.agentbox.example/path",
    "https://api.agentbox.example?next=evil",
    "https://api.agentbox.example#fragment",
    " https://api.agentbox.example",
  ]) {
    assert.equal(parseBffBackendOrigin(value), null);
  }
});

test("existing AgentBox health endpoint is allowlisted for GET only", () => {
  assert.equal(resolveBffUpstreamTarget("/health", "", "GET", backend), `${backend}/health`);
  assert.equal(resolveBffUpstreamTarget("/health", "", "POST", backend), null);
});

test("agent creation is allowlisted for POST only", () => {
  assert.equal(resolveBffUpstreamTarget("/v1/agents", "", "POST", backend), `${backend}/v1/agents`);
  assert.equal(resolveBffUpstreamTarget("/v1/agents", "", "GET", backend), null);
});

test("agent version collection and detail reads are allowlisted", () => {
  assert.equal(
    resolveBffUpstreamTarget("/v1/agents/agent-1/versions", "?limit=50&offset=0", "GET", backend),
    `${backend}/v1/agents/agent-1/versions?limit=50&offset=0`,
  );
  assert.equal(
    resolveBffUpstreamTarget("/v1/agents/agent-1/versions/v1", "", "GET", backend),
    `${backend}/v1/agents/agent-1/versions/v1`,
  );
});

test("execution detail reads are allowlisted", () => {
  assert.equal(
    resolveBffUpstreamTarget("/v1/executions/run-1", "", "GET", backend),
    `${backend}/v1/executions/run-1`,
  );
});

test("unlisted API paths and methods fail closed", () => {
  for (const [path, method] of [
    ["/v1/users", "GET"],
    ["/v1/agents/agent-1", "DELETE"],
    ["/v1/executions", "GET"],
    ["/admin", "POST"],
    ["/health", "DELETE"],
  ]) {
    assert.equal(resolveBffUpstreamTarget(path, "", method, backend), null);
  }
});

test("path traversal, encoded separators, backslashes, and malformed encodings are rejected", () => {
  for (const path of [
    "/../health",
    "/%2e%2e/health",
    "/health%2fadmin",
    "/health%5cadmin",
    "/health\\admin",
    "/%252e%252e/health",
    "/v1/agents/%ZZ/versions",
  ]) {
    assert.equal(resolveBffUpstreamTarget(path, "", "GET", backend), null);
  }
});

test("version collection query accepts only bounded unique pagination fields", () => {
  assert.equal(
    resolveBffUpstreamTarget("/v1/agents/a/versions", "?limit=100&offset=1000000", "GET", backend),
    `${backend}/v1/agents/a/versions?limit=100&offset=1000000`,
  );
  for (const query of [
    "?admin=true",
    "?limit=101",
    "?limit=0",
    "?offset=-1",
    "?offset=1000001",
    "?limit=5&limit=6",
    "?limit=1.5",
  ]) {
    assert.equal(resolveBffUpstreamTarget("/v1/agents/a/versions", query, "GET", backend), null);
  }
});

test("query strings are rejected on every other endpoint", () => {
  assert.equal(resolveBffUpstreamTarget("/health", "?debug=true", "GET", backend), null);
  assert.equal(resolveBffUpstreamTarget("/v1/agents", "?tenant=other", "POST", backend), null);
});

test("unconfigured backend origin fails closed", () => {
  assert.equal(resolveBffUpstreamTarget("/health", "", "GET", undefined), null);
});

test("forwarded headers use a positive allowlist", () => {
  const input = new Headers({
    accept: "application/json",
    "content-type": "application/json",
    authorization: "Bearer attacker-token",
    cookie: "agentbox_session=attacker",
    "x-tenant-id": "tenant-victim",
    "x-user-id": "admin",
    "x-forwarded-for": "127.0.0.1",
    host: "internal.example",
  });
  const output = filterBffForwardHeaders(input);
  assert.equal(output.get("accept"), "application/json");
  assert.equal(output.get("content-type"), "application/json");
  for (const name of ["authorization", "cookie", "x-tenant-id", "x-user-id", "x-forwarded-for", "host"]) {
    assert.equal(output.has(name), false);
  }
});

test("body policy permits only JSON POST bodies and bodyless safe methods", () => {
  assert.equal(isBffRequestBodyAllowed("POST", true, "application/json"), true);
  assert.equal(isBffRequestBodyAllowed("POST", true, "application/json; charset=utf-8"), true);
  assert.equal(isBffRequestBodyAllowed("POST", true, "text/plain"), false);
  assert.equal(isBffRequestBodyAllowed("POST", false, "application/json"), false);
  assert.equal(isBffRequestBodyAllowed("GET", false, null), true);
  assert.equal(isBffRequestBodyAllowed("GET", true, "application/json"), false);
  assert.equal(isBffRequestBodyAllowed("DELETE", true, "application/json"), false);
});
