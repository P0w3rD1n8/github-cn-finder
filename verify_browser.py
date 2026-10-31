#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GitHub 中文发现器 · 浏览器级验收（Playwright + 本机 Edge 内核）

覆盖 HTTP 级核验（verify_sync.py）查不到的行为：首屏卡片数、分页点击、分类过滤、
搜索空态、移动端视口可读性、控制台报错。

用法：
    <DSH python> verify_browser.py                # 默认测线上站点
    <DSH python> verify_browser.py --local        # 起本地 http.server 测当前工作区
    <DSH python> verify_browser.py --headed       # 显示浏览器窗口（调试用）
    <DSH python> verify_browser.py --json

依赖：pip install playwright（浏览器用本机 Edge：channel="msedge"，无需 playwright install）
产物：截图存到 _shots/（已 gitignore）
退出码：0 全绿；1 有失败项
"""
import argparse
import json
import os
import socket
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

LIVE_BASE = "https://p0w3rd1n8.github.io/github-cn-finder/"
ROOT = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(ROOT, "_shots")

results = []


def check(name, ok, detail=""):
    results.append({"name": name, "pass": bool(ok), "detail": str(detail)[:300]})
    flag = "✅" if ok else "❌"
    print(f"  {flag} {name}" + (f" — {detail}" if detail else ""), flush=True)
    return bool(ok)


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def start_server(root):
    port = free_port()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), partial(QuietHandler, directory=root))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, port


def wait_cards(page, expect, timeout=15000):
    """等到卡片数量稳定为 expect（渲染是同步的，但仍给足余量）"""
    try:
        page.wait_for_function(
            "n => document.querySelectorAll('#homeList .card').length === n", arg=expect, timeout=timeout
        )
        return True
    except Exception:
        return False


def count_cards(page):
    return page.locator("#homeList .card").count()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=None)
    ap.add_argument("--local", action="store_true", help="测本地工作区（起临时 http.server）")
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--shots", default=SHOTS)
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright

    httpd = None
    if args.local:
        httpd, port = start_server(ROOT)
        base = f"http://127.0.0.1:{port}/"
    else:
        base = args.url or LIVE_BASE
    print(f"目标: {base}", flush=True)
    os.makedirs(args.shots, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=not args.headed)
        try:
            # ---------- 桌面端 ----------
            ctx = browser.new_context(viewport={"width": 1280, "height": 900},
                                      service_workers="block")
            page = ctx.new_page()
            errors, failures = [], []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            page.on("requestfailed", lambda r: failures.append(f"{r.url} {r.failure}"))

            page.goto(base, wait_until="domcontentloaded", timeout=45000)
            # 等 repos.json 拉完并重渲染，否则随后的点击会被这次重渲染覆盖回第 1 页
            try:
                page.wait_for_load_state("networkidle", timeout=20000)
            except Exception:
                pass
            page.wait_for_timeout(600)
            ok24 = wait_cards(page, 24)
            n = count_cards(page)
            check("首屏 24 卡", ok24 and n == 24, f"实际 {n} 张")

            info = page.locator("#homeList .pg-info").first
            itext = info.inner_text() if info.count() else ""
            check("分页条「第 1/7 页 · 共 152 个」", "第 1/7 页" in itext and "152" in itext, itext)

            # 末页
            page.locator('#homeList .pg[data-pg="7"]').click()
            try:
                page.wait_for_function(
                    "() => (document.querySelector('#homeList .pg-info')||{}).textContent?.includes('第 7/7 页')",
                    timeout=8000,
                )
            except Exception:
                pass
            n7 = count_cards(page)
            info7 = page.locator("#homeList .pg-info").first.inner_text()
            check("第 7 页 8 卡", n7 == 8 and "第 7/7 页" in info7, f"{n7} 张 / {info7}")

            # 回到第 1 页 + 分类
            page.locator('#homeList .pg[data-pg="1"]').click()
            page.wait_for_timeout(300)
            page.locator('#catBar [data-cat="AI 人工智能"]').click()
            page.wait_for_timeout(500)
            nai = count_cards(page)
            info_ai = page.locator("#homeList .pg-info").first
            ai_text = info_ai.inner_text() if info_ai.count() else "（无分页条，单页显示）"
            check("AI 分类 23 个 / 1 页", nai == 23, f"{nai} 张 / {ai_text}")

            # 搜索空态（用无意义关键词，避免命中 GitHub 远程搜索结果）
            page.locator('#catBar [data-cat="全部"]').click()
            page.wait_for_timeout(300)
            page.fill("#searchInput", "zzqqxx不存在的项目")
            page.wait_for_timeout(2000)
            n_empty = count_cards(page)
            body_text = page.locator("body").inner_text()
            has_empty_tip = ("没有找到" in body_text) or ("没有匹配项" in body_text)
            check("搜索无结果 = 0 卡 + 空态文案", n_empty == 0 and has_empty_tip,
                  f"{n_empty} 张，空态文案={'有' if has_empty_tip else '无'}")

            # 搜索命中精选库
            page.fill("#searchInput", "ollama")
            page.wait_for_timeout(2000)
            names = page.evaluate(
                "() => [...document.querySelectorAll('#homeList .card')].map(c => c.dataset.n)"
            )
            check("搜索「ollama」命中精选 ollama/ollama", "ollama/ollama" in names,
                  f"{len(names)} 张: {names[:4]}")

            page.fill("#searchInput", "")
            page.wait_for_timeout(500)
            page.screenshot(path=os.path.join(args.shots, "desktop-1280.png"), full_page=False)

            # 静态项目页
            p_resp = page.goto(base + "p/ollama-ollama.html", wait_until="domcontentloaded", timeout=45000)
            h1 = page.locator("h1").first.inner_text() if page.locator("h1").count() else ""
            check("静态页 p/ollama-ollama.html", p_resp is not None and p_resp.status == 200 and len(h1) > 0,
                  f"HTTP {p_resp.status if p_resp else '?'} / h1={h1[:24]}")

            # 前端会主动取消上一轮搜索请求（cancelPendingSearch），aborted 属正常
            real_failures = [
                f for f in failures
                if "ERR_ABORTED" not in f and "api.github.com/search" not in f
            ]
            check("无控制台报错", len(errors) == 0, " | ".join(errors[:3]))
            check("无请求失败", len(real_failures) == 0,
                  " | ".join(real_failures[:3]) or f"（已忽略 {len(failures) - len(real_failures)} 个主动取消的搜索请求）")
            ctx.close()

            # ---------- 移动端 375×812 ----------
            m = browser.new_context(viewport={"width": 375, "height": 812},
                                    is_mobile=True, has_touch=True, device_scale_factor=2,
                                    service_workers="block")
            mp = m.new_page()
            mob_errors = []
            mp.on("pageerror", lambda e: mob_errors.append(str(e)))
            mp.goto(base, wait_until="domcontentloaded", timeout=45000)
            wait_cards(mp, 24)
            overflow = mp.evaluate(
                "() => ({ sw: document.documentElement.scrollWidth, iw: window.innerWidth })"
            )
            cards = count_cards(mp)
            text_len = len(mp.locator("body").inner_text())
            check("手机 375px 首屏 24 卡", cards == 24, f"{cards} 张")
            check("手机端无横向溢出", overflow["sw"] <= overflow["iw"] + 2,
                  f"scrollWidth={overflow['sw']} innerWidth={overflow['iw']}")
            check("手机端不白屏", text_len > 300, f"正文字数 {text_len}")
            check("手机端无 JS 报错", len(mob_errors) == 0, " | ".join(mob_errors[:3]))
            mp.screenshot(path=os.path.join(args.shots, "mobile-375.png"), full_page=False)
            m.close()
        finally:
            browser.close()
            if httpd:
                httpd.shutdown()

    passed = sum(1 for r in results if r["pass"])
    total = len(results)
    print("\n" + "=" * 60)
    print(f"结果: {passed}/{total} 通过")
    if args.json:
        print(json.dumps({"target": base, "passed": passed, "total": total, "results": results},
                         ensure_ascii=False, indent=2))
    else:
        for r in results:
            if not r["pass"]:
                print(f"  ❌ {r['name']}: {r['detail']}")
        print(f"截图: {args.shots}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
