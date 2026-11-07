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
| 当前版本 | **v1.27.0**（2026-11-07 上线，SW 缓存 gh-cn-v20，162 个项目） |
| 本地 commit | 与远端同步 = `0fd5202`（2026-11-07 v1.26.0 合辑 + 周刊 + RSS） |
| 远端 main | `0fd5202`（v1.26.0 / SW v19；线上 22 项浏览器断言全绿、7 文件逐字节一致） |

## 2. 文件职责一览

| 文件/目录 | 职责 |
|---|---|
| `data.js` | **数据主源（人工维护）**：`REPOS`（精选清单 `{n:"owner/repo"}`）+ `REPO_ZH`（中文名）+ `DETAIL`（中文详情四段式）+ `USAGE`（一句话用法）+ `CATS`（分类表）。**增删项目/改中文简介改这里**，然后跑 fetch-data.py |
| `fetch-data.py` | 数据抓取：读 `data.js` 的 `REPOS` 数组 → 调 GitHub API 抓 star/语言/描述等真实字段 → **写出** `repos.json`。CI 与本地均跑它 |
| `repos.json` | **自动产物，不要手改**：抓取结果（含 star/fork/hist 快照、`pa` 最近提交日、`ar` 是否归档），前端 fetch 使用；CI 每小时自动刷新并提交 |
| `weekly.json` | **自动产物**：每周一张全库 star 快照（`{date, stars}`，保留 60 期），由 fetch-data.py 维护，供「周涨星」和周刊页使用 |
| `build_pages.py` | 静态页生成器：由 data.js 生成 `p/<owner>-<repo>.html`（每个项目一个分享落地页）+ `list.html`（全列表）+ `sitemap.xml` |
| `build_extra.py` | **v1.26.0 新增**：生成 `c/`（专题合辑）、`weekly/`（每周精选）、`feed.xml`（RSS），并重写 sitemap 把附加页纳入 |
| `collections.json` | **人工策展数据**：专题合辑的标题/简介/项目清单，改这里增删合辑 |
| `c/` `weekly/` `feed.xml` | 自动产物（合辑页 / 周刊页 / RSS），不要手改 |
| `build_og.py` | **v1.27.0 新增**：用 Pillow 生成每个项目的 1200×630 分享封面（`og/<owner>-<repo>.png`），CI 里先装 pillow + fonts-noto-cjk 再跑 |
| `og/` | 自动产物：162 张分享封面（约 8MB）；**不加 star 数**，否则每小时都要重生成 |
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
2. **重新生成产物**：fetch-data.py → build_og.py → build_pages.py → build_extra.py（repos.json / og/ / p/ / list.html / sitemap.xml / c/ / weekly/ / feed.xml 全重建；data.js 是人工源不动）。
3. **本地验证**：跑 `verify_browser.py --local`（Playwright + Edge，13 项浏览器级断言：首屏 24 卡、分页条、第 7 页 8 卡、AI 分类 23 个、搜索空态、搜索命中、静态页、无报错、375px 手机端）。**注意**：Playwright 需要命名管道和 TEMP 写权限，DSH 默认沙箱会报 `WinError 5`，必须用完整权限运行（见 §5.4）。
4. **上线推送**：
   - 常规路径：git commit + push（**清代理 + `-c http.sslBackend=openssl` + `credential.helper=` + token 走 URL**，见 §5.1）。
   - 等约 90 秒 CDN 生效，再跑一次线上核验脚本（改 url 为线上地址）。
5. **线上核验**：先跑 HTTP 级 `verify_sync.py`（用法见本节末），再用 `verify_browser.py`（不带 `--local`）验线上浏览器行为。

### 附：两个核验工具

