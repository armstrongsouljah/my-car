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
  if (request.method !== "GET") return;
  // Only handle same-origin requests (the Next.js app shell) — API calls
  // typically go to a different origin and must never be served from cache.
  if (new URL(request.url).origin !== self.location.origin) return;

  event.respondWith(
    fetch(request)
      .then((response) => {
        const copy = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
        return response;
      })
      .catch(() => caches.match(request).then((cached) => cached || caches.match("/")))
  );
});
