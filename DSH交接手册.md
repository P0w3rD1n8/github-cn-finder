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
| 当前版本 | **v1.33.1**（2026-11-15 上线，SW 缓存 gh-cn-v33，167 个项目 + 2026 年度精选） |
| 本地 commit | 与远端同步 = `6a14722`（2026-11-13 v1.32.1 搜索空态修复 + 手册） |
| 远端 main | `6a14722`（v1.32.1 / SW v31；线上 35 项断言全绿、验收已屏蔽百度统计） |

## 2. 文件职责一览

| 文件/目录 | 职责 |
|---|---|
| `data.js` | **数据主源（人工维护）**：`REPOS`（精选清单 `{n:"owner/repo"}`）+ `REPO_ZH`（中文名）+ `DETAIL`（中文详情四段式）+ `USAGE`（一句话用法）+ `CATS`（分类表）。**增删项目/改中文简介改这里**，然后跑 fetch-data.py |
| `fetch-data.py` | 数据抓取：读 `data.js` 的 `REPOS` 数组 → 调 GitHub API 抓 star/语言/描述等真实字段 → **写出** `repos.json`。CI 与本地均跑它 |
| `repos.json` | **自动产物，不要手改**：抓取结果（含 star/fork/hist 快照、`pa` 最近提交日、`ar` 是否归档），前端 fetch 使用；CI 定时刷新并提交（**实际间隔 4.9~11.4 小时，被 Actions 限流**，别再对外说「每小时」） |
| `weekly.json` | **自动产物**：每周一张全库 star 快照（`{date, stars}`，保留 60 期），由 fetch-data.py 维护，供「周涨星」和周刊页使用 |
| `build_pages.py` | 静态页生成器：由 data.js 生成 `p/<owner>-<repo>.html`（每个项目一个分享落地页）+ `list.html`（全列表）+ `sitemap.xml` |
| `build_extra.py` | **v1.26.0 新增**：生成 `c/`（专题合辑）、`weekly/`（每周精选）、`feed.xml`（RSS），并重写 sitemap 把附加页纳入 |
| `collections.json` | **人工策展数据**：专题合辑的标题/简介/项目清单，改这里增删合辑 |
| `c/` `weekly/` `feed.xml` | 自动产物（合辑页 / 周刊页 / RSS），不要手改 |
| `build_og.py` | **v1.27.0 新增**：用 Pillow 生成每个项目的 1200×630 分享封面（`og/<owner>-<repo>.png`），CI 里先装 pillow + fonts-noto-cjk 再跑 |
| `og/` | 自动产物：162 张分享封面（约 8MB）；**不加 star 数**，否则每小时都要重生成 |
| `build_timeline.py` | **v1.28.0 新增**：读 data.js 的 git 历史，比对前后 REPOS 名单，生成 `timeline/`（新增/下架/改名）。**CI 必须 `fetch-depth: 0`**，否则只有 1 个提交、页面为空 |
| `timeline/` | 自动产物：更新记录页（按日期倒序） |
| `screenshots/` | PWA 安装预览图（manifest screenshots 引用，手工放进去的静态资源） |
| `updates.json` | **自动产物**（build_timeline.py 生成）：首页更新状态条与最近上新读它，SW 里走 network-first |
| `indexnow.py` | **v1.33.1**：从 sitemap 取全部 URL 推给 Bing/搜狗（IndexNow 协议，无需账号）；CI 每次构建后自动跑 |
| `599d85….txt` / `4c57b8….txt` | IndexNow 密钥文件（各 32 位，站根托管，内容即 key 本身） |
| `annual.json` | **人工策展**：年度精选的年份/标题/分组/每个项目的「为什么选它」，改这里换榜 |
| `build_annual.py` | 生成 `annual/<year>.html` + `og/annual-<year>.png`；首页顶部横幅指向它 |
| `annual/` | 自动产物：年度精选页（index.html 自动跳当年） |
| `p/` | 152 个静态项目页（v1.24.1 现状） |
| `index.html` | 首页全部前端逻辑：分页、分类、搜索、收藏、海报、主题；版本号在 `window.GH_VER` |
| `sw.js` | Service Worker，缓存名 `gh-cn-v16`；**每次发版必须升级缓存名**，否则用户端不更新 |
| `README.md` | 对外 README：当前版本 + 版本历史（发版时同步） |
| `docs_summary.json` | README 摘要缓存（AI 文档摘要用） |
| `validate-data.js` | 数据校验脚本（CI 用） |
| `verify_sync.py` | **三方一致性核验工具**（本地工作区 ↔ 远端 main ↔ 线上 Pages）：行尾归一化比对、版本三件套、数据表死键/重复键/大小写错配、p 页状态码。用法见 §4 末尾 |
| `.github/workflows/data-update.yml` | 名义每小时第 15 分钟跑 fetch-data.py 并提交 repos.json；**实测被 Actions 限流，实际间隔 4.9~11.4 小时**（2026-11-15~16 六次运行），所以页面文案不再承诺「每小时」 |
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
- 自动：GitHub Actions 定时跑并提交（无需干预）。**别再对外说「每小时」**——2026-11-15~16 实测间隔 4.9~11.4 小时，首页与关于页已改成「定时自动同步」并显示数据时间。
- 手动：清代理 + openssl 后本地 `python fetch-data.py` 再提交。

