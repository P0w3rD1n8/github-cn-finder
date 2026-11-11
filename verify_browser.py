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


def load_expectations(root):
    """从 data.js 算出期望值，避免每次加项目都要改脚本里的写死数字"""
    import math
    import re

    src = open(os.path.join(root, "data.js"), encoding="utf-8").read()
    body = re.search(r"const REPOS = \[(.*?)\n\];", src, re.S).group(1)
    cats = re.findall(r'c:"([^"]+)"', body)
    total = len(cats)
    ai = sum(1 for c in cats if c == "AI 人工智能")
    return {
        "total": total,
        "pages": max(1, math.ceil(total / 24)),
        "last_cards": total - (max(1, math.ceil(total / 24)) - 1) * 24,
        "ai": ai,
        "ai_pages": max(1, math.ceil(ai / 24)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=None)
    ap.add_argument("--local", action="store_true", help="测本地工作区（起临时 http.server）")
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--shots", default=SHOTS)
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright

    exp = load_expectations(ROOT)
    print(f"期望值（来自 data.js）: 共 {exp['total']} 个 / {exp['pages']} 页 / 末页 {exp['last_cards']} 卡 / "
          f"AI {exp['ai']} 个（{exp['ai_pages']} 页）", flush=True)

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
            page.on("console", lambda m: errors.append(
                f"{m.text} @ {(m.location or {}).get('url', '')}") if m.type == "error" else None)
            page.on("requestfailed", lambda r: failures.append(f"{r.url} {r.failure}"))

            page.goto(base, wait_until="domcontentloaded", timeout=45000)
            # 等 repos.json 拉完并重渲染，否则随后的点击会被这次重渲染覆盖回第 1 页
            try:
                page.wait_for_load_state("networkidle", timeout=20000)
            except Exception:
                pass
            page.wait_for_timeout(600)
            ok24 = wait_cards(page, min(24, exp["total"]))
            n = count_cards(page)
            check(f"首屏 {min(24, exp['total'])} 卡", n == min(24, exp["total"]), f"实际 {n} 张")

            info = page.locator("#homeList .pg-info").first
            itext = info.inner_text() if info.count() else ""
            check(f"分页条「第 1/{exp['pages']} 页 · 共 {exp['total']} 个」",
                  f"第 1/{exp['pages']} 页" in itext and str(exp["total"]) in itext, itext)

            # 末页
            page.locator(f'#homeList .pg[data-pg="{exp["pages"]}"]').click()
            try:
                page.wait_for_function(
                    "n => (document.querySelector('#homeList .pg-info')||{}).textContent?.includes(n)",
                    arg=f"第 {exp['pages']}/{exp['pages']} 页",
                    timeout=8000,
                )
            except Exception:
                pass
            n7 = count_cards(page)
            info7 = page.locator("#homeList .pg-info").first.inner_text()
            check(f"第 {exp['pages']} 页 {exp['last_cards']} 卡",
                  n7 == exp["last_cards"] and f"第 {exp['pages']}/{exp['pages']} 页" in info7,
                  f"{n7} 张 / {info7}")

            # 回到第 1 页 + 分类
            page.locator('#homeList .pg[data-pg="1"]').click()
            page.wait_for_timeout(300)
            page.locator('#catBar [data-cat="AI 人工智能"]').click()
            page.wait_for_timeout(500)
            nai = count_cards(page)
            info_ai = page.locator("#homeList .pg-info").first
            has_pager = info_ai.count() > 0
            ai_text = info_ai.inner_text() if has_pager else "（无分页条）"
            if exp["ai"] <= 24:
                ai_ok = nai == exp["ai"] and not has_pager
            else:
                ai_ok = nai == 24 and f"1/{exp['ai_pages']} 页" in ai_text
            check(f"AI 分类 {exp['ai']} 个 / {exp['ai_pages']} 页", ai_ok, f"{nai} 张 / {ai_text}")

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

            # ---------- v1.25.0 新功能 ----------
            # 1) 筛选写入 URL + 刷新保持
            page.locator('#catBar [data-cat="AI 人工智能"]').click()
            page.wait_for_timeout(500)
            u1 = page.url
            check("筛选写入 URL", "cat=" in u1, u1.split("?")[-1][:70])
            page.reload(wait_until="domcontentloaded")
            page.wait_for_timeout(900)
            active_cat = page.locator("#catBar .cat.active").first.inner_text()
            n_after = count_cards(page)
            check("刷新后保持筛选", active_cat == "AI 人工智能" and n_after == min(24, exp["ai"]),
                  f"{active_cat} / {n_after} 张")

            # 2) 活跃度角标：先验判定逻辑，再验真实卡片
            page.locator('#catBar [data-cat="全部"]').click()
            page.wait_for_timeout(500)
            acts = page.evaluate("""() => [
                activityOf({n:'fresh', pa:'2026-11-01'}),
                activityOf({n:'half', pa:'2026-04-01'}),
                activityOf({n:'dead', pa:'2025-01-01'}),
                activityOf({n:'arch', ar:true})
            ]""")
            ok_act = (acts[0] is None
                      and acts[1] and acts[1]["text"] == "半年未更"
                      and acts[2] and acts[2]["text"] == "停更"
                      and acts[3] and acts[3]["text"] == "已归档")
            check("活跃度判定逻辑", ok_act, str(acts)[:120])

            page.fill("#searchInput", "stable-diffusion")
            page.wait_for_timeout(1800)
            badge_txt = page.evaluate(
                "() => [...document.querySelectorAll('#homeList .tag.act-warn,#homeList .tag.act-dead')].map(e=>e.textContent)"
            )
            check("停更项目卡片显示角标", len(badge_txt) > 0, f"示例 {badge_txt[:3]}")
            page.fill("#searchInput", "")
            page.wait_for_timeout(700)

            # 3) 详情页相似项目
            page.locator("#homeList .expand-hint").first.click()
            page.wait_for_timeout(500)
            sim = page.locator(".sim-item").count()
            check("详情页相似项目", sim >= 2, f"{sim} 个")

            # 静态项目页
            p_resp = page.goto(base + "p/ollama-ollama.html", wait_until="domcontentloaded", timeout=45000)
            h1 = page.locator("h1").first.inner_text() if page.locator("h1").count() else ""
            check("静态页 p/ollama-ollama.html", p_resp is not None and p_resp.status == 200 and len(h1) > 0,
                  f"HTTP {p_resp.status if p_resp else '?'} / h1={h1[:24]}")

            # ---------- v1.26.0 专题合辑 / 周刊 / RSS ----------
            c_resp = page.goto(base + "c/", wait_until="domcontentloaded", timeout=45000)
            c_cards = page.locator(".coll-card").count()
            check("专题合辑索引", c_resp is not None and c_resp.status == 200 and c_cards >= 3,
                  f"HTTP {c_resp.status if c_resp else '?'} / {c_cards} 个合辑")

            c1 = page.goto(base + "c/zhuangji.html", wait_until="domcontentloaded", timeout=45000)
            c_items = page.locator(".c-item").count()
            check("合辑内页项目数", c1 is not None and c1.status == 200 and c_items >= 5,
                  f"HTTP {c1.status if c1 else '?'} / {c_items} 个")

            w_resp = page.goto(base + "weekly/", wait_until="domcontentloaded", timeout=45000)
            w_issues = page.locator(".issue").count()
            check("每周精选索引", w_resp is not None and w_resp.status == 200 and w_issues >= 1,
                  f"HTTP {w_resp.status if w_resp else '?'} / {w_issues} 期")

            r_resp = page.goto(base + "feed.xml", wait_until="domcontentloaded", timeout=45000)
            r_body = page.content()
            check("RSS feed.xml", r_resp is not None and r_resp.status == 200 and "<rss" in r_body,
                  f"HTTP {r_resp.status if r_resp else '?'} / {len(r_body)} 字节")

            # ---------- v1.27.0 对比模式 + 项目 OG 图 ----------
            page.goto(base, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(1200)
            page.evaluate("() => { try{ localStorage.removeItem('ghcn_cmp'); }catch(e){} }")
            page.reload(wait_until="domcontentloaded")
            page.wait_for_timeout(1200)
            page.locator("#homeList .cmp-btn").nth(0).click()
            page.locator("#homeList .cmp-btn").nth(1).click()
            page.wait_for_timeout(400)
            tray_on = page.locator("#cmpTray.show").count()
            page.locator("#cmpGo").click()
            page.wait_for_timeout(500)
            rows = page.locator("#cmpWrap table.cmp tr").count()
            cols = page.locator("#cmpWrap table.cmp th").count()
            check("对比模式（2 个项目）", tray_on == 1 and rows >= 8 and cols >= 3,
                  f"tray={tray_on} 行={rows} 列={cols}")
            page.locator("#closeCmp").click()

            og = page.request.get(base + "og/ollama-ollama.png")
            og2 = page.request.get(base + "p/ollama-ollama.html")
            has_meta = 'og/ollama-ollama.png' in og2.text()
            check("项目分享封面 OG 图", og.status == 200 and "image" in (og.headers.get("content-type") or "")
                  and has_meta, f"HTTP {og.status} / meta={has_meta}")

            # ---------- v1.28.0 更新记录 / PWA 安装体验 ----------
            t_resp = page.goto(base + "timeline/", wait_until="domcontentloaded", timeout=45000)
            tl_days = page.locator(".tl-day").count()
            check("更新记录时间线", t_resp is not None and t_resp.status == 200 and tl_days >= 1,
                  f"HTTP {t_resp.status if t_resp else '?'} / {tl_days} 个日期")

            page.goto(base + "?tab=rank", wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(900)
            rank_shown = page.locator("#page-rank.show").count()
            check("快捷方式 ?tab=rank 直达榜单", rank_shown == 1, f"page-rank.show={rank_shown}")

            man = page.request.get(base + "manifest.json")
            man_json = man.json() if man.status == 200 else {}
            check("PWA 快捷方式与安装预览",
                  len(man_json.get("shortcuts", [])) >= 3 and len(man_json.get("screenshots", [])) >= 1,
                  f"shortcuts={len(man_json.get('shortcuts', []))} screenshots={len(man_json.get('screenshots', []))}")

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
