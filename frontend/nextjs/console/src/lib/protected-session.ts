import type { AgentBoxSession, SessionReader } from "./auth-session.ts";

/** Raised when a protected server-rendered surface has no usable session. */
export class AgentBoxUnauthenticatedError extends Error {
  constructor() {
    super("An authenticated AgentBox session is required");
    this.name = "AgentBoxUnauthenticatedError";
  }
}

/**
 * Server-component guard. The caller must supply a server-side SessionReader
 * backed by the selected OIDC/BFF adapter; no browser storage is consulted.
 */
export async function requireAgentBoxSession(
  sessionReader: SessionReader,
  now: () => number = () => Math.floor(Date.now() / 1000),
): Promise<AgentBoxSession> {
  const session = await sessionReader.readSession();
  if (
    !session ||
    !session.subject.trim() ||
    !session.accessToken ||
    !Number.isFinite(session.expiresAt) ||
    session.expiresAt <= now() + 30
  ) {
    throw new AgentBoxUnauthenticatedError();
  }
  return session;
}
