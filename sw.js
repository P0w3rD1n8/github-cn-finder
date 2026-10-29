/* Service Worker：stale-while-revalidate + 超时兜底
   首页/清单立即从缓存渲染（秒开 + 离线可开），网络更新在后台进行，下次打开即新内容；
   缓存未命中（首次访问）走网络，5 秒超时兜底，避免网络卡死时白等。
   版本 v9（v1.21）：首页标题改链静态落地页后，升级缓存版本强制旧缓存失效（cache-first 策略下旧 index.html 会一直优先渲染）。 */
const CACHE = "gh-cn-v9";
const ASSETS = ["./", "./index.html", "./data.js", "./manifest.json", "./icon.svg",
  "./icon-192.png", "./icon-512.png", "./icon-maskable.svg", "./icon-maskable-512.png",
  "./list.html"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
  ).then(() => self.clients.claim()));
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

