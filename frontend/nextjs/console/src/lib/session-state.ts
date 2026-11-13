import type { AgentBoxSession } from "./auth-session.ts";

export type SessionState =
  | { status: "authenticated"; session: AgentBoxSession }
  | { status: "unauthenticated" };

const EXPIRY_SKEW_SECONDS = 30;
const MAX_TIMEOUT_MS = 2_147_000_000;

/** Resolve a read-only session into a fail-closed UI state. */
export function resolveSessionState(
  session: AgentBoxSession | null,
  now: number = Math.floor(Date.now() / 1000),
): SessionState {
  if (
    !session ||
    !session.subject ||
    !session.accessToken ||
    !Number.isFinite(session.expiresAt) ||
    session.expiresAt <= now + EXPIRY_SKEW_SECONDS
  ) {
    return { status: "unauthenticated" };
  }
  return { status: "authenticated", session };
}

/** Milliseconds until the gate must re-read the session, capped to timer limits. */
export function sessionRecheckDelayMs(
  expiresAt: number,
  nowMs: number = Date.now(),
): number {
  if (!Number.isFinite(expiresAt) || !Number.isFinite(nowMs)) return 0;
  const remaining = expiresAt * 1000 - nowMs - EXPIRY_SKEW_SECONDS * 1000;
  return Math.min(Math.max(0, remaining), MAX_TIMEOUT_MS);
}
