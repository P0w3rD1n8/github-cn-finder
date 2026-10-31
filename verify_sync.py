#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GitHub 中文发现器 · 本地 / 远端 main / 线上 Pages 三方一致性核验（仅标准库）

用法：
    <DSH python> verify_sync.py [--repo <本地仓库路径>] [--json] [--fetch] [--pages|--full-pages]

核验项：
  A. 本地工作区 vs 远端 main：逐文件比对，区分「真内容差异」与「仅 CRLF/LF 差异」
  B. 线上站点 vs 本地文件：行尾归一化后 sha256 比对（CRLF 噪声不算差异）
  C. 版本三件套：index.html GH_VER / sw.js CACHE / README 当前版本，且本地=线上
  D. 线上 p/ 页：在册页必须 200；历史下架页（从 git 历史自动推算）必须 404
  E. data.js 数据表：REPOS 与 CN_DESC/REPO_ZH/DETAIL/USAGE/镜像/AUTHORS 的键对齐、死键、重复键
  F. repos.json 快照时间（本地 vs 线上）

说明：
  - 本机 git 走 HTTPS 需 `-c http.sslBackend=openssl`，脚本内部已带该参数。
  - 系统 schannel 对 GitHub/Pages 会报 SEC_E_NO_CREDENTIALS，故所有 HTTP 显式绕过代理 + 用 OpenSSL。
  - 不依赖 GitHub API（避免 60/h 限流），远端内容直接从本地已 fetch 的 origin/main 读。
