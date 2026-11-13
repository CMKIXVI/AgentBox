export type SessionCookiePolicy = {
  name: string;
  httpOnly: true;
  secure: boolean;
  sameSite: "lax";
  path: "/";
  maxAge: number;
};

const DEFAULT_SESSION_MAX_AGE_SECONDS = 60 * 60;
const MAX_SESSION_MAX_AGE_SECONDS = 8 * 60 * 60;
const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);
const ALLOWED_FETCH_SITES = new Set(["same-origin", "same-site"]);

/**
 * Returns cookie attributes only; it does not create, sign, store, or read a
 * session. Production uses the __Host- prefix, which requires Secure, Path=/,
 * and no Domain attribute.
 */
export function buildSessionCookiePolicy(
  options: { nodeEnv?: string; maxAgeSeconds?: number } = {},
): SessionCookiePolicy {
  const production = options.nodeEnv === "production";
  const maxAge = options.maxAgeSeconds ?? DEFAULT_SESSION_MAX_AGE_SECONDS;
  if (
    !Number.isInteger(maxAge) ||
    maxAge < 1 ||
    maxAge > MAX_SESSION_MAX_AGE_SECONDS
  ) {
    throw new RangeError("Session cookie lifetime must be between 1 second and 8 hours");
  }

  return {
    name: production ? "__Host-agentbox_session" : "agentbox_session",
    httpOnly: true,
    secure: production,
    sameSite: "lax",
    path: "/",
    maxAge,
  };
}

/** Same cookie scope and security attributes, with immediate expiry. */
export function buildClearedSessionCookiePolicy(
  options: { nodeEnv?: string } = {},
): SessionCookiePolicy {
  return {
    ...buildSessionCookiePolicy({ ...options, maxAgeSeconds: 1 }),
    maxAge: 0,
  };
}

/**
 * Parse an explicitly configured public web origin. Paths, credentials,
 * query strings, fragments, and non-local HTTP origins are rejected.
 */
export function parseTrustedWebOrigin(value: string | undefined): string | null {
  if (!value || value !== value.trim()) return null;
  try {
    const parsed = new URL(value);
    const localHttp =
      parsed.protocol === "http:" &&
      (parsed.hostname === "localhost" ||
        parsed.hostname === "127.0.0.1" ||
        parsed.hostname === "[::1]");
    if (
      (parsed.protocol !== "https:" && !localHttp) ||
      parsed.username ||
      parsed.password ||
      parsed.pathname !== "/" ||
      parsed.search ||
      parsed.hash ||
      parsed.origin !== value.replace(/\/$/, "")
    ) {
      return null;
    }
    return parsed.origin;
  } catch {
    return null;
  }
}

export type CsrfRequestLike = {
  method: string;
  headers: Pick<Headers, "get">;
};

/**
 * Strict Origin + Fetch Metadata check for state-changing BFF requests.
 * Call this before parsing or acting on a request body. This is not a
 * substitute for authentication, authorization, or per-operation checks.
 */
export function isCsrfRequestAllowed(
  request: CsrfRequestLike,
  configuredWebOrigin: string | undefined,
): boolean {
  const method = request.method.toUpperCase();
  if (SAFE_METHODS.has(method)) return true;

  const expectedOrigin = parseTrustedWebOrigin(configuredWebOrigin);
  if (!expectedOrigin) return false;

  const originHeader = request.headers.get("origin");
  if (!originHeader || originHeader !== expectedOrigin) return false;

  const fetchSite = request.headers.get("sec-fetch-site");
  if (fetchSite !== null && !ALLOWED_FETCH_SITES.has(fetchSite)) return false;

  return true;
}
