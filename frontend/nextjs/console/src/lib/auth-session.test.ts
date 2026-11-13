import assert from "node:assert/strict";
import test from "node:test";
import { createAccessTokenProvider } from "./auth-session.ts";

const now = 1_794_571_200;

test("returns access token for a valid session", async () => {
  const provider = createAccessTokenProvider({
    readSession: async () => ({
      subject: "user-1",
      accessToken: "short-lived-token",
      expiresAt: now + 300,
    }),
  }, () => now);
  assert.equal(await provider(), "short-lived-token");
});

test("fails closed for a missing session", async () => {
  const provider = createAccessTokenProvider({ readSession: async () => null }, () => now);
  assert.equal(await provider(), null);
});

test("rejects expired, near-expiry, and incomplete sessions", async () => {
  const sessions = [
    { subject: "user-1", accessToken: "token", expiresAt: now - 1 },
    { subject: "user-1", accessToken: "token", expiresAt: now + 30 },
    { subject: "", accessToken: "token", expiresAt: now + 300 },
    { subject: "user-1", accessToken: "", expiresAt: now + 300 },
    { subject: "user-1", accessToken: "token", expiresAt: Number.NaN },
  ];
  for (const session of sessions) {
    const provider = createAccessTokenProvider({ readSession: async () => session }, () => now);
    assert.equal(await provider(), null);
  }
});