## 4. 发版上线 SOP（v1.x.y）

每次内容或功能变更，按固定五步：

1. **三处版本号同步**（必须同时改）：
   - `index.html`：`window.GH_VER = "v1.x.y";`
   - `sw.js`：`const CACHE = "gh-cn-vXX";`（每次 +1，当前 v16 → v17）
   - `README.md`：当前版本 + 版本历史顶部加一条
2. **重新生成产物**：fetch-data.py → build_og.py → build_pages.py → build_extra.py → build_timeline.py（repos.json / og/ / p/ / list.html / sitemap.xml / c/ / weekly/ / feed.xml / timeline/ 全重建；data.js 是人工源不动）。
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

**verify_browser.py — 浏览器级行为验收（33 项）**
```powershell
$env:PYTHONPATH = "$PWD\.pylibs"     # playwright 装在工作区 .pylibs（见 §5.4）
& $py verify_browser.py --local      # 本地起 http.server 测当前工作区
& $py verify_browser.py              # 测线上
& $py verify_browser.py --headed     # 显示窗口调试
```
- 覆盖：首屏卡数 / 分页条 / 末页卡数 / AI 分类 / 搜索空态 / 搜索命中 / 静态页 / 控制台无报错 / 请求无失败 / 375px 手机端 / **v1.25.0 新增：筛选写 URL、刷新保持筛选、活跃度判定、停更角标、相似项目**。
- 截图落在 `_shots/`（已 gitignore）。
- 已知口径：搜索会同时查 GitHub API，**无意义关键词才会 0 结果**；前端会主动取消上一轮搜索请求，`ERR_ABORTED` 不计为失败。
- **v1.31.1 起：验收不再污染百度统计**。脚本对每个 context 调 `block_analytics()`，把 `hm.baidu.com` / `hmcdn.baidu.com` / `zz.bdstatic.com` 的请求**返回空脚本**（用 fulfill 而不是 abort，否则控制台会报 ERR_FAILED 干扰断言）。跑完会打印「已拦截统计上报 N 次」。
  背景：v1.31.0 那天连跑 4 次线上验收，给自己刷了 50~80 PV，导致当天峰值判断失真。**以后线上验收想跑几次都行，数据是干净的。**

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
- **v1.32.1 补充（重要）：加速器开着时必须走代理，不能清空**。`git config --global http.proxy` = `http://127.0.0.1:7897`；
  2026-11-13 晚实测：直连（`-c http.proxy=`）报 `Recv failure: Connection was reset` / `Failed to connect`，
  而 `-c http.proxy=http://127.0.0.1:7897 -c https.proxy=...` 一次成功。
  **判据**：先 `Test-NetConnection github.com -Port 443`，通了再试；两种模式各试一次，哪个通用哪个。
  另一个坑：GitHub 不可达时 push 默认超时可达 **5 分钟**，批量重试前先探端口，避免白等。
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

