/* Stock_AI_Holding PWA — Service Worker */
const CACHE = "stock-holding-v8";
const PRECACHE = ["/static/manifest.json"];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(PRECACHE)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET") return;
  const u = new URL(e.request.url);

  // /app HTML — 僅走網路，不寫入快取（避免顯示舊版 PWA）
  if (u.pathname === "/app" || u.pathname === "/") {
    e.respondWith(fetch(e.request, { cache: "no-store" }));
    return;
  }

  // 靜態資源 — cache-first（manifest、icons 等）
  if (u.pathname.startsWith("/static/")) {
    e.respondWith(
      caches.match(e.request).then((hit) => hit || fetch(e.request))
    );
  }
});
