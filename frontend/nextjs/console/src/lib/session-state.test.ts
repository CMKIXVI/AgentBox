import assert from "node:assert/strict";
import test from "node:test";
import { resolveSessionState } from "./session-state.ts";

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
