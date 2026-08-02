import { APP_URL } from "@/lib/site";

// True deny-by-default: only the three public paths are allowed, everything
// else — including any authenticated route added later — is disallowed
// without needing this file touched. "/$" (the Robots Exclusion Protocol's
// end-of-string anchor) matches only the exact root, not every path as a
// prefix, so it can't accidentally allow-list everything alongside it.
// `robots: { index: false, follow: false }` on the root layout (see
// app/layout.jsx) is the same fail-closed default enforced again in the
// per-page <meta name="robots"> tag.
export default function robots() {
  return {
    rules: {
      userAgent: "*",
      allow: ["/$", "/contact", "/privacy"],
      disallow: "/",
    },
    sitemap: `${APP_URL}/sitemap.xml`,
  };
}
