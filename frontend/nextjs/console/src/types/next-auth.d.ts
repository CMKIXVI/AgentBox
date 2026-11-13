import "next-auth/jwt";

declare module "next-auth/jwt" {
  interface JWT {
    agentboxAccessToken?: string;
    agentboxRefreshToken?: string;
    agentboxExpiresAt?: number;
  }
}
