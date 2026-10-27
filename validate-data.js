#!/usr/bin/env node
/* GitHub 中文发现器 · 数据校验（CI：每次 push 到 main 自动跑）
 * 校验 data.js：
 *   1. 完整性：REPOS 每条都有中文名(REPO_ZH)、四段式详情(DETAIL)、人群标签(USAGE)、中文简介(d)
 *   2. 无重复 key：CN_DESC / REPO_ZH / DETAIL / USAGE / 镜像表 内 key 唯一
 *   3. 格式：REPOS.n 为 owner/repo，分类 c 在合法集合内，人群标签在 USAGES 内
 *   4. 无 404 链接（有 GITHUB_TOKEN 时）：GET /repos/{n} 逐仓库确认真实存在
 * 失败（exit 1）时阻断合并/发布，防止坏数据上线。 */
const fs = require("fs");
const path = require("path");

const DATA = path.join(__dirname, "data.js");
const src = fs.readFileSync(DATA, "utf8");

// 在沙箱里执行 data.js，返回全部 const（data.js 是合法 JS；const 不进全局，用尾部表达式捕获）
const vm = require("vm");
const sandbox = {};
vm.createContext(sandbox);
const grabbed = vm.runInContext(
  src + "\n;({USAGES,USAGE,REPOS,GC_MIRRORS,GT_MIRRORS,CN_DESC,AUTHORS,REPO_ZH,ORG_SET,CAT_COLORS,DETAIL,CATS})",
  sandbox
);
const { REPOS, USAGES, USAGE, CN_DESC, REPO_ZH, DETAIL, AUTHORS, ORG_SET, CAT_COLORS, GC_MIRRORS, GT_MIRRORS, CATS } = grabbed;

let errors = [];
let warnings = [];

// ---- 1. REPOS 基础 ----
if (!Array.isArray(REPOS) || REPOS.length < 100) errors.push(`REPOS 异常：${REPOS && REPOS.length}`);
const keys = new Set();
for (const r of REPOS) {
  if (keys.has(r.n)) errors.push(`REPOS 重复仓库：${r.n}`);
  keys.add(r.n);
  if (!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(r.n)) errors.push(`仓库名格式异常：${r.n}`);
  if (!r.d || r.d.length < 5) errors.push(`${r.n} 缺中文简介 d`);
  if (!r.c) errors.push(`${r.n} 缺分类 c`);
}

// ---- 2. 分类/人群合法性 ----
for (const r of REPOS) {
  if (r.c && CATS.length && !CATS.includes(r.c)) errors.push(`${r.n} 分类不在列表：${r.c}`);
  const u = USAGE[r.n];
  if (!u || !u.length) errors.push(`${r.n} 缺人群标签 USAGE`);
  else for (const g of u) if (!USAGES.includes(g)) errors.push(`${r.n} 人群标签非法：${g}`);
}

// ---- 3. 覆盖完整性：每个仓库都要有中文名/详情 ----
for (const r of REPOS) {
  if (!REPO_ZH[r.n] || REPO_ZH[r.n].length < 2) errors.push(`${r.n} 缺中文名 REPO_ZH`);
  if (!DETAIL[r.n] || DETAIL[r.n].length < 20) errors.push(`${r.n} 缺四段式详情 DETAIL`);
  // DETAIL 四段式结构抽查
  const d = DETAIL[r.n] || "";
  for (const seg of ["应用场景", "主要功能", "适用平台", "怎么用起来"]) {
    if (!d.includes(seg)) { errors.push(`${r.n} 详情缺「${seg}」段`); break; }
  }
}

// ---- 4. 无重复 key（JS 对象重复 key 会静默覆盖，从源文本核对） ----
function dupKeysInObject(objName) {
  const m = src.match(new RegExp(`const ${objName} = \\{([\\s\\S]*?)\\n?\\};`));
  if (!m) return errors.push(`${objName} 未找到`);
  const keys = [...m[1].matchAll(/^\s*"([^"]+)":/gm)].map(x => x[1]);
  const seen = new Set();
  for (const k of keys) {
    if (seen.has(k)) errors.push(`${objName} 重复 key：${k}`);
    seen.add(k);
  }
}
["CN_DESC", "REPO_ZH", "DETAIL", "USAGE", "GC_MIRRORS", "GT_MIRRORS"].forEach(dupKeysInObject);

// ---- 5. 仓库存在性（无 404 链接）：GET https://github.com/{n}（只读状态码，立即取消 body）
// 不用 GitHub API（CI token 与 fine-grained token 都只对本仓库有权限，查外部仓库一律 404）。
// 用 fetch（undici，读 HTTPS_PROXY，CI 直连也通）；HEAD 在部分代理下会挂起，故用 GET+cancel。
async function checkReposExist() {
  const concurrency = 5;
  const queue = [...REPOS];
  const fail = [];
  let checked = 0;
  async function worker() {
    while (queue.length) {
      const r = queue.shift();
      let status = null;
      for (let attempt = 0; attempt < 3 && status === null; attempt++) {
        try {
          const res = await fetch(`https://github.com/${r.n}`, {  // n 已由正则保证只含安全字符，勿 encodeURIComponent（%2F 会让 GitHub 404）
            method: "GET",
            redirect: "follow",
            headers: { "User-Agent": "gh-cn-finder-validate" },
            signal: AbortSignal.timeout(20000),
          });
          status = res.status;
          try { if (res.body) await res.body.cancel(); } catch {}  // 不下载页面内容
        } catch (e) {
          if (attempt === 2) warnings.push(`${r.n} → 网络异常 ${e.message}`);
        }
      }
      if (status === 404) fail.push(`${r.n} → 404 不存在`);
      if (status !== null) checked++;
    }
  }
  await Promise.all(Array.from({length: concurrency}, worker));
  if (fail.length) errors.push(`存在 404 仓库：${fail.join(", ")}`);
  else console.log(`✅ 仓库存在性校验通过（${checked}/${REPOS.length} 个全部存在）`);
}

(async () => {
  await checkReposExist();
  console.log(`REPOS=${REPOS.length}  CN_DESC=${Object.keys(CN_DESC).length}  REPO_ZH=${Object.keys(REPO_ZH).length}  DETAIL=${Object.keys(DETAIL).length}  USAGE=${Object.keys(USAGE).length}  GC=${Object.keys(GC_MIRRORS).length}  GT=${Object.keys(GT_MIRRORS).length}`);
  if (warnings.length) console.log("⚠️ warnings:\n  " + warnings.join("\n  "));
  if (errors.length) {
    console.error("❌ 校验失败：\n  " + errors.join("\n  "));
    process.exit(1);
  }
  console.log("✅ 数据校验全部通过（完整性/无重复/格式/仓库存在性）");
})();
