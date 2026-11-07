/* Service Worker：stale-while-revalidate + 超时兜底
   首页/清单立即从缓存渲染（秒开 + 离线可开），网络更新在后台进行，下次打开即新内容；
   缓存未命中（首次访问）走网络，5 秒超时兜底，避免网络卡死时白等。
   版本 v10（v1.21.2）：install 改为逐个容错缓存（addAll 任一资源失败会让整个 SW 不激活，
   data.js/index.html 因此长期不在缓存 → 返回首页时 data.js 加载失败 → 白屏），并先继承旧缓存已有资源。
   版本 v11（v1.22.2）：activate 后通知所有已打开页面（postMessage APP_UPDATED），
   页面收到后弹出「网站已更新，点刷新」提示——解决用户不知道要刷新、一直看旧缓存的问题。
   版本 v12（v1.23.0）：缓存清单新增 qrcode.min.js（海报功能本地二维码库）。
   版本 v13（v1.23.1）：海报 v2 布局（信息加密+动态撑满）+ toast 移底部（class 控制显示，修复关不掉/压分类栏）。
   版本 v14（v1.23.2）：海报简介改白字居中。
   版本 v15（v1.24.0）：首页「加载更多」升级为页码分页（每页 24 + 页码条）；收录 5 个「大肥鱼」DeepSeek Harness 插件项目。
   版本 v16（v1.24.1）：下架 5 个大肥鱼插件项目（插件非应用类型、除 dsh-ops 外人气过低，回归 152 个精选）。
   版本 v17（v1.24.2）：新增 10 个项目（162 个）；修正 10 个仓库改名（llama.cpp/React/OpenHands/Qwen3 等）。
   版本 v18（v1.25.0）：筛选状态写入 URL（可分享/刷新不丢）；卡片新增活跃度角标（半年未更/停更/已归档）；
   详情页新增「相似项目」推荐；数据管线新增每周 star 快照 weekly.json（供周涨星与周刊）。
   版本 v19（v1.26.0）：新增「专题合辑」5 个（装机/自媒体/本地 AI/自建服务/学编程）、「每周精选」周刊页与 RSS 订阅。
   版本 v20（v1.27.0）：新增「对比模式」（勾选 2–3 个项目并排比较）与每个项目的专属分享封面图（og/*.png）。
   版本 v21（v1.27.1）：导航与 data.js 改为 network-first（no-store），sw.js 用 updateViaCache:none 注册，
   新版本一次刷新即可生效；未操作页面时收到更新会静默刷新。 */
const CACHE = "gh-cn-v21";
const ASSETS = ["./", "./index.html", "./data.js", "./qrcode.min.js", "./manifest.json", "./icon.svg",
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
  // v21（v1.27.1）：页面导航、data.js 改走 network-first。
  // 背景：安卓 Edge 上 stale-while-revalidate 会先给旧页面，用户要连刷好几次才看到新版。
  // 改成「先要网络（绕过 HTTP 缓存），超时或离线才回缓存」，一次刷新就能拿到新版。
  const isNav = e.request.mode === "navigate";
  if (isNav || u.pathname.endsWith("/index.html") || u.pathname.endsWith("/data.js")) {
    e.respondWith(networkFirst(e.request, isNav ? 3000 : 2500, "reload"));
    return;
  }
  if (u.pathname.endsWith("/repos.json")) {      // 实时数据：network-first（3 秒超时回退缓存），保证 star 是最新的
    e.respondWith(networkFirst(e.request, 3000, "reload"));
    return;
  }
  e.respondWith(fromCacheOrNetwork(e.request));
});

async function networkFirst(req, timeout, cacheMode){
  try{
    const res = await fetchWithTimeout(req, timeout || 3000, cacheMode);
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

function fetchWithTimeout(req, ms, cacheMode){
  const opts = cacheMode ? {cache: cacheMode} : undefined;
  return new Promise((resolve, reject)=>{
    const timer = setTimeout(()=>reject(new Error("fetch timeout")), ms);
    fetch(req, opts).then(r=>{ clearTimeout(timer); resolve(r); },
                    err=>{ clearTimeout(timer); reject(err); });
  });
}

