#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub 中文发现器 · 精选库真实数据采集脚本
从 index.html 解析精选库仓库清单 → 调 GitHub REST API 抓取真实字段
→ 输出 repos.json（前端 fetch 使用；手填伪指标 RATING/FAV_BASE/FORKS/ISSUES 由本文件取代）
用法：python fetch-data.py
环境变量：GH_TOKEN（推荐，用户 PAT，额度 5000/h）或 GITHUB_TOKEN（Actions 自动注入）
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

INDEX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "repos.json")
API = "https://api.github.com"

TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""


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
    print(f"共 {len(names)} 个仓库，开始抓取（token={'有' if TOKEN else '无'}）…")

    repos = {}
    ok = fail = 0
    for i, n in enumerate(names, 1):
        r = fetch_repo(n)
        if r:
            repos[n] = r
            ok += 1
        else:
            fail += 1
        if i % 25 == 0:
            print(f"  进度 {i}/{len(names)}（成功 {ok}，失败 {fail}）")
        time.sleep(0.15)  # 轻微限速，避免打爆限流

    data = {
        "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "repos": repos,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print(f"✅ 已生成 {OUT}：{ok} 成功 / {fail} 失败 / 共 {len(names)}")


if __name__ == "__main__":
    main()
