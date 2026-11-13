import NextAuth from "next-auth";

const issuer = process.env.AGENTBOX_OIDC_CLIENT_ISSUER;
const clientId = process.env.AGENTBOX_OIDC_WEB_CLIENT_ID;
const clientSecret = process.env.AGENTBOX_OIDC_WEB_CLIENT_SECRET;

export const oidcConfigured = Boolean(issuer && clientId && clientSecret && process.env.AUTH_SECRET);

const providers = oidcConfigured
  ? [{
      id: "agentbox-oidc",
      name: "AgentBox Identity",
      type: "oidc" as const,
      issuer,
      clientId,
      clientSecret,
      authorization: { params: { scope: process.env.AGENTBOX_OIDC_SCOPES ?? "openid profile email offline_access" } },
      checks: ["pkce", "state", "nonce"] as ["pkce", "state", "nonce"],
    }]
  : [];

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers,
  secret: process.env.AUTH_SECRET,
  session: { strategy: "jwt", maxAge: 30 * 60 },
  pages: { signIn: "/signin" },
  callbacks: {
    async jwt({ token, account }) {
      if (account) {
        token.agentboxAccessToken = account.access_token;
        token.agentboxRefreshToken = account.refresh_token;
        token.agentboxExpiresAt = account.expires_at;
        token.agentboxAuthError = undefined;
        return token;
      }

      if (typeof token.agentboxExpiresAt === "number" && Date.now() < token.agentboxExpiresAt * 1000 - 60_000) {
        return token;
      }
      if (typeof token.agentboxRefreshToken !== "string" || !token.agentboxRefreshToken || !issuer || !clientId || !clientSecret) {
        token.agentboxAuthError = "RefreshTokenUnavailable";
        return token;
      }

      try {
        const discoveryUrl = new URL(".well-known/openid-configuration", issuer.endsWith("/") ? issuer : issuer + "/");
        const discoveryResponse = await fetch(discoveryUrl, { cache: "no-store" });
        if (!discoveryResponse.ok) throw new Error("OIDC discovery failed");
        const discovery = (await discoveryResponse.json()) as { token_endpoint?: string };
        if (!discovery.token_endpoint) throw new Error("OIDC token endpoint is missing");

        const form = new URLSearchParams({
          grant_type: "refresh_token",
          refresh_token: token.agentboxRefreshToken,
        });
        const refreshResponse = await fetch(discovery.token_endpoint, {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
            Authorization: "Basic " + Buffer.from(clientId + ":" + clientSecret).toString("base64"),
          },
          body: form,
          cache: "no-store",
        });
        if (!refreshResponse.ok) throw new Error("OIDC token refresh failed");
        const refreshed = (await refreshResponse.json()) as { access_token?: string; refresh_token?: string; expires_in?: number };
        if (!refreshed.access_token) throw new Error("OIDC refresh returned no access token");

        token.agentboxAccessToken = refreshed.access_token;
        token.agentboxRefreshToken = refreshed.refresh_token ?? token.agentboxRefreshToken;
        token.agentboxExpiresAt = Math.floor(Date.now() / 1000) + (refreshed.expires_in ?? 300);
        token.agentboxAuthError = undefined;
      } catch {
        token.agentboxAuthError = "RefreshAccessTokenError";
      }
      return token;
    },
    // Never expose API access or refresh tokens to browser JavaScript.
    session({ session }) {
      return session;
    },
  },
});
