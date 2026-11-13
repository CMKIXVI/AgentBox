import { isCsrfRequestAllowed, type CsrfRequestLike } from "./bff-security.ts";
import { isBffRequestBodyAllowed } from "./bff-upstream.ts";

export const MAX_BFF_REQUEST_BYTES = 1_048_576;
export const MAX_BFF_RESPONSE_BYTES = 2_097_152;

export type BffRequestPolicyResult =
  | { allowed: true }
  | { allowed: false; reason: "csrf" | "body" | "content-type" | "content-length" };

export type BffRequestPolicyInput = {
  request: CsrfRequestLike & { headers: Headers };
  hasBody: boolean;
  configuredWebOrigin: string | undefined;
};

/**
 * Validate request trust metadata before callers read or parse the body.
 * A declared length is mandatory for body-bearing BFF operations; the route
 * must still enforce the byte limit while consuming the stream.
 */
export function validateBffRequestEnvelope(
  input: BffRequestPolicyInput,
): BffRequestPolicyResult {
  if (!isCsrfRequestAllowed(input.request, input.configuredWebOrigin)) {
    return { allowed: false, reason: "csrf" };
  }

  const contentType = input.request.headers.get("content-type");
  if (!isBffRequestBodyAllowed(input.request.method, input.hasBody, contentType)) {
    return {
      allowed: false,
      reason: input.hasBody && !contentType?.toLowerCase().startsWith("application/json")
        ? "content-type"
        : "body",
    };
  }

  if (input.hasBody) {
    const rawLength = input.request.headers.get("content-length");
    if (!rawLength || !/^\\d+$/.test(rawLength)) {
      return { allowed: false, reason: "content-length" };
    }
    const length = Number(rawLength);
    if (!Number.isSafeInteger(length) || length < 1 || length > MAX_BFF_REQUEST_BYTES) {
      return { allowed: false, reason: "content-length" };
    }
  }

  return { allowed: true };
}

const ALLOWED_RESPONSE_TYPES = new Set([
  "application/json",
  "application/problem+json",
]);

/** Reject redirects and non-JSON upstream payloads before relaying a response. */
export function isBffUpstreamResponseAllowed(
  status: number,
  contentType: string | null,
  contentLength: string | null,
): boolean {
  if (!Number.isInteger(status) || status < 200 || status > 599) return false;
  if (status >= 300 && status < 400) return false;

  if (contentLength !== null) {
    if (!/^\\d+$/.test(contentLength)) return false;
    const length = Number(contentLength);
    if (!Number.isSafeInteger(length) || length > MAX_BFF_RESPONSE_BYTES) return false;
  }

  if (status === 204) return contentLength === null || contentLength === "0";
  if (!contentType) return false;
  return ALLOWED_RESPONSE_TYPES.has(contentType.split(";")[0].trim().toLowerCase());
}

/** Relay only the response metadata required by the JSON client contract. */
export function filterBffResponseHeaders(input: Headers): Headers {
  const output = new Headers();
  const contentType = input.get("content-type");
  if (contentType) output.set("content-type", contentType);
  output.set("cache-control", "no-store, max-age=0");
  output.set("pragma", "no-cache");
  output.set("x-content-type-options", "nosniff");
  return output;
}

/** Server-generated correlation value; never reuse a caller-supplied identity. */
export function createBffRequestId(): string {
  return crypto.randomUUID();
}

/** Every authenticated upstream request must bypass caches and redirects. */
export function buildBffFetchPolicy(): Pick<RequestInit, "cache" | "redirect" | "credentials"> {
  return {
    cache: "no-store",
    redirect: "manual",
    credentials: "omit",
  };
}

/** Stable, non-sensitive error shape for BFF policy failures. */
export function buildBffPolicyError(
  status: 400 | 403 | 413 | 415,
  code: string,
  requestId: string,
): Response {
  return new Response(
    JSON.stringify({ error: { code, requestId } }),
    {
      status,
      headers: new Headers({
        "content-type": "application/json; charset=utf-8",
        "cache-control": "no-store, max-age=0",
        pragma: "no-cache",
        "x-content-type-options": "nosniff",
      }),
    },
  );
}
