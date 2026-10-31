# 发现器开发交接手册（DSH 接手版）

> 本手册写给 DeepSeek Harness（DSH）及任何接手者：项目全貌、文件职责、日常操作 SOP、上线流程、已知坑与凭据位置。按手册即可独立继续运营「GitHub 中文发现器」。

## 0. 项目一句话

GitHub 中文发现器：一个纯静态 PWA 网站，用中文名收录并展示 GitHub 上「值得中文用户知道」的开源项目（精选库模式），主打手机端可读性，附 star 实时回写、页码分页、收藏、分享海报、静态项目页、站点地图。内容运营靠人工精选 + 每小时 GitHub Actions 自动刷新 star 数据。

## 1. 线上与仓库

| 项 | 值 |
|---|---|
| 线上站点 | https://p0w3rd1n8.github.io/github-cn-finder/ |
| GitHub 仓库 | P0w3rD1n8/github-cn-finder（远端 main 分支） |
| 本地仓库（ROG） | C:\Users\power\GitHub中文发现器 |
| DSH 工作区 | C:\Users\power\Documents\发现器开发-建议（宣传/视频物料在此） |
| 当前版本 | **v1.24.1**（2026-10-31 上线，SW 缓存 gh-cn-v16，152 个项目） |
| 本地 commit | 已对齐远端 = c5b9928（2026-10-31 对齐；此前孪生提交 65354e8 / af2deb4 分叉已消除） |
| 远端 main | c5b9928（含 6303e18 重建静态页 + c5b9928 star 快照，2026-10-31_05:49） |

## 2. 文件职责一览

| 文件/目录 | 职责 |
|---|---|
| `data.js` | **数据主源（人工维护）**：`REPOS`（精选清单 `{n:"owner/repo"}`）+ `REPO_ZH`（中文名）+ `DETAIL`（中文详情四段式）+ `USAGE`（一句话用法）+ `CATS`（分类表）。**增删项目/改中文简介改这里**，然后跑 fetch-data.py |
| `fetch-data.py` | 数据抓取：读 `data.js` 的 `REPOS` 数组 → 调 GitHub API 抓 star/语言/描述等真实字段 → **写出** `repos.json`。CI 与本地均跑它 |
| `repos.json` | **自动产物，不要手改**：抓取结果（含 star/fork/hist 快照，`updated` 时间戳），前端 fetch 使用；CI 每小时自动刷新并提交 |
| `build_pages.py` | 静态页生成器：由 data.js 生成 `p/<owner>-<repo>.html`（每个项目一个分享落地页）+ `list.html`（全列表）+ `sitemap.xml` |
| `p/` | 152 个静态项目页（v1.24.1 现状） |
| `index.html` | 首页全部前端逻辑：分页、分类、搜索、收藏、海报、主题；版本号在 `window.GH_VER` |
| `sw.js` | Service Worker，缓存名 `gh-cn-v16`；**每次发版必须升级缓存名**，否则用户端不更新 |
| `README.md` | 对外 README：当前版本 + 版本历史（发版时同步） |
| `docs_summary.json` | README 摘要缓存（AI 文档摘要用） |
| `validate-data.js` | 数据校验脚本（CI 用） |
| `verify_sync.py` | **三方一致性核验工具**（本地工作区 ↔ 远端 main ↔ 线上 Pages）：行尾归一化比对、版本三件套、数据表死键/重复键/大小写错配、p 页状态码。用法见 §4 末尾 |
| `.github/workflows/data-update.yml` | 每小时第 15 分钟自动跑 fetch-data.py 并提交 repos.json 数据更新（GitHub Actions，无需本地） |
| `.github/workflows/build-pages.yml` | 生成静态页 + 提交（CI 侧） |
| `.github/workflows/validate.yml` | 数据格式校验 |

## 3. 日常运营 SOP

