"use client";

import { useEffect, useState, type ReactNode } from "react";
import type { SessionReader } from "../lib/auth-session.ts";
import {
  resolveSessionState,
  sessionRecheckDelayMs,
  type SessionState,
} from "../lib/session-state.ts";

type SessionGateProps = {
  sessionReader: SessionReader;
  children: ReactNode;
  loadingFallback?: ReactNode;
  unauthenticatedFallback: ReactNode;
};

/**
 * UI boundary only: it does not sign users in, redirect, or replace API authorization.
 * Backend authorization remains mandatory for every protected request.
 */
export function SessionGate({
  sessionReader,
  children,
  loadingFallback = <p role="status">Checking session…</p>,
  unauthenticatedFallback,
}: SessionGateProps) {
  const [state, setState] = useState<SessionState | null>(null);

  useEffect(() => {
    let active = true;
    setState(null);
    void sessionReader.readSession().then(
      (session) => {
        if (active) setState(resolveSessionState(session));
      },
      () => {
        if (active) setState({ status: "unauthenticated" });
      },
    );
    return () => {
      active = false;
    };
  }, [sessionReader]);

  useEffect(() => {
    if (state?.status !== "authenticated") return;
    let active = true;
    const delay = sessionRecheckDelayMs(state.session.expiresAt);
    const timer = setTimeout(() => {
      void sessionReader.readSession().then(
        (session) => {
          if (active) setState(resolveSessionState(session));
        },
        () => {
          if (active) setState({ status: "unauthenticated" });
        },
      );
    }, delay);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [sessionReader, state]);

  if (state === null) return loadingFallback;
  if (state.status === "unauthenticated") return unauthenticatedFallback;
  return children;
}
