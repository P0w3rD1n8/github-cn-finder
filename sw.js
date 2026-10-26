/* Service Worker：网络优先 + 离线兜底，保证每次打开都是最新版 */
const CACHE = "gh-cn-v4";
const ASSETS = ["./index.html", "./manifest.json", "./icon.svg"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
  ).then(() => self.clients.claim()));
});
self.addEventListener("fetch", e => {
  if (new URL(e.request.url).origin !== location.origin) return;
  // 网络优先：先取线上最新内容，成功则顺手更新缓存；断网时才用缓存兜底
  e.respondWith(
    fetch(e.request).then(res => {
      if (res && res.ok) {
        const copy = res.clone();
        caches.open(CACHE).then(c => c.put(e.request, copy)).catch(()=>{});
      }
      return res;
    }).catch(() => caches.match(e.request))
  );
});