**verify_sync.py — HTTP 级三方一致性**
```powershell
$py = "C:\Users\power\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
$env:PYTHONIOENCODING="utf-8"     # 否则中文/emoji 输出会 GBK 报错
& $py verify_sync.py              # 默认：本地↔远端 main、线上↔本地、版本、数据表、repos.json
& $py verify_sync.py --fetch      # 先 git fetch 刷新 origin/main（网络抖时会挂，慎用）
& $py verify_sync.py --pages      # 另抽样 12 个 p 页查线上状态码
& $py verify_sync.py --full-pages --page-budget 120   # 全量 p 页
& $py verify_sync.py --links      # 巡检全部仓库链接：404 / 改名（走 GitHub API，需 token）
```
- 判定口径：**CRLF/LF 差异不算问题**（已加 `.gitattributes` 统一 LF，但仍保留归一化兜底）；只报真内容差异。
- p 页默认不扫：GitHub Pages 链路偶发 20–35s 握手卡顿，全量扫描容易跑成分钟级；`--pages` 有总预算，超时/网络失败的请求单独归类、不计为内容问题。
- 下架页清单**不再手写**：从 `git log --diff-filter=D -- p/` 自动推算"历史存在、现已删除"的页面，逐个要求 404。
- `--links` 的探测方式：有 `GH_TOKEN`/`GITHUB_TOKEN` 或 `~/.git-credentials` 时走 API（162 个约 10 秒，直接拿到新 `full_name`）；无 token 退回 HEAD 探测（慢且易受网络影响）。**404 记为问题，改名只记为提示**（改完 REPOS 与四张表才算修完）。

**verify_browser.py — 浏览器级行为验收（18 项）**
```powershell
$env:PYTHONPATH = "$PWD\.pylibs"     # playwright 装在工作区 .pylibs（见 §5.4）
& $py verify_browser.py --local      # 本地起 http.server 测当前工作区
& $py verify_browser.py              # 测线上
& $py verify_browser.py --headed     # 显示窗口调试
```
- 覆盖：首屏卡数 / 分页条 / 末页卡数 / AI 分类 / 搜索空态 / 搜索命中 / 静态页 / 控制台无报错 / 请求无失败 / 375px 手机端 / **v1.25.0 新增：筛选写 URL、刷新保持筛选、活跃度判定、停更角标、相似项目**。
- 截图落在 `_shots/`（已 gitignore）。
- 已知口径：搜索会同时查 GitHub API，**无意义关键词才会 0 结果**；前端会主动取消上一轮搜索请求，`ERR_ABORTED` 不计为失败。

## 5. 已知坑与对策（血泪经验，必须遵守）

### 5.1 git 代理 / SSL 后端 / 凭据（三个都必须处理，缺一个就推不上去）
- git 全局代理指向 `http://127.0.0.1:7897`（Clash），**fetch/push 前必须清代理直连**：
  ```powershell
  $env:HTTP_PROXY=""; $env:HTTPS_PROXY=""; $env:http_proxy=""; $env:https_proxy=""
  ```
- **必须 `-c http.sslBackend=openssl`**：全局是 schannel，对 GitHub 报 `SEC_E_NO_CREDENTIALS`。
- **必须 `-c credential.helper=`**：系统级 `credential.helper=manager` 是 sh 脚本，DSH 沙箱禁止创建命名管道，会报
  `couldn't create signal pipe, Win32 error 5` → `failed to execute prompt script`；而内置 `credential-store` 在沙箱里也取不到凭据。所以凭据走 URL。
- **可用的 push 命令（2026-10-31 实测 2 秒成功，`c5b9928..1ea01e2`）**：
  ```powershell
  $env:HTTP_PROXY=""; $env:HTTPS_PROXY=""; $env:http_proxy=""; $env:https_proxy=""
  $tok = ([regex]::Match((Get-Content "C:\Users\power\.git-credentials" | Where-Object { $_ -match 'github' }),'https://([^:]+):([^@]+)@')).Groups[2].Value
  git -c credential.helper= -c http.sslBackend=openssl push "https://P0w3rD1n8:$tok@github.com/P0w3rD1n8/github-cn-finder.git" main
  ```
  fetch 同理（可省 token，公开仓库）：
  ```powershell
  git -c credential.helper= -c http.sslBackend=openssl fetch origin main
  ```
