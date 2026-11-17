import type { AgentBoxSession } from "./auth-session.ts";

export type SessionState =
  | { status: "authenticated"; session: AgentBoxSession }
  | { status: "unauthenticated" };

const EXPIRY_SKEW_SECONDS = 30;

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
