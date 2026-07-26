"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { trackSignal } from "@/lib/telemetry";

export function TelemetryProvider({ children }) {
  const pathname = usePathname();

  useEffect(() => {
    trackSignal("pageview", { path: pathname });
  }, [pathname]);

  return children;
}
