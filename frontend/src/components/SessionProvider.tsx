"use client";

import { SessionProvider as NextAuthSessionProvider, useSession, signOut } from "next-auth/react";
import { useEffect, useCallback, type ReactNode } from "react";
import { clearAuthToken } from "@/lib/api";

const IDLE_TIMEOUT_MS = 15 * 60 * 1000; // 15 minutes

const ACTIVITY_EVENTS = [
  "click",
  "mousemove",
  "keydown",
  "scroll",
  "touchstart",
  "touchmove",
] as const;

function IdleLogout() {
  const { data: session } = useSession();

  const handleLogout = useCallback(async () => {
    clearAuthToken();
    await signOut({ redirect: true, redirectTo: "/" });
  }, []);

  useEffect(() => {
    if (!session) return;

    let timer = setTimeout(handleLogout, IDLE_TIMEOUT_MS);

    const resetTimer = () => {
      clearTimeout(timer);
      timer = setTimeout(handleLogout, IDLE_TIMEOUT_MS);
    };

    ACTIVITY_EVENTS.forEach((event) => window.addEventListener(event, resetTimer));

    return () => {
      clearTimeout(timer);
      ACTIVITY_EVENTS.forEach((event) => window.removeEventListener(event, resetTimer));
    };
  }, [session, handleLogout]);

  return null;
}

export default function SessionProvider({ children }: { children: ReactNode }) {
  return (
    <NextAuthSessionProvider>
      <IdleLogout />
      {children}
    </NextAuthSessionProvider>
  );
}