### 3.1 收录一个新项目
1. 查证：GitHub 仓库真实存在、star 数、是否重复/已收录（搜 data.js 与 p/）。
2. 编辑 `data.js` 的四处（必须配齐，`validate-data.js` 会逐条校验）：
   - `REPOS` 数组加一条**完整对象**：`{n:"owner/repo",d:"一句中文简介（≥5 字）",s:stars,l:"语言",c:"分类"}`。
     **只写 `{n:"..."}` 会被 validate 判失败**——它硬性检查 `r.d`（中文简介）和 `r.c`（分类）；`s`/`l` 是离线兜底值，线上展示的 star 来自 `repos.json`。
     位置：`REPOS` 是**按分类分段**的（`// AI 人工智能`、`// 前端`、`// 后端`…注释行分隔），要插进对应分类段内，**不是按字母序**。
   - `REPO_ZH` 加：`"owner/repo":"中文名"`。
   - `DETAIL` 加四段式详情，**段名必须逐字是**：`🎯应用场景：…` `✨主要功能：…` `💻适用平台：…` `🛠怎么用起来：…`（validate 逐个 `includes` 检查，缺一段即失败）。
   - `USAGE` 加**人群标签数组，不是句子**：`"owner/repo":["程序员","普通用户"]`。合法值只有 `USAGES` 那 9 个：`全部 / 程序员 / 学编程 / 自媒体创作者 / 普通用户 / 游戏玩家 / 设计师 / 视频剪辑 / 自托管/运维`。
   分类从 `CATS` 里选，仅以下 10 个：`全部 / AI 人工智能 / 实用工具 / 开发者工具 / 影音与直播 / 手机 App / 学编程 / 游戏娱乐 / 网页界面 / 后台服务`（不在 CATS 的分类会被 validate-data.js 判失败）。
3. 本地跑 `python fetch-data.py`（读 data.js → 抓真实数据 → 写 repos.json；注意清代理 + openssl，见 §5.1；本机无系统 python，用 DSH 内置，见 §5.4）。
4. 跑 `python build_pages.py`（生成新 p 页 + list.html + sitemap.xml）。
5. 按 §4 发版上线。

### 3.2 下架一个项目
1. `data.js` 删对应四处条目：`REPOS` / `REPO_ZH` / `DETAIL` / `USAGE`。
   顺带清残留（validate 不查，但 `verify_sync.py` 会把它们报成"死键"）：`CN_DESC` 同名键、`GC_MIRRORS`/`GT_MIRRORS` 的小写键、`AUTHORS` 里不再被任何仓库引用的 owner。
2. 重新跑 fetch-data.py + build_pages.py（repos.json、p 页、list、sitemap 自动重建）。
3. 手动删 `p/<owner>-<repo>.html`（build_pages 不负责删旧页，必须手动删）。
4. 按 §4 发版上线，并到线上确认旧 p 页 404。

### 3.3 star 数据刷新
- 自动：GitHub Actions 每小时第 15 分钟自动跑并提交（无需干预）。
- 手动：清代理 + openssl 后本地 `python fetch-data.py` 再提交。

## 4. 发版上线 SOP（v1.x.y）

每次内容或功能变更，按固定五步：

1. **三处版本号同步**（必须同时改）：
   - `index.html`：`window.GH_VER = "v1.x.y";`
   - `sw.js`：`const CACHE = "gh-cn-vXX";`（每次 +1，当前 v16 → v17）
   - `README.md`：当前版本 + 版本历史顶部加一条
2. **重新生成产物**：fetch-data.py → build_pages.py（repos.json / p/ / list.html / sitemap.xml 全重建；data.js 是人工源不动）。
3. **本地验证**：用 `C:\Users\power\Documents\_verify_online_v1241.py`（Playwright + Edge channel=msedge）对本地文件跑一遍：首屏 24 卡、分页条、搜索、各分类、静态页、无报错。**用 DSH 内置 Python 跑，需先装 playwright**（见 §5.4）。改动涉及行为时按清单逐项验。
4. **上线推送**：
   - 常规路径：git commit + push（**清代理 + `-c http.sslBackend=openssl`**，见 §5.1；直连 push 若 `Recv failure: Connection reset`，改走 REST API 脚本，见 §5.2）。
   - 等约 90 秒 CDN 生效，再跑一次线上核验脚本（改 url 为线上地址）。
