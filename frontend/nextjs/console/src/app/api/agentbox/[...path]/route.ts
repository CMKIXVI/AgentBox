import { getToken } from "next-auth/jwt";
import { NextRequest, NextResponse } from "next/server";

type RouteContext = { params: Promise<{ path: string[] }> };

async function proxy(request: NextRequest, context: RouteContext) {
  const baseUrl = process.env.AGENTBOX_API_BASE_URL;
  const secret = process.env.AUTH_SECRET;
  if (!baseUrl || !secret) {
    return NextResponse.json(
      { detail: "AgentBox API proxy is not configured" },
      { status: 503 },
    );
  }

  if (!["GET", "HEAD"].includes(request.method)) {
    const origin = request.headers.get("origin");
    if (origin !== request.nextUrl.origin) {
      return NextResponse.json({ detail: "Invalid request origin" }, { status: 403 });
    }
  }

  const token = await getToken({ req: request, secret });
  const accessToken = token?.agentboxAccessToken;
  if (typeof accessToken !== "string" || accessToken.length === 0) {
    return NextResponse.json({ detail: "Authentication required" }, { status: 401 });
  }

  const { path } = await context.params;
  if (!path?.length || path.some((segment) => segment === "." || segment === "..")) {
    return NextResponse.json({ detail: "Invalid API path" }, { status: 400 });
  }

  let upstreamUrl: URL;
  try {
    const normalizedBase = new URL(baseUrl);
    if (
      normalizedBase.protocol !== "https:" &&
      normalizedBase.hostname !== "localhost" &&
      normalizedBase.hostname !== "127.0.0.1"
    ) {
      return NextResponse.json({ detail: "AgentBox API must use HTTPS" }, { status: 500 });
    }
    upstreamUrl = new URL(
      path.map((segment) => encodeURIComponent(segment)).join("/"),
      normalizedBase.toString().replace(/\/?$/, "/"),
    );
    upstreamUrl.search = request.nextUrl.search;
  } catch {
    return NextResponse.json({ detail: "Invalid AgentBox API configuration" }, { status: 500 });
  }

  const headers = new Headers({ Accept: "application/json" });
  headers.set("Authorization", `Bearer ${accessToken}`);
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("Content-Type", contentType);

  const body = ["GET", "HEAD"].includes(request.method)
    ? undefined
    : await request.arrayBuffer();

  try {
    const upstream = await fetch(upstreamUrl, {
      method: request.method,
      headers,
      body,
      cache: "no-store",
      redirect: "manual",
    });
    const responseHeaders = new Headers();
    const upstreamContentType = upstream.headers.get("content-type");
    if (upstreamContentType) responseHeaders.set("Content-Type", upstreamContentType);
    responseHeaders.set("Cache-Control", "no-store");
    return new Response(upstream.body, {
      status: upstream.status,
      headers: responseHeaders,
    });
  } catch {
    return NextResponse.json({ detail: "AgentBox API is unavailable" }, { status: 502 });
  }
}

export const GET = proxy;
export const HEAD = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
