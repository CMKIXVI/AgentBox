import assert from "node:assert/strict";
import test from "node:test";
import { resolveSafeReturnTarget } from "./safe-return-target.ts";

test("preserves a safe root-relative path, query, and fragment", () => {
  assert.equal(
    resolveSafeReturnTarget("/agents/run-123?tab=traces#latest"),
    "/agents/run-123?tab=traces#latest",
  );
});

test("accepts the application root", () => {
  assert.equal(resolveSafeReturnTarget("/"), "/");
});

test("uses the safe root fallback for missing and non-string values", () => {
  for (const value of [null, undefined, "", 12, {}, false]) {
    assert.equal(resolveSafeReturnTarget(value), "/");
  }
});

test("rejects absolute URLs, including same-origin absolute URLs", () => {
  assert.equal(resolveSafeReturnTarget("https://evil.example/path"), "/");
  assert.equal(resolveSafeReturnTarget("https://agentbox.invalid/agents"), "/");
  assert.equal(resolveSafeReturnTarget("javascript:alert(1)"), "/");
});

test("rejects protocol-relative and triple-slash targets", () => {
  assert.equal(resolveSafeReturnTarget("//evil.example/path"), "/");
  assert.equal(resolveSafeReturnTarget("///evil.example/path"), "/");
});

test("rejects literal backslashes and whitespace-wrapped values", () => {
  assert.equal(resolveSafeReturnTarget("/\\\\evil.example/path"), "/");
  assert.equal(resolveSafeReturnTarget(" /agents"), "/");
});

test("rejects control characters and header-injection attempts", () => {
  assert.equal(resolveSafeReturnTarget("/agents\r\nLocation: https://evil.example"), "/");
  assert.equal(resolveSafeReturnTarget("/agents\u0000admin"), "/");
});

test("rejects encoded path separators and encoded backslashes", () => {
  assert.equal(resolveSafeReturnTarget("/%2f%2fevil.example"), "/");
  assert.equal(resolveSafeReturnTarget("/%5c%5cevil.example"), "/");
});

test("rejects raw and encoded dot-segment traversal", () => {
  assert.equal(resolveSafeReturnTarget("/agents/../admin"), "/");
  assert.equal(resolveSafeReturnTarget("/%2e%2e/admin"), "/");
  assert.equal(resolveSafeReturnTarget("/agents/%2E%2e/admin"), "/");
});

test("rejects malformed and nested percent-encoded path segments", () => {
  assert.equal(resolveSafeReturnTarget("/agents/%zz"), "/");
  assert.equal(resolveSafeReturnTarget("/%252f%252fevil.example"), "/");
});

test("validates the fallback instead of trusting an unsafe fallback", () => {
  assert.equal(
    resolveSafeReturnTarget("https://evil.example", "//evil.example"),
    "/",
  );
  assert.equal(
    resolveSafeReturnTarget(null, "/dashboard?view=recent"),
    "/dashboard?view=recent",
  );
});
