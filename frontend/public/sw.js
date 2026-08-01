// Minimal app-shell service worker. GlavBox is a live-data app (accounts,
// cars, reminders — all API-backed), not offline-first content, so this
// deliberately doesn't try to cache or replay API responses. It exists to
// satisfy PWA installability and give navigation a network-first fallback
// instead of a browser error page when the connection drops mid-use.
const CACHE_NAME = "glavbox-shell-v1";
const APP_SHELL = ["/", "/icons/icon-192.png", "/icons/icon-512.png"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  // Only handle top-level document navigations, not every sub-resource —
  // Next's app router fetches same-origin RSC/data payloads on client-side
  // transitions, and falling back to the cached "/" shell for one of those
  // (instead of a real page navigation) would hand the client JS runtime a
  // full HTML document where it expects RSC/JSON, breaking the render.
  if (request.method !== "GET" || request.mode !== "navigate") return;

  const url = new URL(request.url);
  // Only handle same-origin requests (the Next.js app shell) — API calls
  // typically go to a different origin and must never be served from cache,
  // and this excludes any future same-origin /api/* proxy route too.
  if (url.origin !== self.location.origin) return;
  if (url.pathname === "/api" || url.pathname.startsWith("/api/")) return;

  event.respondWith(
    fetch(request)
      .then((response) => {
        if (response.ok) {
          // Keep the worker alive until the cache write actually finishes —
          // otherwise the browser can tear it down right after respondWith()
          // resolves, leaving the write incomplete.
          event.waitUntil(
            caches
              .open(CACHE_NAME)
              .then((cache) => cache.put(request, response.clone()))
              .catch(() => {})
          );
        }
        return response;
      })
      .catch(() => caches.match(request).then((cached) => cached || caches.match("/")))
  );
});