- **注意**：`git fetch` 在 `--fetch` 场景偶发挂死（git-remote-https 子进程不被超时杀掉），需要时单独跑、别塞进自动化脚本。
- git 在 `C:\Program Files\Git\cmd\git.exe`（不在 PATH，需全路径调用或用 `git` 若已配）。

### 5.2 push 仍失败时的备用通道：REST API 上传
> 2026-10-31 起 **git push 已实测可用**（见 §5.1），本节降级为兜底方案。
- 历史上多次 `Recv failure: Connection reset`，当时误判为"网络问题"；实际主因是 §5.1 的 schannel + credential helper 两个坑。
- 备用脚本：`C:\Users\power\Documents\upload_via_api.py`（REST API 逐文件上传，含删除）。
- **脚本两个坑**（已解决，勿改回）：
  1. ref 对象没有 tree 字段，须先 `GET /repos/…/git/ref/heads/main` 拿 commit sha，再 `GET /repos/…/git/commits/{sha}` 拿 `tree.sha`。
  2. 删除文件时 mode 写 `000000` 会 422；正确写法：`"path": "...", "mode": "100644", "sha": null`。
- GH_TOKEN 来源：`C:\Users\power\.git-credentials`（格式 `https://P0w3rD1n8:gho_xxxxx`，把冒号后当 token 用）。**凭据不要提交进仓库**。

### 5.3 其他坑
- **push 前先 `fetch` + `rebase`**：CI 每小时会提交 `repos.json`，本地久了直接 push 会被 `! [rejected] (fetch first)` 拒掉。正确姿势：`git fetch origin main` → `git rebase origin/main` → push（只改 repos.json 的提交不会冲突）。**push 失败后不要手动 `git update-ref refs/remotes/origin/main`**——那会把跟踪引用指到假的位置。
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
- HTTP 级核验可用（urllib）；**浏览器级核验（Playwright）已装好**，但装法有坑，记录如下：
  1. `pip install playwright` 在本机**会卡死**（pip 的网络路径不通，连小包都下不动）。可行做法：用 urllib 手动从阿里镜像下 wheel，再解压到工作区 `.pylibs/`（`*.whl` 就是 zip，`zipfile.extractall` 即可；`pip --target` 会因目录重命名被沙箱拒）。
  2. 需要的 wheel：`playwright-*-py3-none-win_amd64`、`greenlet-*-cp312-cp312-win_amd64`、`pyee-*-py3-none-any`（`typing_extensions` 运行时已自带）。
  3. 跑之前设 `$env:PYTHONPATH="$PWD\.pylibs"`；`.pylibs/` 已 gitignore（约 108MB）。
  4. **必须用完整权限（danger-full-access）跑**：Playwright 启动 Edge 要建命名管道，默认沙箱报 `PermissionError: [WinError 5]`；另外 `TEMP` 要指到工作区内（`$env:TEMP="$PWD\.tmp-pw"`），否则 `mkdtemp EPERM`。
  5. 浏览器用本机 Edge（`channel="msedge"`），**不需要** `playwright install chromium`。

## 6. 当前状态与待办