### 5.5 Service Worker 缓存策略（v1.27.1，别改回去）
- **问题**：安卓 Edge 上要刷新好几次才看到新版。两层原因：① 导航走 stale-while-revalidate 先给旧缓存；② `sw.js` 自己也被 HTTP 缓存（GitHub Pages `max-age=600`），旧 SW 不退。
- **现在的策略**：页面导航、`data.js`、`repos.json` 一律 network-first，且 `fetch(req, {cache: "reload"})` 绕过 HTTP 缓存。
- **坑**：导航请求用 `cache: "no-store"` 会失败并静默回退到缓存（表现为「怎么刷都是旧版」），**必须用 `reload`**。
- **注册**：`register("sw.js", {updateViaCache: "none"})` + 页面可见时主动 `reg.update()`。
- **自动刷新**：`controllerchange` 时刷新一次（`sessionStorage` 防循环）；收到 `APP_UPDATED` 且用户还没滚动/点击过就静默刷新，动过手则只弹提示。
- **上线次次生效，但用户侧仍有一次滞后**：新 SW 要装到设备上才会用新策略，所以 v1.27.1 这次用户可能还要多刷一次；之后每次发版都是「一次刷新」或自动刷新。

### 5.6 搜索引擎收录：Bing 站长 + IndexNow（v1.33.1 起）
- **背景**：2026-11-15 实测搜「GitHub 中文发现器」**搜不到本站**（只出 GitHub 仓库），此前文案里写"搜站名"是无效引导。
- **Bing 站长**：`https://www.bing.com/webmasters` → Microsoft 账号登录 → 添加站点，**必须填完整子路径**
  `https://p0w3rd1n8.github.io/github-cn-finder/`（GitHub Pages 项目站不是域名根）。
  验证方式选「HTML 元标记」，把 `<meta name="msvalidate.01" content="…">` 放进 `index.html` 的 `<head>`（已在第 9~10 行），推上去后点「验证」。
- **网站地图**：左侧菜单叫「**网站地图**」（不是 Sitemaps），提交 `https://p0w3rd1n8.github.io/github-cn-finder/sitemap.xml`。
  2026-11-15 结果：已知 1 个、错误 0、警告 0、**已发现 181 个 URL**、当天爬过。
- **IndexNow**（Bing/搜狗/Yandex 主动推送）：**开放协议，不需要注册**，满足三条即可——
  ① 站根有 `{key}.txt`，内容是这串 key；② 推送带同一个 key；③ 带 `keyLocation` 指向该文件。
  脚本 `indexnow.py` 从 `sitemap.xml` 取全部 URL POST 到 `api.indexnow.org`，**200/202 都是受理**。
  已接进 `build-pages.yml`（`python indexnow.py || true`，失败不阻断构建）。
  **站点当前托管两个 key 文件**（`599d85…` 与 `4c57b8…`，都 32 位），对应后台可能显示的任一个。
- **Portal 页面 ≠ 成效**：Bing 左侧「IndexNow」页是文档/统计，显示"未验证"不影响推送生效；判断是否收录只看两处——
  `site:p0w3rd1n8.github.io` 搜索结果，以及「网站地图」里的"上次爬网时间/已发现 URL"。
- **预期**：24 小时内开始抓，1 周内名称能搜到，2~4 周长尾词才有排名；**收录 ≠ 流量**，排名还靠外链和时间。
- **百度**另需 `ziyuan.baidu.com`（国内手机号+实名），且对 GitHub Pages 收录很慢，暂不做。

