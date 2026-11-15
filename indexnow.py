#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""indexnow.py — 把站点 URL 主动推送给 Bing / 搜狗 / Yandex 等支持的引擎

IndexNow 是开放协议，不需要账号：站点根目录放 {key}.txt，POST 到 api.indexnow.org 即可。
本站根 = https://p0w3rd1n8.github.io/github-cn-finder/

用法：
    python indexnow.py                # 推送 sitemap.xml 里全部 URL（约 175 条）
    python indexnow.py --limit 20     # 只推前 20 条（测试用）
    python indexnow.py --dry-run      # 只打印不发送
"""
import argparse
import json
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET

BASE = "https://p0w3rd1n8.github.io/github-cn-finder"
KEY = "599d85c56a314155b3c66ff8d4a3c5f9"
KEY_LOCATION = f"{BASE}/{KEY}.txt"
HOST = "p0w3rd1n8.github.io"
ENDPOINT = "https://api.indexnow.org/indexnow"
ROOT = os.path.dirname(os.path.abspath(__file__))


def sitemap_urls():
    path = os.path.join(ROOT, "sitemap.xml")
    if not os.path.exists(path):
        return []
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    tree = ET.parse(path)
    return [loc.text.strip() for loc in tree.getroot().findall(".//s:loc", ns) if loc.text]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    urls = sitemap_urls()
    if args.limit:
        urls = urls[: args.limit]
    if not urls:
        print("⚠️ sitemap.xml 里没有 URL，跳过")
        return 0

    payload = {
        "host": HOST,
        "key": KEY,
        "keyLocation": KEY_LOCATION,
        "urlList": urls,
    }
    if args.dry_run:
        print(f"[dry-run] 将推送 {len(urls)} 条到 {ENDPOINT}")
        print("keyLocation:", KEY_LOCATION)
        print("示例:", urls[:3])
        return 0

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT, data=data, headers={"Content-Type": "application/json; charset=utf-8"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"✅ IndexNow：已推送 {len(urls)} 条，HTTP {r.status}（200/202 均为受理）")
            return 0
    except Exception as e:
        body = ""
        if hasattr(e, "read"):
            try:
                body = e.read().decode("utf-8", "replace")[:200]
            except Exception:
                pass
        print(f"⚠️ IndexNow 推送失败：{type(e).__name__} {body}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
