// Single source of truth for the app's public origin — metadataBase
// (layout.jsx), the sitemap's absolute URLs (sitemap.js), and the sitemap
// location robots.txt advertises (robots.js) must all agree, or canonical
// URLs and crawler-facing pointers disagree with each other.
export const APP_URL = process.env.NEXT_PUBLIC_APP_URL || "https://app.glavbox.com";