### 5.7 对外发布合规（小红书，2026-11-15 被判违规后总结）
- **触发**：置顶评论放了 `https://p0w3rd1n8.github.io/github-cn-finder/`，被判「笔记存在外部平台信息或联系方式」→ **限制推荐和搜索展示**（粉丝可见，等于没流量）。
- **红线（都要守）**：
  1. **图片里不放网址/二维码/水印**——包括自动生成的封面（`build_social.py` 已改为不印域名，只写站名）
  2. **评论区不放链接**，置顶也不行
  3. 正文不写"搜索 xx""公众号 xx""主页简介有链接"这类引导
  4. 站名可提，但**不加"去搜"**
- **正确做法**：笔记必须**自包含**（读者看完这篇就够），收尾只用"想看的可以关注我"。
- **处置后**：先申诉（话术：已删除外部链接+图片已更换，请求复核）；24 小时没恢复就删掉换干净图重发。
- **教训**：写文案前先验证"读者照做能不能做到"——"搜站名"当时搜不到，等于让读者做无效动作。

### 5.8 CC Safety Net（用户 2026-11-16 装的执行前安全护栏）
- **它会拦我**：装好后凡是读 ~/.git-credentials 的命令一律 BLOCKED by CC Safety Net（规则 secret.basename.git-credentials），
  而本项目的 push 流程正好要读这个文件取 token → 直接把发版卡死。
- **规矩**：policy.json（~/.cc-safety-net/policy.json 用户级、.cc-safety-net/policy.json 项目级）
  **读可以、写不行**——必须写提案 → policy check <file> --global 校验 → **用户本人在终端**跑 policy apply（交互确认）。
  **助手禁止执行 apply、禁止包装、禁止直接改文件**，这是它的设计。
- **现状**：用户级策略已加 secret_protection.allow_paths: [~/.git-credentials]，push 恢复正常。
  只放行了这一个文件，其他凭据（~/.ssh、.env）仍被拦。
- **别提交**：不要把 policy.json、提案文件写进仓库（提案放 %TEMP% 即可）。
- **自查命令**：cc-safety-net status / doctor / explain "<命令>" / logs，
  bin 在 ~/.dsh/profiles/desktop/node_modules/cc-safety-net/dist/bin/cc-safety-net.js，用 DSH 自带 node 跑。
- **审计日志**：~/.cc-safety-net/logs/<工作区>/<年月>/<session>.jsonl，每条记录我的命令与 allow/block 决策——
  排查"我到底跑过什么"时先看这里。

### 5.9 小红书 Red Skill「开源项目选型助手」（2026-11-21 上线）

**是什么**：小红书 Builder Hub 里的 Red Skill = 「Prompt + AI 能力 + 工作流」打包成可安装的 Skill。
创作者上传 `SKILL.md` 文件夹 → 审核 → 发笔记时挂「组件」，用户点开一键复制口令装进自己的 Agent。
**这是唯一不需要外链的渠道**——站外链接不可点、导流会限流（§5.7），而 Skill 是平台内官方形态。

**素材位置**（都在 `content/`）：
- `xhs-skill/SKILL.md` + `references/{rubric,pitfalls,catalog}.md` —— 源文件
- `build_xhs_skill.py` —— 一键重生成 catalog + 打两个包（完整版含 catalog / 安全版不含）
- `xhs-skill-safe.zip` —— 上传用（当前线上版本系列）
- `RedSkill发布说明.md` / `RedSkill填写文案.md` / `RedSkill测试清单.md` —— 流程、字段值、验收用例
- `xhs-skill-粘贴版.txt` —— 给读不到本地文件的 Agent 用（单文件 7043 字）

**填写字段的坑**：字段跟「小工具」那套**不一样**。
- 唯一标识：英文/数字/连字符（本站填 `open-source-picker`）
- **简介上限 1000 字**（不是 14 字，那是小工具）
- 场景标签选项：效率工具 / 内容创作 / 学习成长 / 职场办公 / **编程开发** / 生活决策 / 金融理财 / 其它（选「编程开发」）
- 版本号必填；**编辑已生效的 Skill 不需要升版本号**（用户实测），但上传新源码包要升

