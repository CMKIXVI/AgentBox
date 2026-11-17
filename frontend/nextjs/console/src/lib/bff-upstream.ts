const API_ROUTE_RULES = [
  { pattern: /^\/health$/, methods: ["GET"] },
  { pattern: /^\/v1\/agents$/, methods: ["POST"] },
  { pattern: /^\/v1\/agents\/[^/]+\/versions$/, methods: ["GET"] },
  { pattern: /^\/v1\/agents\/[^/]+\/versions\/[^/]+$/, methods: ["GET"] },
  { pattern: /^\/v1\/executions\/[^/]+$/, methods: ["GET"] },
] as const;

const FORWARDED_REQUEST_HEADERS = ["accept", "content-type"] as const;
const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);

/** Accept only a configured upstream origin, never a caller-provided URL. */
export function parseBffBackendOrigin(value: string | undefined): string | null {
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

function normalizePathname(pathname: string): string | null {
  if (
    !pathname.startsWith("/") ||
    pathname.startsWith("//") ||
    pathname.includes("\\") ||
    /%(?:2f|5c|25)/i.test(pathname) ||
    /[\u0000-\u001f\u007f]/.test(pathname)
  ) {
    return null;
  }
  const rawSegments = pathname.split("/");
  const normalized: string[] = [];
  try {
    for (const segment of rawSegments) {
      const decoded = decodeURIComponent(segment);
      if (
        decoded === "." ||
        decoded === ".." ||
        decoded.includes("/") ||
        decoded.includes("\\") ||
        /[\u0000-\u001f\u007f]/.test(decoded)
      ) {
        return null;
      }
      normalized.push(encodeURIComponent(decoded));
    }
  } catch {
    return null;
  }
  return normalized.join("/");
}

function allowedQuery(pathname: string, search: string): string | null {
  if (!search) return "";
  if (!/^\/v1\/agents\/[^/]+\/versions$/.test(pathname)) return null;

  const params = new URLSearchParams(search);
  const entries = [...params.entries()];
  if (
    entries.some(([key]) => key !== "limit" && key !== "offset") ||
    new Set(entries.map(([key]) => key)).size !== entries.length
  ) {
    return null;
  }
  const limit = params.get("limit");
  const offset = params.get("offset");
  if (
    (limit !== null && (!/^\d+$/.test(limit) || Number(limit) < 1 || Number(limit) > 100)) ||
    (offset !== null && (!/^\d+$/.test(offset) || Number(offset) > 1_000_000))
  ) {
    return null;
  }
  return params.toString() ? `?${params.toString()}` : "";
}

/**
 * Resolve a request to one of the existing, explicitly supported AgentBox API
 * operations. Returns null for every unlisted path/method or unsafe URL input.
 */
export function resolveBffUpstreamTarget(
  pathname: string,
  search: string,
  method: string,
  configuredBackendOrigin: string | undefined,
): string | null {
  const origin = parseBffBackendOrigin(configuredBackendOrigin);
  const normalizedPath = normalizePathname(pathname);
  if (!origin || !normalizedPath) return null;

  const normalizedMethod = method.toUpperCase();
  const rule = API_ROUTE_RULES.find((candidate) => candidate.pattern.test(normalizedPath));
  if (!rule || !(rule.methods as readonly string[]).includes(normalizedMethod)) return null;

  const query = allowedQuery(normalizedPath, search);
  if (query === null) return null;
  return `${origin}${normalizedPath}${query}`;
}

/** Positive allowlist: browser credentials and caller identity never cross upstream. */
export function filterBffForwardHeaders(input: Headers): Headers {
  const output = new Headers();
  for (const name of FORWARDED_REQUEST_HEADERS) {
    const value = input.get(name);
    if (value !== null) output.set(name, value);
  }
  return output;
}

/** Only JSON mutation bodies are supported; safe methods must not carry bodies. */
export function isBffRequestBodyAllowed(
  method: string,
  hasBody: boolean,
  contentType: string | null,
): boolean {
  const normalizedMethod = method.toUpperCase();
  if (SAFE_METHODS.has(normalizedMethod)) return !hasBody;
  if (normalizedMethod !== "POST") return false;
  return hasBody && contentType?.split(";")[0].trim().toLowerCase() === "application/json";
}
