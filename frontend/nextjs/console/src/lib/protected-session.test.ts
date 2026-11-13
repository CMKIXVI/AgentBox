import assert from "node:assert/strict";
import test from "node:test";
import {
  AgentBoxUnauthenticatedError,
  requireAgentBoxSession,
} from "./protected-session.ts";

const now = 1_794_571_200;

test("protected server surface receives a valid session", async () => {
  const session = {
    subject: "user-1",
    accessToken: "short-lived-token",
    expiresAt: now + 300,
  };
  assert.deepEqual(
    await requireAgentBoxSession({ readSession: async () => session }, () => now),
    session,
  );
});

test("protected server surface rejects missing sessions", async () => {
  await assert.rejects(
    requireAgentBoxSession({ readSession: async () => null }, () => now),
    AgentBoxUnauthenticatedError,
  );
});

test("protected server surface rejects expired, near-expiry, and malformed sessions", async () => {
  const sessions = [
    { subject: "user-1", accessToken: "token", expiresAt: now - 1 },
    { subject: "user-1", accessToken: "token", expiresAt: now + 30 },
    { subject: " ", accessToken: "token", expiresAt: now + 300 },
    { subject: "user-1", accessToken: "", expiresAt: now + 300 },
    { subject: "user-1", accessToken: "token", expiresAt: Number.NaN },
  ];
  for (const session of sessions) {
    await assert.rejects(
      requireAgentBoxSession({ readSession: async () => session }, () => now),
      AgentBoxUnauthenticatedError,
    );
  }
});
