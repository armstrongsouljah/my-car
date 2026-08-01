"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isLoggedIn } from "@/lib/api";

export default function AuthGuard({ children }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!isLoggedIn()) {
      // Reads the URL straight off window rather than usePathname/
      // useSearchParams so this component doesn't need a Suspense boundary
      // (every page that wraps its content in AuthGuard would need one too).
      const next = window.location.pathname + window.location.search;
      router.replace(`/login?next=${encodeURIComponent(next)}`);
    } else {
      setReady(true);
    }
  }, [router]);

  if (!ready) return null;
  return children;
}