5. **线上核验**：先跑 HTTP 级 `verify_sync.py`（用法见本节末），再用 Playwright 验浏览器行为（分页点击/搜索空态/无报错）。

### 附：一致性核验工具 verify_sync.py
```powershell
$py = "C:\Users\power\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
$env:PYTHONIOENCODING="utf-8"     # 否则中文/emoji 输出会 GBK 报错
& $py verify_sync.py              # 默认：本地↔远端 main、线上↔本地、版本、数据表、repos.json
& $py verify_sync.py --fetch      # 先 git fetch 刷新 origin/main（网络抖时会挂，慎用）
& $py verify_sync.py --pages      # 另抽样 12 个 p 页查线上状态码
& $py verify_sync.py --full-pages --page-budget 120   # 全量 152 个
```
- 判定口径：**CRLF/LF 差异不算问题**（本机 autocrlf=true、远端 REST 上传保留 CRLF，两边永远会有行尾差异）；只报真内容差异。
- p 页默认不扫：GitHub Pages 链路偶发 20–35s 握手卡顿，全量扫描容易跑成分钟级；`--pages` 有总预算，超时/网络失败的请求单独归类、不计为内容问题。
- 下架页清单**不再手写**：从 `git log --diff-filter=D -- p/` 自动推算"历史存在、现已删除"的页面，逐个要求 404。

## 5. 已知坑与对策（血泪经验，必须遵守）

### 5.1 git 全局代理 + SSL 后端（两个都必须处理）
- git 全局代理指向 `http://127.0.0.1:7897`（Clash），**fetch/push 前必须清代理直连**：
  ```powershell
  $env:HTTP_PROXY=""; $env:HTTPS_PROXY=""; $env:http_proxy=""; $env:https_proxy=""
  git -c http.proxy= -c https.proxy= fetch --all
  ```
- **本机 git 走 HTTPS 必须加 `-c http.sslBackend=openssl`**：全局 sslBackend 是 schannel，默认会报 `SEC_E_NO_CREDENTIALS`；换 OpenSSL 后一次通过：
  ```powershell
  git -c http.sslBackend=openssl -c http.proxy= -c https.proxy= fetch origin
  git -c http.sslBackend=openssl -c http.proxy= -c https.proxy= push origin main
  ```
- git 在 `C:\Program Files\Git\cmd\git.exe`（不在 PATH，需全路径调用或用 `git` 若已配）。

### 5.2 直连 push 失败 → REST API 上传
- 本机直连 `git push` 多次实测 `Recv failure: Connection reset`（网络环境问题，不是 git 配置问题）。
- 已写好备用脚本：`C:\Users\power\Documents\upload_via_api.py`（REST API 逐文件上传，含删除）。
- **脚本两个坑**（已解决，勿改回）：
  1. ref 对象没有 tree 字段，须先 `GET /repos/…/git/ref/heads/main` 拿 commit sha，再 `GET /repos/…/git/commits/{sha}` 拿 `tree.sha`。
  2. 删除文件时 mode 写 `000000` 会 422；正确写法：`"path": "...", "mode": "100644", "sha": null`。
- GH_TOKEN 来源：`C:\Users\power\.git-credentials`（格式 `https://P0w3rD1n8:gho_xxxxx`，把冒号后当 token 用）。**凭据不要提交进仓库**。

### 5.3 其他坑
- star 数据必须走真实 API 回写，前端不造假数据。
- UTC 时间口径：榜单/「今日」按 UTC 日切；黑名单在 fetch-data.py 里维护。
- 手机端首屏可读性是验收底线（用户明确要求）。
- 「全部」按钮点击委托用 `#catBar [data-cat="全部"]` 选择器（避开 strict 冲突）。
- 分类切换/搜索/排序都必须把 homePage 重置为 1。

### 5.4 Python 环境（本机无系统 python）
- 本机 `python` 只是 Microsoft Store 别名，真解释器不存在；豆包侧解析到的是豆包沙箱运行时。
- **统一用 DSH 内置 Python 3.12.14**：
  ```
  C:\Users\power\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe
  ```
  例：`& "C:\Users\power\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe" fetch-data.py`