**被拒 → 通过的真实过程（重要）**：
1. **1.0.0 原始版**（含 catalog，用词直白）：21:05 提交，**21:08 未通过**——3 分钟，说明是机审。
2. **查不到理由**：卡片「版本历史」只显示「未通过」+ 时间；站内信/通知中心也没有。
3. **1.0.1**：删掉 `catalog.md` + 把「刷」「磁力」「影视」「账号池」「免 API Key」「引流」等改成中性说法 → **通过**。
4. **但这是两个变量同时改的**，无法确定哪个是关键；也不能排除 1.0.0 是偶发误判（没有复测原始版）。
5. **教训**：「未通过且无理由」时，最稳的第一步其实是**原样重传一次**确认是否偶发；
   但机审 3 分钟出结果、反复失败可能影响账号信用，所以要在"多试一次"和"一次排干净"之间权衡。
   **别像我这次一样，先断言「3 分钟=机审拦敏感词」，然后被推翻两次**——先确认再下结论。

**四个测试用例的结论（豆包 vs Work Buddy/Hy4 Flash）**：

| 用例 | 输入 | 豆包 | WB（Hy4 Flash 免费） |
|---|---|---|---|
| 一 · 正常项目 | `syncthing/syncthing` | ✅ 判「推荐用」 | ✅ 判「可以用但有条件」，门槛判**中**（更严） |
| 二 · 可疑项目 | `Ebony-Vinyl/dsh-our-free-model` | ✅ 劝退，但数据是 3 天前缓存 | ✅ 劝退，数据**实时准确**（82,823 / 纯 issue 179） |
| 三 · 不存在项目 | `foo/this-repo-does-not-exist-12345` | ✅ 四信号全「查不到」，还核了账号是否存在 | ✅ 按第一步直接反问，不猜 |
| 四 · 无联网模型 | `facebook/react` | 跳过（豆包能联网） | 未测 |

**两个模型的关键差异（选 Agent 时的参考）**：
- 豆包：**能查实时数据，但不是每次都查**。对 `dsh-our-free-model` 报 star 78,900、最后提交 11-18，
  却声明「数据来自本次 GitHub API 读取」——实际是 3 天前的缓存页（真实值 82,797 / 11-21）。
- Hy4 Flash：同一条用例报 82,823 / 纯 issue 179 / 今天推送，与独立核对完全一致；
  连 `open_issues_count` 里混着 PR 都做了拆分（406 − 45 PR = 179 issue）。
- **结论**：模型能不能拿到实时数据，跟模型强弱无关，跟它这次走的是直播 API 还是搜索缓存有关。
  所以 Skill 里必须有「报数字要注明数据时点」这条兜底。

**测试逼出来的三条规则改进（已进 1.0.2）**：
1. **门槛判定看"普通人能不能自己搞定"，不看"有没有安装包"**——豆包判 syncthing 为「中」，
   理由「便携包但要配对设备」，比我原来写的「便携包=低门槛」更对。
2. **报数字必须注明数据时点**，无法确认实时就写「数据可能不是最新的」。
3. **绝对不要凭记忆报数字**：四项数据要么真查到，要么写「查不到」；编一个合理数字比说不知道更糟。

**已上线（2026-11-22）**：
- **笔记已发布**：https://www.xiaohongshu.com/discovery/item/6b01ac52000000001603feaa
  标题「GitHub 上 star 高就一定好用吗」，三张 3:4 配图（`xhs-note-{1,2,3}-*.png`），组件已挂载
- **组件实测通过**：手机端点开会弹出复制口令 → 读者链路通畅（不是只"看起来挂上了"）
- 线上 Skill 版本：**1.0.1**（删 catalog + 敏感词中性化那版，1.0.2 的改进还没传）

