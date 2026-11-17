const INTERNAL_ORIGIN = "https://agentbox.invalid";
const CONTROL_CHARACTERS = /[\u0000-\u001f\u007f]/;
const ENCODED_PATH_SEPARATOR = /%(?:2f|5c)/i;

/**
 * Accept only a same-origin, root-relative navigation target.
 *
 * This is a client-side navigation safety helper, not an authorization check.
 * A future authentication callback must still validate its own state/nonce and
 * must not treat a return target as evidence of identity or permission.
 */
export function resolveSafeReturnTarget(
  value: unknown,
  fallback: string = "/",
): string {
  const safeFallback = isSafeRelativeTarget(fallback) ? fallback : "/";
  if (typeof value !== "string" || value.length === 0) return safeFallback;
  if (value !== value.trim() || CONTROL_CHARACTERS.test(value)) {
    return safeFallback;
  }
  if (
    !value.startsWith("/") ||
    value.startsWith("//") ||
    value.includes("\\")
  ) {
    return safeFallback;
  }

  const queryIndex = value.indexOf("?");
  const hashIndex = value.indexOf("#");
  const delimiters = [queryIndex, hashIndex].filter((index) => index >= 0);
  const pathEnd = delimiters.length > 0 ? Math.min(...delimiters) : value.length;
  const rawPath = value.slice(0, pathEnd);
  if (ENCODED_PATH_SEPARATOR.test(rawPath)) return safeFallback;

  try {
    for (const segment of rawPath.split("/")) {
      const decoded = decodeURIComponent(segment);
      if (
        decoded === "." ||
        decoded === ".." ||
        decoded.includes("/") ||
        decoded.includes("\\") ||
        decoded.includes("%")
      ) {
        return safeFallback;
      }
    }

    const parsed = new URL(value, INTERNAL_ORIGIN);
    if (
      parsed.origin !== INTERNAL_ORIGIN ||
      parsed.username.length > 0 ||
      parsed.password.length > 0
    ) {
      return safeFallback;
    }
    return `${parsed.pathname}${parsed.search}${parsed.hash}`;
  } catch {
    return safeFallback;
  }
}

function isSafeRelativeTarget(value: string): boolean {
  if (
    value.length === 0 ||
    value !== value.trim() ||
    CONTROL_CHARACTERS.test(value) ||
    !value.startsWith("/") ||
    value.startsWith("//") ||
    value.includes("\\")
  ) {
    return false;
  }
  const queryIndex = value.indexOf("?");
  const hashIndex = value.indexOf("#");
  const delimiters = [queryIndex, hashIndex].filter((index) => index >= 0);
  const pathEnd = delimiters.length > 0 ? Math.min(...delimiters) : value.length;
  const rawPath = value.slice(0, pathEnd);
  if (ENCODED_PATH_SEPARATOR.test(rawPath)) return false;
  try {
    for (const segment of rawPath.split("/")) {
      const decoded = decodeURIComponent(segment);
      if (
        decoded === "." ||
        decoded === ".." ||
        decoded.includes("/") ||
        decoded.includes("\\") ||
        decoded.includes("%")
      ) {
        return false;
      }
    }
    const parsed = new URL(value, INTERNAL_ORIGIN);
    return parsed.origin === INTERNAL_ORIGIN;
  } catch {
    return false;
  }
}
