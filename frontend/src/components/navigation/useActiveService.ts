"use client";

import { usePathname } from "next/navigation";
import { useMemo } from "react";

export type Service = "insights" | "research" | null;

export function useActiveService() {
  const pathname = usePathname();

  const service = useMemo((): Service => {
    if (pathname.startsWith("/insights") || pathname.startsWith("/reports")) {
      return "insights";
    }
    if (pathname.startsWith("/research") || pathname.startsWith("/companies")) {
      return "research";
    }
    return null;
  }, [pathname]);

  return {
    isInsightsActive: service === "insights",
    isResearchActive: service === "research",
    currentService: service,
  };
}