### 已上线（v1.25.0）
- 页码分页：每页 24 个，页码条「上一页/页码窗口/下一页/第 x/N 页 · 共 N 个」。
- **162 个项目**；AI 分类 26 个（2 页）；分页 7 页、末页 18 卡。
- **v1.25.0（2026-11-07）体验三件套**：筛选状态写入 URL（`?cat=&use=&sort=&p=&q=`，刷新/分享不丢）；卡片活跃度角标（只标异常：半年未更 / 停更 / 已归档——162 个里 131 个是 7 天内更新的，给活跃项目打标等于没信息）；详情页「相似项目」4 个（同分类+同语言+人群标签+人气量级加权）。
- **v1.25.0 数据管线**：`repos.json` 新增 `ar`（归档）字段；新增 `weekly.json` 每周 star 快照（CI 每周补一笔，保留 60 期），为周涨星榜/周刊铺路。
- v1.24.2（2026-11-07）新增 10 个：OpenClaw、Superpowers、OpenCode、Firecrawl、MarkItDown、CleanYourTV、DeepInfer、Aerial、肉呆去广告、课标知识图谱。
- 同步 10 个仓库改名（`Qwen2.5` → `Qwen3` 文案已重写；llama.cpp / React / React Native / OpenHands / ComfyUI / alist / LobeChat / LibreChat / developer-roadmap）。
- 已下架并确认线上 404：5 个大肥鱼插件（T-Auto/dsh-ops、QCYTSN/dsh-dafeiyu、liyupi/dafeiyu-cleaner、xiaoshihou514/dsh-desktop-pet、RYANFFY/deepseek-dafeiyu-pet）+ 早期下架的 legado（阅读）。
- 说明：`repos.json` 每小时被 CI 刷新，本地与远端差一个快照属正常，不是漂移。
- 工具：`verify_sync.py`（HTTP 级三方核验 + `--links` 链接巡检）+ `verify_browser.py`（24 项浏览器断言，期望值从 data.js 实时计算）。
- **v1.26.0（2026-11-07）内容板块**：专题合辑 5 个（装机必备 / 自媒体工具箱 / 本地 AI 入门 / 自建服务 / 零基础学编程，数据在 `collections.json`，可人工增删）；每周精选周刊 `weekly/`（本周新增 + 周涨星 Top10 + 总榜 + 归档提醒）；RSS `feed.xml`；补了 `favicon.ico`。
- 周刊首期（2026-11-07）是基线，**从第二期（约 11-14）开始才有「周涨星」**——依赖 `weekly.json` 累积两期以上。
- **v1.27.0（2026-11-07）**：新增「对比模式」（卡片点 ⇄ 对比，最多 3 个，弹窗并排比较 8 项）与每项目专属分享封面 `og/*.png`；分享卡片 `og:image` 指向各自封面。

### 待办/未决（等用户拍板，勿擅自做）
1. **dsh-our-free-model 是否收录**：Ebony-Vinyl/dsh-our-free-model（★64.8k）——用户未表态；按"插件非应用"的既有口径，建议维持不收。
2. **插件单独子项 + star 门槛方案**：用户曾提出「插件与应用不同类应单设子项」「低人气（如 star<100）应剔除」，方案暂缓，未重启。
3. **仓库改名巡检**：已做进 `verify_sync.py --links`（2026-11-07 新增，API 模式 162 个约 10 秒）。建议每月跑一次，把 `改名` 提示同步到 REPOS 与四张表。上次巡检（11-07）修了 10 个改名。
4. 宣传/引流侧物料在 `C:\Users\power\Documents\发现器开发-建议\`（视频、封面、脚本），如需再产出可参考其中的 make_video.py / 决策参考。

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

- [ ] 卡片有「⇄ 对比」，选 2 个能弹出对比表（v1.27.0）
- [ ] p 页 `og:image` 指向 `og/<owner>-<repo>.png` 且图片可访问（v1.27.0）

- [ ] 首页快捷入口能进合辑/周刊（v1.26.0）
- [ ] `c/` 5 个合辑 + 合辑内页项目数正确（v1.26.0）
- [ ] `weekly/` 有当期、`feed.xml` 可被解析（v1.26.0）

- [ ] 筛选写入 URL：点分类后地址栏出现 `?cat=…`，刷新不丢（v1.25.0）
- [ ] 停更项目的卡片有角标（半年未更 / 停更 / 已归档）（v1.25.0）
- [ ] 详情页底部有「相似项目」4 个（v1.25.0）

- [ ] sw.js 缓存名已升级（gh-cn-vXX）
- [ ] index.html GH_VER 正确
- [ ] 首页首屏 24 卡 + 页码条「第 1/7 页 · 共 162 个」
- [ ] 末页（第 7 页）18 卡
- [ ] 搜索关键词 0 结果空态正常
- [ ] 已下架项目的 p 页 404
- [ ] sitemap.xml 162 项目 + 首页 + list.html = 164 url
- [ ] 手机视口（375px）首屏可读、不闪白