**待办**：
- 上传 1.0.2（数据时点 + 门槛判定两条改进）。
  **注意：更新 Skill 不需要重发笔记**——笔记挂的是 Skill 的引用，组件会自动用新版
- 观察窗口（发布后 24~48 小时）：**阅读量 + 组件点击**。
  **最该看的比值是「组件点击 ÷ 阅读量」**：阅读多点击少 = 内容行但转化弱；阅读少点击多 = 精准但量小，两种修法完全不同
- **已知限制（2026-11-22 用户实测）**：小红书后台**不提供 Skill 安装数**，
  数据看板 / Red Skill 详情 / 笔记数据三处都找不到。别再去找了——
  想看"有没有人真的装上用"，只能用组件点击数 + 评论区互动（有人问"怎么用/装不上"才算真有人试）
- 下一版可以加进 pitfalls 的两条（测试中发现，但没来得及进 1.0.2）：
  - **远程控制已安装实例**：作者可从仓库向所有已装用户推送公告、弹窗、一键替换升级
  - **低 fork 率也可能是异常**：fork/star 远低于 5%（如 2.8%）配合「短时间高星」时，同样是可疑信号

### 5.10 跨机器共享会话（极空间「文档同步」，2026-11-23 起）

**目标**：家里 PC 和公司 PC 能看到同一批 DSH 会话，不用两台同时开着。

**背景**：DSH 是本地应用，会话存在本机
`~/.dsh/sessions/--<工作区路径编码>--/session-<uuid>/`（JSONL，默认 Zstd 压缩帧）。
DSH **没有**云端会话同步；豆包那种跨设备记忆是云应用才有的能力。

**方案**：用极空间 PC 客户端的「文档同步 → 双向同步」，不装 Docker / Syncthing / 组网工具。

已建两个任务（家里 PC，均为**手动同步** + 开启本地回收站 + 删除策略两条都勾）：

| 本地 | 极空间 | 规模 |
|---|---|---|
| `C:\Users\power\.dsh\sessions` | `/我的文件/dsh-sessions` | 7 文件 / 13.3 MB |
| `C:\Users\power\.dsh\attachments` | `/我的文件/dsh-attachments` | 203 文件 / 45.6 MB |

**为什么选手动同步**：会话是 DSH 运行中持续 append 的，自动同步可能复制到半写状态；
手动同步强制「同步时 DSH 是关着的」，把风险降下来。

**公司 PC 侧步骤**：
1. 装 DSH（版本对齐 `0.2.2-rc.5`），先开一次生成 `~/.dsh`（会多一个空会话，无害）
2. 关掉 DSH
3. 极空间客户端建两个双向同步任务：本地选公司机器上的两个目录，
   **极空间端选已存在的 `/dsh-sessions`、`/dsh-attachments`（不要新建）**
4. 同步策略同样选手动；删除策略两条都勾
5. 验证分两步（见下）

