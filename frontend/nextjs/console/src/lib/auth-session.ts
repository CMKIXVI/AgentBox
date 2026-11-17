/**
 * Provider-neutral boundary for a standards-compliant OIDC session adapter.
 * No OAuth/OIDC, cookies, token refresh, or credential persistence is implemented here.
 */
export type AgentBoxSession = {
  subject: string;
  accessToken: string;
  expiresAt: number;
  displayName?: string;
};
export type SessionReader = { readSession(): Promise<AgentBoxSession | null> };
const EXPIRY_SKEW_SECONDS = 30;
export function createAccessTokenProvider(
  sessionReader: SessionReader,
  now: () => number = () => Math.floor(Date.now() / 1000),
): () => Promise<string | null> {
  return async () => {
    const session = await sessionReader.readSession();
    if (!session || !session.subject || !session.accessToken) return null;
    if (!Number.isFinite(session.expiresAt) || session.expiresAt <= now() + EXPIRY_SKEW_SECONDS) return null;
    return session.accessToken;
  };
}