退出码：0 全绿；1 有问题（problems 非空）。
"""
import argparse
import hashlib
import json
import os
import re
import ssl
import subprocess
import sys
import urllib.error
import urllib.request

BASE = "https://p0w3rd1n8.github.io/github-cn-finder"
CTX = ssl.create_default_context()
OPENER = urllib.request.build_opener(
    urllib.request.ProxyHandler({}),
    urllib.request.HTTPSHandler(context=CTX),
)

PAGE_FILES = ["index.html", "sw.js", "data.js", "sitemap.xml", "list.html", "manifest.json", "robots.txt"]
LOADED = 0

def fetch(url, head=False, timeout=12, retries=1):
    last = None
    for _ in range(retries + 1):
        req = urllib.request.Request(
            url, method="HEAD" if head else "GET",
            headers={"User-Agent": "gh-cn-finder-verify/1.0", "Cache-Control": "no-cache"},
        )
        try:
            with OPENER.open(req, timeout=timeout) as r:
                return r.status, (b"" if head else r.read())
        except urllib.error.HTTPError as e:
            return e.code, b""
        except Exception as e:  # noqa: BLE001
            last = e
    raise last


def norm(b):
    return b.replace(b"\r\n", b"\n")


def sha1_blob(b):
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def say(msg):
    print(msg, flush=True)


def read(path):
    with open(path, "rb") as f:
        return f.read()


def git(repo, *args, binary=True, timeout=120):
    cmd = ["git", "-C", repo, "-c", "core.quotePath=false",
           "-c", "http.sslBackend=openssl", "-c", "http.proxy=", "-c", "https.proxy="] + list(args)
    env = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        env.pop(k, None)
    try:
        r = subprocess.run(cmd, capture_output=True, env=env, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"git {' '.join(args)[:60]} 超时({timeout}s)")
    out = r.stdout if binary else r.stdout.decode("utf-8", "replace")
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode("utf-8", "replace")[:400])
    return out


def extract_obj(src, name):
    """取 const NAME = { ... }; 的对象体（单行/多行通吃，非贪婪）"""
    m = re.search(r"const " + name + r" = \{(.*?)\};", src, re.S)
    return m.group(1) if m else None


def extract_arr(src, name):
    """取 const NAME = [ ... ]; 的数组体"""
    m = re.search(r"const " + name + r" = \[(.*?)\n\];", src, re.S)
    return m.group(1) if m else None


def keys_in(body):
    """对象体里的键（只认 owner/repo 形状，值里的 URL/中文不会误判）"""
    return re.findall(r'"([A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+)"\s*:', body)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--pages", action="store_true", help="抽样 12 个 p 页检查线上状态码（慢，受网络影响）")
    ap.add_argument("--full-pages", action="store_true", help="扫描全部 p 页（最慢）")
    ap.add_argument("--page-budget", type=int, default=45, help="p 页扫描的总时间预算（秒，默认 45）")
    ap.add_argument("--fetch", action="store_true", help="先 git fetch 刷新 origin/main（默认不 fetch，避免网络挂起）")
    args = ap.parse_args()
    repo = os.path.abspath(args.repo)
    report = {"repo": repo, "problems": [], "checks": {}}
    P = report["problems"]

    # ---------- A. 本地 vs 远端 main ----------
    say("① 本地工作区 ↔ 远端 main …")
    if args.fetch:
        try:
            git(repo, "fetch", "origin", "main")
        except Exception as e:  # noqa: BLE001
            P.append(f"git fetch 失败（继续用已有 origin/main）: {e}")

    try:
        head = git(repo, "rev-parse", "HEAD", binary=False).strip()
        remote = git(repo, "rev-parse", "origin/main", binary=False).strip()
        remote_paths = [p for p in git(repo, "ls-tree", "-r", "--name-only", "origin/main", binary=False).splitlines() if p]
        tracked = [p for p in git(repo, "ls-files", binary=False).splitlines() if p]
    except Exception as e:  # noqa: BLE001
        print(f"❌ 无法读取 git 信息: {e}")
        return 2

    content_diff, crlf_only, missing_local = [], [], []
    remote_true = None
    try:  # 真实远端 head（1 次 API，用来看本地 origin/main 引用是否过期）
        st, body = fetch("https://api.github.com/repos/P0w3rD1n8/github-cn-finder/git/ref/heads/main")
        if st == 200:
            remote_true = json.loads(body.decode("utf-8"))["object"]["sha"]
    except Exception:  # noqa: BLE001
        remote_true = None

    stale_ref = bool(remote_true and remote_true != remote)
    dirty = [x for x in git(repo, "status", "--porcelain=v1", binary=False).splitlines() if x.strip()]

    if stale_ref and remote_true == head:
        # 本地已推送（例如用 URL 推送，origin/main 引用没更新）——逐文件比对没有意义
        say(f"   ⚠ 本地 origin/main 引用停在 {remote[:10]}，真实远端已是 {remote_true[:10]}（= HEAD，已推送）")
        say("     跳过逐文件比对；如需精确比对先跑一次 `--fetch`")
    else:
        for p in remote_paths:
            fp = os.path.join(repo, p.replace("/", os.sep))
            if not os.path.exists(fp):
                missing_local.append(p)
                continue
            lb = read(fp)
            rb = git(repo, "show", f"origin/main:{p}")
            if lb == rb:
                continue
            if norm(lb) == norm(rb):
                crlf_only.append(p)
            else:
                content_diff.append(p)
        if stale_ref:
            say(f"   ⚠ 本地 origin/main 引用({remote[:10]}) 与真实远端({remote_true[:10]}) 不一致，比对结果可能失真")

    only_local = sorted(set(tracked) - set(remote_paths)) if not stale_ref else []
    report["checks"]["repo"] = {
        "head": head[:10], "remote_main": remote[:10], "remote_true": (remote_true or "")[:10],
        "stale_ref": stale_ref,
        "files_remote": len(remote_paths), "files_tracked": len(tracked),
        "content_diff": content_diff, "crlf_only": crlf_only,
        "missing_local": missing_local, "only_local_tracked": only_local,
        "dirty": dirty,
        "clean": not (content_diff or missing_local or only_local) and not dirty,
    }
    if content_diff:
        P.append(f"本地与远端有真实内容差异: {content_diff[:10]}")
    if missing_local:
        P.append(f"远端有、本地缺: {missing_local[:10]}")
    if only_local:
        P.append(f"本地已跟踪、远端没有: {only_local[:10]}")
    if dirty:
        P.append(f"工作区有未提交改动: {dirty[:6]}")

    # ---------- B/C. 线上 vs 本地 ----------
    say("② 线上站点 ↔ 本地文件 …")
    live = {}

    def get_live(name):
        try:
            st, body = fetch(f"{BASE}/{name}", timeout=15)
            return name, st, body, None
        except Exception as e:  # noqa: BLE001
            return name, None, b"", f"{type(e).__name__}: {str(e)[:70]}"

    # 并发抓（串行时任一请求卡住会把整轮拖成分钟级）
    import concurrent.futures as _cf
    with _cf.ThreadPoolExecutor(max_workers=len(PAGE_FILES)) as ex:
        for name, st, body, err in ex.map(get_live, PAGE_FILES):
            live[name] = {"status": st, "body": body}
            if err:
                P.append(f"线上 {name} 取回失败（网络）: {err}")

    rows = []
    for name in PAGE_FILES:
        lp = os.path.join(repo, name)
        if not live[name]["body"] or not os.path.exists(lp):
            continue
        lb = read(lp)
        rows.append({
            "file": name,
            "identical": sha256(lb) == sha256(live[name]["body"]),
            "identical_norm": sha256(norm(lb)) == sha256(norm(live[name]["body"])),
            "local_len": len(lb), "live_len": len(live[name]["body"]),
        })
    report["checks"]["live_vs_local"] = rows
    for r in rows:
        if not r["identical_norm"]:
            P.append(f"线上与本地内容不同: {r['file']}")

    def txt(name):
        return live.get(name, {}).get("body", b"").decode("utf-8", "replace")

    def grab(s, pat):
        m = re.search(pat, s)
        return m.group(1) if m else None

    local_index = read(os.path.join(repo, "index.html")).decode("utf-8", "replace")
    local_sw = read(os.path.join(repo, "sw.js")).decode("utf-8", "replace")
    local_readme = read(os.path.join(repo, "README.md")).decode("utf-8", "replace")
    ver = {
        "local_index_ver": grab(local_index, r'GH_VER\s*=\s*"(v[\d.]+)"'),
        "live_index_ver": grab(txt("index.html"), r'GH_VER\s*=\s*"(v[\d.]+)"'),
        "local_sw_cache": grab(local_sw, r'const CACHE\s*=\s*"(gh-cn-v\d+)"'),
        "live_sw_cache": grab(txt("sw.js"), r'const CACHE\s*=\s*"(gh-cn-v\d+)"'),
        "local_readme_ver": grab(local_readme, r'当前版本：\*\*(v[\d.]+)\*\*'),
    }
    report["checks"]["version"] = ver
    # 只在两边都取到值时才判不一致（线上取回失败时 live_* 为 None，属网络问题，别误报）
    if ver["live_index_ver"] and ver["local_index_ver"] != ver["live_index_ver"]:
        P.append(f"版本不一致: 本地 {ver['local_index_ver']} / 线上 {ver['live_index_ver']}")
    if ver["live_sw_cache"] and ver["local_sw_cache"] != ver["live_sw_cache"]:
        P.append(f"SW 缓存名不一致: 本地 {ver['local_sw_cache']} / 线上 {ver['live_sw_cache']}")
    if ver["local_readme_ver"] != ver["local_index_ver"]:
        P.append(f"README 版本未同步: {ver['local_readme_ver']} vs index {ver['local_index_ver']}")

    # ---------- E. data.js 数据表 ----------
    say("③ data.js 数据表对齐 …")
    src = read(os.path.join(repo, "data.js")).decode("utf-8")
    rep_body = extract_arr(src, "REPOS")
    repos = re.findall(r'\{n:"([^"]+)"', rep_body or "")
    rep_set, rep_low = set(repos), {r.lower() for r in repos}
    owners = {r.split("/")[0] for r in repos}
    tables = {}
    for name, lowered in (("CN_DESC", False), ("REPO_ZH", False), ("DETAIL", False), ("USAGE", False),
                          ("GC_MIRRORS", True), ("GT_MIRRORS", True)):
        body = extract_obj(src, name)
        if body is None:
            tables[name] = {"missing_block": True}
            continue
        ks = keys_in(body)
        dead, casefix = [], []
        for k in ks:
            if lowered:
                if k.lower() not in rep_low:
                    dead.append(k)
            elif k not in rep_set:
                (casefix if k.lower() in rep_low else dead).append(k)
        missing = [r for r in repos if r not in set(ks)] if not lowered else []
        tables[name] = {
            "keys": len(ks), "unique": len(set(ks)),
            "dups": sorted({k for k in ks if ks.count(k) > 1}),
            "dead": dead, "case_mismatch": casefix, "missing": missing,
        }
        if tables[name]["dups"]:
            P.append(f"{name} 有重复键: {tables[name]['dups']}")
        if dead:
            P.append(f"{name} 有死键(不在 REPOS): {dead[:8]}")
        if casefix:
            P.append(f"{name} 有大小写错配键: {casefix[:8]}")
        if missing:
            P.append(f"{name} 缺 REPOS 条目: {missing[:8]}")

    auth_body = extract_obj(src, "AUTHORS")
    auth_keys = re.findall(r'"([A-Za-z0-9_.\-]+)"\s*:\s*\{t:', auth_body or "")
    auth_dup = sorted({k for k in auth_keys if auth_keys.count(k) > 1})
    auth_orphan = sorted(set(auth_keys) - owners)
    tables["AUTHORS"] = {"keys": len(auth_keys), "dups": auth_dup, "orphan": auth_orphan}
    if auth_dup:
        P.append(f"AUTHORS 有重复键（后者静默覆盖前者）: {auth_dup}")
    if auth_orphan:
        P.append(f"AUTHORS 键不是任何 REPOS 的 owner（可能是大小写错配）: {auth_orphan}")

    report["checks"]["tables"] = {"repos": len(repos), "repos_unique": len(rep_set), "detail": tables}
    if len(rep_set) != len(repos):
        P.append("REPOS 有重复仓库条目")

    # ---------- F. repos.json 快照 ----------
    local_rj = json.loads(read(os.path.join(repo, "repos.json")).decode("utf-8"))
    live_rj_txt = txt("data.js")  # 线上 data.js（取回失败时为空串）
    report["checks"]["repos_json"] = {
        "local_updated": local_rj.get("updated"),
        "local_count": len(local_rj.get("repos", {})),
        "live_data_repos": len(re.findall(r'\{n:"', live_rj_txt)) if live_rj_txt else None,
    }
    if report["checks"]["repos_json"]["local_count"] != len(repos):
        P.append(f"repos.json 条数({report['checks']['repos_json']['local_count']}) ≠ REPOS({len(repos)})")

    # ---------- D. 线上 p 页（默认不扫；--pages 抽样 / --full-pages 全量） ----------
    if not (args.pages or args.full_pages):
        report["checks"]["pages"] = {"skipped": True}
    else:
        import concurrent.futures as cf
        import time as _time

        pdir = os.path.join(repo, "p")
        pages_all = sorted(f for f in os.listdir(pdir) if f.endswith(".html"))
        if args.full_pages or len(pages_all) <= 12:
            pages = pages_all
        else:
            step = max(1, len(pages_all) // 12)
            pages = pages_all[::step][:12]
        budget = args.page_budget
        say(f"④ p 页扫描：{'全量' if args.full_pages else '抽样'} {len(pages)}/{len(pages_all)} 个，预算 {budget}s")

        def head(fname):
            try:
                st, _ = fetch(f"{BASE}/p/{fname}", head=True)
                return fname, st, None
            except Exception as e:  # noqa: BLE001
                return fname, None, type(e).__name__

        def sweep(names, workers, budget_s):
            """并发 HEAD，超出预算就放弃剩余；网络错误单独归类，不算内容问题"""
            ex = cf.ThreadPoolExecutor(max_workers=workers)
            futs = {ex.submit(head, f): f for f in names}
            done, bad, netfail = 0, [], []
            try:
                for fut in cf.as_completed(futs, timeout=budget_s):
                    fname, st, err = fut.result()
                    done += 1
                    if err:
                        netfail.append([fname, err])
                    else:
                        bad.append([fname, st])
            except cf.TimeoutError:
                pass
            finally:
                ex.shutdown(wait=False, cancel_futures=True)
            return done, bad, netfail

        done, results, netfail = sweep(pages, 12, budget)
        not_200 = [[f, st] for f, st in results if st != 200]

        # 下架清单：git 历史里出现过、现在已删的 p 页（自动维护，无需手写）
        try:
            hist = git(repo, "log", "--all", "--diff-filter=D", "--name-only", "--pretty=format:", "--", "p/", binary=False)
            removed = sorted({os.path.basename(x) for x in hist.splitlines() if x.startswith("p/") and x.endswith(".html")})
            removed = [f for f in removed if f not in set(pages_all)]
        except Exception:  # noqa: BLE001
            removed = []

        rd, rres, rnet = sweep(removed, 8, max(15, budget // 2)) if removed else (0, [], [])
        still_live = [[f, st] for f, st in rres if st != 404]

        report["checks"]["pages"] = {
            "total": len(pages_all), "checked": done, "not_200": not_200,
            "network_errors": netfail, "removed_checked": rd, "removed_total": len(removed),
            "removed_still_live": still_live,
        }
        if not_200:
            P.append(f"{len(not_200)} 个在册 p 页线上非 200: {not_200[:5]}")
        if still_live:
            P.append(f"{len(still_live)} 个已下架 p 页仍可访问: {still_live[:5]}")
        if netfail or (done < len(pages)):
            say(f"   ⚠ 网络不稳：{len(netfail)} 个请求失败、{len(pages) - done} 个超出预算未完成（不计为问题）")

    # ---------- 输出 ----------
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    else:
        c = report["checks"]
        print("=" * 74)
        print(f"本地 HEAD   : {c['repo']['head']}  远端引用: {c['repo']['remote_main']}  真实远端: {c['repo'].get('remote_true') or '未知'}")
        print(f"文件数      : 远端 {c['repo']['files_remote']} / 本地已跟踪 {c['repo']['files_tracked']}")
        print(f"本地↔远端   : {'一致' if c['repo']['clean'] else '有差异'}"
              f"（仅 CRLF 差异 {len(c['repo']['crlf_only'])} 个"
              f"{'，origin/main 引用过期已跳过逐文件比对' if c['repo']['stale_ref'] else ''}）")
        for k in ("content_diff", "missing_local", "only_local_tracked", "dirty"):
            if c["repo"].get(k):
                print(f"  {k}: {c['repo'][k][:8]}")
        v = c["version"]
        print(f"版本        : 本地 {v['local_index_ver']} / 线上 {v['live_index_ver']} "
              f"| SW 本地 {v['local_sw_cache']} / 线上 {v['live_sw_cache']} | README {v['local_readme_ver']}")
        print(f"REPOS       : {c['tables']['repos']} 个（唯一 {c['tables']['repos_unique']}）")
        for name, d in c["tables"]["detail"].items():
            if name == "AUTHORS":
                print(f"  AUTHORS    keys={d['keys']:<4} dup={d['dups'] or '无'}")
                continue
            flags = []
            if d["dups"]:
                flags.append(f"重复{d['dups']}")
            if d["dead"]:
                flags.append(f"死键{d['dead'][:3]}")
            if d["case_mismatch"]:
                flags.append(f"大小写{d['case_mismatch']}")
            if d.get("missing"):
                flags.append(f"缺{d['missing'][:3]}")
            print(f"  {name:<11} keys={d['keys']:<4} {' '.join(flags) if flags else '干净'}")
        rj = c["repos_json"]
        live_n = rj["live_data_repos"] if rj["live_data_repos"] is not None else "取回失败"
        print(f"repos.json  : {rj['local_updated']} | {rj['local_count']} 条 | 线上 data.js {live_n} 个")
        print("线上 vs 本地文件:")
        for r in c["live_vs_local"]:
            print(f"  {r['file']:<14} live={r['live_len']:<7} local={r['local_len']:<7} "
                  f"逐字节={r['identical']} 归一化={r['identical_norm']}")
        if c.get("pages"):
            pg = c["pages"]
            if pg.get("skipped"):
                print("p 页        : 已跳过（默认不扫；加 --pages 抽样 / --full-pages 全量）")
            else:
                print(f"p 页        : 应查 {pg['checked']}/{pg['total']} 个，非200 {pg['not_200'] or '无'}"
                      f"，网络失败 {len(pg['network_errors'])} 个")
                print(f"              历史下架 {pg['removed_checked']}/{pg['removed_total']} 个，仍可访问 {pg['removed_still_live'] or '无'}")
        print("-" * 74)
        print("问题:", P or "无")

    return 0 if not P else 1


if __name__ == "__main__":
    sys.exit(main())
