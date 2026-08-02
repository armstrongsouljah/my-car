const APP_URL = process.env.NEXT_PUBLIC_APP_URL || "https://app.glavbox.com";

// Fail-closed: only the public/marketing routes are allowed, everything else
// (the authenticated app) is disallowed explicitly rather than trying to
// remember to list every future authenticated route here — a disallowed
// prefix always wins over the bare "/" allow below, regardless of add order.
export default function robots() {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/dashboard", "/cars", "/expenses", "/reminders", "/settings", "/login", "/mileage"],
    },
    sitemap: `${APP_URL}/sitemap.xml`,
  };
}
