import assert from "node:assert/strict";
import test from "node:test";
import { AgentBoxApiClient } from "./agentbox-api.ts";
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


test("API client obtains bearer token through the session reader", async () => {
  let requested = false;
  const client = AgentBoxApiClient.fromSessionReader(
    "https://api.example.test",
    {
      readSession: async () => ({
        subject: "user-1",
        accessToken: "session-token",
        expiresAt: now + 300,
      }),
    },
    async (_input, init) => {
      requested = true;
      const headers = new Headers(init?.headers);
      assert.equal(headers.get("authorization"), "Bearer session-token");
      assert.equal(headers.has("x-tenant-id"), false);
      return new Response(JSON.stringify({ agent_id: "demo", items: [], limit: 50, offset: 0 }), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    },
    () => now,
  );
  const result = await client.listAgentVersions("demo");
  assert.equal(requested, true);
  assert.equal(result.agent_id, "demo");
});

test("API client does not send a request without a valid session", async () => {
  let requested = false;
  const client = AgentBoxApiClient.fromSessionReader(
    "https://api.example.test",
    { readSession: async () => null },
    async () => {
      requested = true;
      return new Response(null, { status: 500 });
    },
    () => now,
  );
  await assert.rejects(client.listAgentVersions("demo"), { status: 401 });
  assert.equal(requested, false);
});
