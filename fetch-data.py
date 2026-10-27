#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub 中文发现器 · 精选库真实数据采集脚本
从 index.html 解析精选库仓库清单 → 调 GitHub REST API 抓取真实字段
→ 输出 repos.json（前端 fetch 使用；手填伪指标 RATING/FAV_BASE/FORKS/ISSUES 由本文件取代）
每次抓取会带上 ps（上一次快照的 star，来自 git 上一版或线上最新版），前端据此计算
"较上次快照的星标增量"做今日星标增速榜（无需 24h 历史数组，口径由榜单标题注明）。
用法：python fetch-data.py
环境变量：GH_TOKEN（推荐，用户 PAT，额度 5000/h）或 GITHUB_TOKEN（Actions 自动注入）
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

INDEX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "repos.json")
API = "https://api.github.com"
RAW_PREV = "https://raw.githubusercontent.com/P0w3rD1n8/github-cn-finder/main/repos.json"

TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""


def load_prev_repos():
    """取上一版快照的 star 值：优先当前 checkout 的 git 上一版（Actions 里 HEAD=上次提交），
    失败则拉线上最新版；都拿不到返回 None（首轮：ps 为空，前端自动兜底）。"""
    try:
        out = subprocess.check_output(
            ["git", "show", "HEAD:repos.json"], stderr=subprocess.DEVNULL)
        return json.loads(out.decode("utf-8")).get("repos", {})
    except Exception:
        pass
    try:
        req = urllib.request.Request(RAW_PREV, headers={"User-Agent": "gh-cn-finder-updater"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8")).get("repos", {})
    except Exception:
        return None


def parse_repos(html):
    """从 index.html 的 REPOS 数组提取全部 {n:'owner/repo'}"""
    m = re.search(r"const REPOS = \[(.*?)\n\];", html, re.S)
    if not m:
        sys.exit("找不到 REPOS 数组")
    return re.findall(r'\{n:"([^"]+)"', m.group(1))


def api_get(path):
    url = API + path
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "gh-cn-finder-updater",
    })
    if TOKEN:
        req.add_header("Authorization", "Bearer " + TOKEN)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_repo(full_name, retries=3):
    """抓单个仓库真实字段，失败返回 None"""
    for attempt in range(retries):
        try:
            d = api_get("/repos/" + urllib.parse.quote(full_name, safe="/"))
            return {
                "s": d.get("stargazers_count"),
                "fk": d.get("forks_count"),
                "iu": d.get("open_issues_count"),
                "pa": (d.get("pushed_at") or "")[:10],
                "lg": d.get("language") or "",
            }
        except Exception as e:
            code = getattr(e, "code", None)
            if code == 403:  # 限流：带 Retry-After 等待
                wait = int(getattr(e, "headers", {}).get("Retry-After", "60") or 60)
                print(f"  限流，等待 {wait}s…")
                time.sleep(wait)
            elif code == 404:
                print(f"  404：{full_name} 不存在，跳过")
                return None
            elif attempt < retries - 1:
                time.sleep(2 + attempt * 2)
            else:
                print(f"  失败：{full_name} ({e})")
                return None
    return None


def main():
    with open(INDEX, encoding="utf-8") as f:
        html = f.read()
    names = parse_repos(html)
    print(f"共 {len(names)} 个仓库，开始抓取（token={'有' if TOKEN else '无'}，8 并发）…")

    prev = load_prev_repos()
    print(f"上一版快照：{'已取得（%d 个仓库）' % len(prev) if prev else '无（首轮，ps 留空）'}")

    repos = {}
    ok = fail = 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(fetch_repo, n): n for n in names}
        done = 0
        for fut in as_completed(futures):
            n = futures[fut]
            r = fut.result()
            if r:
                repos[n] = r
                ok += 1
            else:
                fail += 1
            done += 1
            if done % 25 == 0:
                print(f"  进度 {done}/{len(names)}（成功 {ok}，失败 {fail}）")

    # 成功率门槛：失败太多就放弃写入，避免空文件/劣质数据污染线上（Review 工程项）
    if ok < len(names) * 0.9:
        sys.exit(f"❌ 成功率过低（{ok}/{len(names)}），放弃写入，保留线上上一版数据")

    # ps：上一次快照的 star（前端据此算较上次快照的增量做增速榜）
    ps_hit = 0
    for n, r in repos.items():
        if prev and n in prev and isinstance(prev[n].get("s"), (int, float)):
            r["ps"] = prev[n]["s"]
            ps_hit += 1
        else:
            r["ps"] = None

    data = {
        "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "repos": repos,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print(f"✅ 已生成 {OUT}：{ok} 成功 / {fail} 失败 / 共 {len(names)}，ps 命中 {ps_hit}")


if __name__ == "__main__":
    main()