- 控制台是 GBK，脚本里的 emoji/中文 print 会抛 `UnicodeEncodeError`（如 build_pages.py 结尾那行 ✅），**不影响已写入的文件**；想干净输出就加 `$env:PYTHONIOENCODING="utf-8"`。
- HTTP 级核验可用（urllib）；**浏览器级核验（Playwright）需要先装 playwright**（Edge 与 node v24 都在）：`<DSH python> -m pip install playwright` 后按需 `playwright install chromium` 或用 Edge channel=msedge。

## 6. 当前状态与待办

### 已上线（v1.24.1）
- 页码分页：每页 24 个，页码条「上一页/页码窗口/下一页/第 x/N 页 · 共 N 个」。
- 152 个项目；AI 分类 23 个恰 1 页；分页 7 页、末页 8 卡。
- 已下架并确认线上 404：5 个大肥鱼插件（T-Auto/dsh-ops、QCYTSN/dsh-dafeiyu、liyupi/dafeiyu-cleaner、xiaoshihou514/dsh-desktop-pet、RYANFFY/deepseek-dafeiyu-pet）+ 早期下架的 legado（阅读）。
- 2026-10-31 DSH 接手时已核验：线上=本地（data.js 规范化逐字节相同、sitemap 154、list.html 仅 CRLF 差异、下架页 404、在册页 200、CI 全绿）；本地已 `git reset --hard origin/main` 对齐到 c5b9928，无分叉。
- 说明：`repos.json` 每小时被 CI 刷新，本地与远端差一个快照属正常，不是漂移。

### 待办/未决（等用户拍板，勿擅自做）
1. **dsh-our-free-model 是否收录**：Ebony-Vinyl/dsh-our-free-model（★★53.1k，GitHub Trending 日榜第 1）——用户已试装此插件，是否收录进「AI 人工智能」分类未表态。
2. **插件单独子项 + star 门槛方案**：用户曾提出「插件与应用不同类应单设子项」「低人气（如 star<100）应剔除」，方案暂缓，未重启。
3. 宣传/引流侧物料在 `C:\Users\power\Documents\发现器开发-建议\`（视频、封面、脚本），如需再产出可参考其中的 make_video.py / 决策参考。

## 7. DSH 侧操作要点（本机）

- 本机 DSH：`C:\Users\power\AppData\Local\Programs\DeepSeek Harness\DeepSeek Harness.exe`，版本 0.2.1-rc.5。
- 数据根：`C:\Users\power\.dsh\`；profile：`profiles\{desktop,web}`。
- 插件管理命令（官方，参考 dsh-plugin-hub README）：
  ```
  dsh plugin --profile web add <包名>
  dsh plugin --profile web remove <包名>
  dsh plugin --profile web update [包名]
  ```
  安装/卸载/更新后**必须重启 dsh web** 才生效。
- **插件 duplicate 报错**（`duplicate factory registration`）＝ 同名 entry 装了两份（例如同时装了聚合包和独立包）。DSH 可正常启动后不损坏，卸载多余那份重启即可。**建议：只装一个来源，别混装。**
- 接手项目：在 DSH 里打开 `C:\Users\power\GitHub中文发现器` 作为工作区，配合本手册即可独立迭代。DSH 是本地 AI 助手，不连接豆包云端技能，纯本地文件操作。

## 8. 验证清单（发版后线上必查）

- [ ] sw.js 缓存名已升级（gh-cn-vXX）
- [ ] index.html GH_VER 正确
- [ ] 首页首屏 24 卡 + 页码条「第 1/7 页 · 共 152 个」
- [ ] 末页（第 7 页）8 卡
- [ ] 搜索关键词 0 结果空态正常
- [ ] 已下架项目的 p 页 404
- [ ] sitemap.xml 152 项目 + 首页 + list.html = 154 url
- [ ] 手机视口（375px）首屏可读、不闪白
