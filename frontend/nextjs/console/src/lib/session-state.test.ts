import assert from "node:assert/strict";
import test from "node:test";
import {
  resolveSessionState,
  sessionRecheckDelayMs,
} from "./session-state.ts";

const now = 1_794_571_200;
const validSession = {
  subject: "user-1",
  accessToken: "short-lived-token",
  expiresAt: now + 300,
};

test("allows a valid session to render protected content", () => {
  assert.deepEqual(resolveSessionState(validSession, now), {
    status: "authenticated",
    session: validSession,
  });
});

test("fails closed for missing, incomplete, expired, and near-expiry sessions", () => {
  const invalidSessions = [
    null,
    { ...validSession, subject: "" },
    { ...validSession, accessToken: "" },
    { ...validSession, expiresAt: now - 1 },
    { ...validSession, expiresAt: now + 30 },
    { ...validSession, expiresAt: Number.NaN },
  ];
  for (const session of invalidSessions) {
    assert.deepEqual(resolveSessionState(session, now), {
      status: "unauthenticated",
    });
  }
});

test("rechecks a session 30 seconds before expiry", () => {
  assert.equal(sessionRecheckDelayMs(now + 300, now * 1000), 270_000);
});

test("rechecks immediately when expiry is inside the safety window", () => {
  assert.equal(sessionRecheckDelayMs(now + 20, now * 1000), 0);
});

test("caps long session delays to the platform timer limit", () => {
  assert.equal(sessionRecheckDelayMs(now + 100_000_000, now * 1000), 2_147_000_000);
});

test("invalid expiry values fail closed with an immediate recheck", () => {
  assert.equal(sessionRecheckDelayMs(Number.NaN, now * 1000), 0);
});
