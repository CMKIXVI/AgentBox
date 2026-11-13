import NextAuth from "next-auth";

const issuer = process.env.AGENTBOX_OIDC_CLIENT_ISSUER;
const clientId = process.env.AGENTBOX_OIDC_WEB_CLIENT_ID;
const clientSecret = process.env.AGENTBOX_OIDC_WEB_CLIENT_SECRET;

export const oidcConfigured = Boolean(issuer && clientId && clientSecret);

const providers = oidcConfigured
  ? [
      {
        id: "agentbox-oidc",
        name: "AgentBox Identity",
        type: "oidc" as const,
        issuer,
        clientId,
        clientSecret,
        authorization: { params: { scope: "openid profile email" } },
        checks: ["pkce", "state"] as ["pkce", "state"],
      },
    ]
  : [];

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers,
  secret: process.env.AUTH_SECRET,
  session: { strategy: "jwt", maxAge: 30 * 60 },
  pages: { signIn: "/signin" },
  callbacks: {
    jwt({ token, account }) {
      if (account) {
        token.agentboxAccessToken = account.access_token;
        token.agentboxRefreshToken = account.refresh_token;
        token.agentboxExpiresAt = account.expires_at;
      }
      return token;
    },
    // Never expose API access or refresh tokens to browser JavaScript.
    session({ session }) {
      return session;
    },
  },
});
