/* Service Worker：stale-while-revalidate + 超时兜底
   首页/清单立即从缓存渲染（秒开 + 离线可开），网络更新在后台进行，下次打开即新内容；
   缓存未命中（首次访问）走网络，5 秒超时兜底，避免网络卡死时白等。
   版本 v10（v1.21.2）：install 改为逐个容错缓存（addAll 任一资源失败会让整个 SW 不激活，
   data.js/index.html 因此长期不在缓存 → 返回首页时 data.js 加载失败 → 白屏），并先继承旧缓存已有资源。
   版本 v11（v1.22.2）：activate 后通知所有已打开页面（postMessage APP_UPDATED），
   页面收到后弹出「网站已更新，点刷新」提示——解决用户不知道要刷新、一直看旧缓存的问题。 */
const CACHE = "gh-cn-v11";
const ASSETS = ["./", "./index.html", "./data.js", "./manifest.json", "./icon.svg",
  "./icon-192.png", "./icon-512.png", "./icon-maskable.svg", "./icon-maskable-512.png",
  "./list.html"];

self.addEventListener("install", e => {
  e.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    // 先继承旧缓存里已有的同一资源（避免升级后短暂丢资源），没有的再走网络
    const oldCaches = await caches.keys();
    await Promise.allSettled(ASSETS.map(async asset => {
      let got = false;
      for (const old of oldCaches){
        if (old === CACHE) continue;
        try{
          const hit = await caches.match(new Request(asset), {cacheName: old});
          if (hit){ await cache.put(asset, hit); got = true; break; }
        }catch(err){}
      }
      if (got) return;
      try{
        const res = await fetchWithTimeout(asset, 8000);
        if (res && res.ok) await cache.put(asset, res);
      }catch(err){ /* 单个资源失败不阻断整个 SW 激活 */ }
    }));
    self.skipWaiting();
  })());
});
self.addEventListener("activate", e => {
  e.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)));
    await self.clients.claim();
    // v11：通知所有已打开页面「已更新」，页面显示刷新提示
    const cs = await self.clients.matchAll({includeUncontrolled: true});
    cs.forEach(c => c.postMessage({type: "APP_UPDATED"}));
  })());
});
self.addEventListener("fetch", e => {
  const u = new URL(e.request.url);
  if (u.origin !== location.origin) return;      // 跨源资源不拦截，走正常网络
  if (e.request.method !== "GET") return;        // 只处理 GET
  if (u.pathname.endsWith("/repos.json")) {      // 实时数据：network-first（3 秒超时回退缓存），保证 star 是最新的
    e.respondWith(networkFirst(e.request));
    return;
  }
  e.respondWith(fromCacheOrNetwork(e.request));
});

async function networkFirst(req){
  try{
    const res = await fetchWithTimeout(req, 3000);
    if (res && res.ok){
      const copy = res.clone();
      caches.open(CACHE).then(c => c.put(req, copy)).catch(()=>{});
      return res;
    }
  }catch(err){}
  const cached = await caches.match(req);
  if (cached) return cached;
  return new Response("离线状态：实时数据暂不可用，请联网后刷新重试", {
    status: 503, headers: {"Content-Type": "text/plain;charset=utf-8"}
  });
}

async function fromCacheOrNetwork(req){
  const cached = await caches.match(req);
  if (cached){
    // 缓存命中：先回缓存（秒开/离线可用），后台静默更新
    updateCache(req).catch(()=>{});
    return cached;
  }
  // 缓存未命中（首次访问或新资源）：走网络，5 秒超时兜底
  try{
    const res = await fetchWithTimeout(req, 5000);
    if (res && res.ok){
      const copy = res.clone();
      caches.open(CACHE).then(c => c.put(req, copy)).catch(()=>{});
    }
    return res;
  }catch(err){
    return new Response("离线状态：缓存中暂无该资源，请联网后刷新重试", {
      status: 503, headers: {"Content-Type": "text/plain;charset=utf-8"}
    });
  }
}

async function updateCache(req){
  const res = await fetchWithTimeout(req, 8000);
  if (res && res.ok){
    const copy = res.clone();
    const c = await caches.open(CACHE);
    await c.put(req, copy);
  }
}

function fetchWithTimeout(req, ms){
  return new Promise((resolve, reject)=>{
    const timer = setTimeout(()=>reject(new Error("fetch timeout")), ms);
    fetch(req).then(r=>{ clearTimeout(timer); resolve(r); },
                    err=>{ clearTimeout(timer); reject(err); });
  });
}

