import assert from "node:assert/strict";
import test from "node:test";
import {
  buildClearedSessionCookiePolicy,
  buildSessionCookiePolicy,
  isCsrfRequestAllowed,
  parseTrustedWebOrigin,
} from "./bff-security.ts";

function request(
  method: string,
  headers: Record<string, string> = {},
): { method: string; headers: Headers } {
  return { method, headers: new Headers(headers) };
}

test("production session cookie uses the __Host- prefix and secure attributes", () => {
  assert.deepEqual(buildSessionCookiePolicy({ nodeEnv: "production" }), {
    name: "__Host-agentbox_session",
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    path: "/",
    maxAge: 3600,
  });
});

test("development cookie is usable on local HTTP without weakening production", () => {
  const policy = buildSessionCookiePolicy({ nodeEnv: "development" });
  assert.equal(policy.name, "agentbox_session");
  assert.equal(policy.secure, false);
  assert.equal(policy.httpOnly, true);
  assert.equal(policy.sameSite, "lax");
  assert.equal(policy.path, "/");
});

test("cookie lifetime is bounded to eight hours", () => {
  assert.equal(buildSessionCookiePolicy({ maxAgeSeconds: 8 * 60 * 60 }).maxAge, 28800);
  for (const maxAgeSeconds of [0, -1, 1.5, 28801, Number.NaN]) {
    assert.throws(
      () => buildSessionCookiePolicy({ maxAgeSeconds }),
      RangeError,
    );
  }
});

test("clearing cookie preserves production scope and expires immediately", () => {
  assert.deepEqual(buildClearedSessionCookiePolicy({ nodeEnv: "production" }), {
    name: "__Host-agentbox_session",
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    path: "/",
    maxAge: 0,
  });
});

test("trusted origin accepts HTTPS origins and local development HTTP", () => {
  assert.equal(parseTrustedWebOrigin("https://console.example.com"), "https://console.example.com");
  assert.equal(parseTrustedWebOrigin("http://localhost:3000"), "http://localhost:3000");
});

test("trusted origin rejects missing, malformed, and non-origin values", () => {
  for (const value of [
    undefined,
    "",
    " https://console.example.com",
    "http://console.example.com",
    "https://user:pass@console.example.com",
    "https://console.example.com/path",
    "https://console.example.com?x=1",
    "https://console.example.com#fragment",
    "not a url",
  ]) {
    assert.equal(parseTrustedWebOrigin(value), null);
  }
});

test("safe methods do not require CSRF headers", () => {
  for (const method of ["GET", "HEAD", "OPTIONS", "get"]) {
    assert.equal(isCsrfRequestAllowed(request(method), undefined), true);
  }
});

test("state-changing requests require the exact configured Origin", () => {
  const expected = "https://console.example.com";
  assert.equal(
    isCsrfRequestAllowed(request("POST", { origin: expected }), expected),
    true,
  );
  assert.equal(isCsrfRequestAllowed(request("POST"), expected), false);
  assert.equal(
    isCsrfRequestAllowed(request("POST", { origin: "https://evil.example" }), expected),
    false,
  );
  assert.equal(
    isCsrfRequestAllowed(request("DELETE", { origin: "null" }), expected),
    false,
  );
});

test("state-changing requests fail closed when the trusted origin is absent or invalid", () => {
  assert.equal(
    isCsrfRequestAllowed(request("POST", { origin: "https://console.example.com" }), undefined),
    false,
  );
  assert.equal(
    isCsrfRequestAllowed(
      request("POST", { origin: "https://console.example.com" }),
      "http://console.example.com",
    ),
    false,
  );
});

test("Fetch Metadata rejects cross-site and none contexts", () => {
  const origin = "https://console.example.com";
  assert.equal(
    isCsrfRequestAllowed(
      request("POST", { origin, "sec-fetch-site": "cross-site" }),
      origin,
    ),
    false,
  );
  assert.equal(
    isCsrfRequestAllowed(
      request("POST", { origin, "sec-fetch-site": "none" }),
      origin,
    ),
    false,
  );
});

test("Fetch Metadata accepts same-origin and exact-origin same-site requests", () => {
  const origin = "https://console.example.com";
  for (const fetchSite of ["same-origin", "same-site"]) {
    assert.equal(
      isCsrfRequestAllowed(
        request("PATCH", { origin, "sec-fetch-site": fetchSite }),
        origin,
      ),
      true,
    );
  }
});