**验证顺序（两步必须分开看）**：
1. **文件层面**：看 `C:\Users\<用户名>\.dsh\sessions\` 里有没有
   `--C-Users-power-GitHub~4E2D~6587~53D1~73B0~5668--` 目录
   → 有 = 同步成功；没有 = 同步没成，与路径无关
2. **列表层面**：开 DSH 看会话列表是否显示
   → ① 成功但 ② 不显示 = **会话列表按工作区路径过滤**，需要统一两台机器的仓库路径

**待办：统一仓库绝对路径（等 DSH 关闭时做，零代码改动）**

会话目录名是**工作区绝对路径**编码出来的，两台路径不同就归到不同目录。
目标：两台都用 `C:\work\github-cn-finder`（或两台都存在的同一盘符同一路径）。

挪动前已核实：
- **代码里没有硬编码绝对路径**（`.py`/`.html`/`.json`/`.yml` 全部为零）
- 只有 `DSH交接手册.md` 里有 12 处 `C:\Users\power\...` 需要跟着改
- 仓库 880 个文件 / 164 MB，`git` 用相对路径，挪动不影响 `git`

步骤：① 关掉 DSH → ② 移动整个仓库目录 → ③ 改手册 12 处路径 →
④ 两台都从新路径打开 DSH → ⑤ 再点一次极空间同步

**纪律（否则会丢数据）**：
- **同一时间只在一台电脑上开 DSH**，否则两边同时写会话
- **不要在 `~/.dsh/sessions` 或 `attachments` 里手动删改文件**——删除策略是双向的
- **不要同步 `profiles` 和 `.credentials.yaml`**（凭据不上 NAS）
- 极空间客户端要**开机自启**（手动同步靠它点按钮）

## 6. 当前状态与待办

> ⚠️ **本节内容停留在 v1.25.0（162 个项目）**，已明显滞后（2026-11-21 时线上是 v1.39.x / 172 个项目）。
> 看最新状态请以 **README 的版本历史** 与 **§5.6 / §5.9** 为准；本节下面这段只作历史参考。

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
- **v1.32.0（2026-11-13）首屏意图入口 + 真实涨星**：首页搜索框下加 4 个大按钮（装机必装/AI 工具/学编程/手机 App），点了直接筛分类——针对新访客平均只停 44 秒；「今日推荐」从按日期取模改为真实涨星（2 期周快照用「本周最热」，否则「近 24 小时最热」），显示涨幅数字，点击进站内详情页而不是跳 GitHub。
- **v1.32.1（2026-11-13）搜索空态修复**：线上偶发看不到空态文案（接口 >2 秒，验收固定等 2 秒读到 loading）→ 验收改 wait_for_selector(.empty)，前端加 10 秒超时兜底。
- **v1.30.0（2026-11-11）年度精选**：`annual/2026.html`，20 个项目分 5 组（装机必装 / AI 这一年 / 程序员利器 / 创作者工具 / 学与玩），每个项目一句「为什么选它」；首页顶部紫色横幅入口 + 专属分享封面。策展在 `annual.json`，每年改这个文件即可复用。
- **v1.29.0（2026-11-11）首页露出更新**：更新记录不能只藏在快捷入口——首页第一屏加「🟢 每小时自动刷新 star · 数据时间 · 本周上新 N 个 · 全部更新记录 →」状态条，外加「✨ 最近上新」横排（最近 10 个新项目）。数据来自 `updates.json`，本周上新按 7 天窗口从 git 历史统计；本周无新增时降级显示「最近上新 日期」。快捷入口改成单行横滑（`flex:0 0 auto` + `nowrap`，否则中文会被压成竖排）。
- **v1.28.0（2026-11-11）**：新增「更新记录」时间线页 `timeline/`（从 git 历史算新增/下架/改名，改名识别先用仓库名、再用 owner 配对）；PWA 加 4 个长按快捷方式（推荐/榜单/收藏/周刊，`?tab=` 直达）、安装预览截图、稳定 `id`。
- **v1.27.2（2026-11-08）补镜像**：GitCode 镜像 131 → 144 条，缺镜像 27 → 14。做法是枚举 `GitHub_Trending/` 与 `gh_mirrors/` 的候选前缀，**再用页面 `<title>` 精确解析 `owner/repo` 比对**；只靠"页面里出现仓库名"会误判（`gh_mirrors/op/openclaw` 实际是 `pjasicek/OpenClaw`、`GitHub_Trending/co/core` 实际是 `home-assistant/core`）。
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

- [ ] 手机端刷新一次即看到新版本；SW 缓存名为当前版本（v1.27.1）
- [ ] `timeline/` 有更新记录、`?tab=rank` 能直达榜单、manifest 里有 4 个快捷方式（v1.28.0）
- [ ] `annual/2026.html` 有 20 个项目、首页顶部有年度横幅（v1.30.0）
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
