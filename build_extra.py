#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_extra.py — 专题合辑 / 每周精选 / RSS 生成器（v1.25.0）

读取：collections.json（人工策展）、weekly.json（每周 star 快照）、repos.json（实时数据）
输出：c/index.html、c/<slug>.html、weekly/index.html、weekly/<date>.html、feed.xml，
      并重写 sitemap.xml（把附加页也纳入）
用法：python build_extra.py
纯标准库；幂等（内容不变时输出不变）。
"""
import datetime
import html as html_mod
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_pages as bp  # noqa: E402  复用 PAGE_CSS / esc / load_data / BASE_URL

ROOT = os.path.dirname(os.path.abspath(__file__))
COL_FILE = os.path.join(ROOT, "collections.json")
WEEKLY_FILE = os.path.join(ROOT, "weekly.json")
REPOS_FILE = os.path.join(ROOT, "repos.json")
C_DIR = os.path.join(ROOT, "c")
W_DIR = os.path.join(ROOT, "weekly")
FEED = os.path.join(ROOT, "feed.xml")

SITE = "GitHub 中文发现器"
BASE = bp.BASE_URL

EXTRA_CSS = """
.cards{display:grid;grid-template-columns:1fr;gap:10px;margin:18px 0}
.c-item{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:12px 14px}
.c-item .h{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}
.c-item .zh{font-size:15px;font-weight:600;color:var(--text)}
.c-item .repo{font-size:12px;color:var(--text2)}
.c-item .st{margin-left:auto;color:var(--star);font-size:12px}
.c-item .d{font-size:13px;color:var(--text2);margin-top:6px;line-height:1.6}
.c-item a{color:inherit;text-decoration:none}
.c-item:hover{border-color:var(--accent)}
.intro{background:var(--card);border:1px solid var(--border);border-left:3px solid var(--accent);border-radius:8px;padding:12px 14px;font-size:13.5px;line-height:1.7;margin:14px 0}
.note{font-size:12px;color:var(--text2);margin-top:10px}
.coll-grid{display:grid;grid-template-columns:1fr;gap:12px;margin:18px 0}
.coll-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px 16px;text-decoration:none;color:var(--text)}
.coll-card:hover{border-color:var(--accent)}
.coll-card h2{font-size:16px;margin:0 0 4px}
.coll-card p{font-size:12.5px;color:var(--text2);margin:0;line-height:1.6}
.issue{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:12px 14px;margin:10px 0}
.issue a{color:var(--accent);text-decoration:none}
.issue .date{color:var(--text2);font-size:12px;margin-left:8px}
ol.rank{padding-left:22px;font-size:13.5px;line-height:1.9}
ol.rank .st{color:var(--star)}
.delta{color:#3fb950;font-weight:600}
nav.sub{margin:18px 0 0;font-size:13px}
nav.sub a{color:var(--accent);text-decoration:none;margin-right:14px}
"""


def esc(s):
    return html_mod.escape(str(s), quote=True)


def page(title, desc, body, canonical):
    return (
        '<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f"<title>{esc(title)}</title>\n"
        f'<meta name="description" content="{esc(desc)}">\n'
        f'<link rel="canonical" href="{esc(canonical)}">\n'
        f'<link rel="icon" href="{BASE}/icon.svg" type="image/svg+xml">\n'
        '<meta name="theme-color" content="#0d1117">\n'
        f"<style>\n{bp.PAGE_CSS}{EXTRA_CSS}\n</style>\n"
        "</head>\n<body>\n"
        '<header class="site-head"><span class="logo">🧭 ' + SITE + '</span>'
        f'<a class="back" href="{BASE}/">← 返回首页</a></header>\n'
        '<main class="container">\n' + body + "\n</main>\n</body>\n</html>\n"
    )


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_collections(data):
    cols = load_json(COL_FILE, {"collections": []})["collections"]
    by_name = {r["n"]: r for r in data["repos"]}
    os.makedirs(C_DIR, exist_ok=True)
    made = []
    cards = []
    for col in cols:
        missing = [n for n in col["items"] if n not in by_name]
        if missing:
            sys.exit(f"❌ 合辑 {col['slug']} 引用了不存在的项目：{missing}")
        items = []
        for n in col["items"]:
            r = by_name[n]
            zh = data["repo_zh"].get(n) or n.split("/")[1]
            desc = data["cn_desc"].get(n) or r.get("d", "")
            owner, repo = n.split("/")
            items.append(
                '<div class="c-item"><div class="h">'
                f'<a class="zh" href="{BASE}/p/{esc(owner)}-{esc(repo)}.html">{esc(zh)}</a>'
                f'<span class="repo">{esc(n)}</span>'
                f'<span class="st">⭐ {int(r.get("s") or 0):,}</span></div>'
                f'<div class="d">{esc(desc)}</div></div>'
            )
        body = (
            f"<h1>{esc(col['title'])}</h1>\n"
            f'<div class="intro"><b>{esc(col.get("subtitle", ""))}</b><br>{esc(col.get("desc", ""))}'
            + (f'<div class="note">💡 {esc(col["note"])}</div>' if col.get("note") else "")
            + "</div>\n"
            f'<div class="cards">{"".join(items)}</div>\n'
            f'<nav class="sub"><a href="{BASE}/c/">← 全部合辑</a><a href="{BASE}/">回首页</a>'
            f'<a href="{BASE}/weekly/">📮 每周精选</a></nav>'
        )
        html_text = page(
            f"{col['title']} - {SITE}",
            col.get("desc", ""),
            body,
            f"{BASE}/c/{col['slug']}.html",
        )
        with open(os.path.join(C_DIR, col["slug"] + ".html"), "w", encoding="utf-8", newline="\n") as f:
            f.write(html_text)
        made.append(col["slug"])
        cards.append(
            f'<a class="coll-card" href="{BASE}/c/{esc(col["slug"])}.html">'
            f'<h2>{esc(col["title"])}</h2><p>{esc(col.get("subtitle", ""))}'
            f'（{len(col["items"])} 个）</p></a>'
        )
    index_body = (
        "<h1>📚 专题合辑</h1>\n"
        f'<div class="intro">按「使用场景」把项目串起来，比按分类翻更省事。'
        f'共 {len(cols)} 个专题，每个专题都是人工挑选。</div>\n'
        f'<div class="coll-grid">{"".join(cards)}</div>\n'
        f'<nav class="sub"><a href="{BASE}/">回首页</a><a href="{BASE}/list.html">全部项目</a></nav>'
    )
    with open(os.path.join(C_DIR, "index.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(page(f"专题合辑 - {SITE}", "按场景组织的开源项目清单", index_body, f"{BASE}/c/"))
    return made


def write_next_weekly():
    """写 weekly/next.json：首页显示「周X更新一期 · 下一期 日期」"""
    import datetime as _dt
    snaps = load_json(WEEKLY_FILE, {"snapshots": []})["snapshots"]
    today = _dt.date.today()
    if snaps:
        last = _dt.date.fromisoformat(snaps[-1]["date"])
        nxt = last + _dt.timedelta(days=7)
    else:
        nxt = today
    while nxt < today:
        nxt += _dt.timedelta(days=7)
    wd = "周" + "一二三四五六日"[nxt.weekday()]
    payload = {"last": snaps[-1]["date"] if snaps else "", "next": nxt.isoformat(),
               "weekday": wd + "更新", "label": f"{nxt.month} 月 {nxt.day} 日"}
    os.makedirs(W_DIR, exist_ok=True)
    with open(os.path.join(W_DIR, "next.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    return payload


def weekly_pages(data):
    snaps = load_json(WEEKLY_FILE, {"snapshots": []})["snapshots"]
    os.makedirs(W_DIR, exist_ok=True)
    by_name = {r["n"]: r for r in data["repos"]}
    repo_meta = load_json(REPOS_FILE, {"repos": {}}).get("repos", {})
    issues = []

    def zh_of(n):
        return data["repo_zh"].get(n) or n.split("/")[1]

    for i, snap in enumerate(snaps):
        date = snap.get("date", "")
        stars = snap.get("stars", {})
        prev = snaps[i - 1] if i > 0 else None
        parts = [f"<h1>📮 第 {i + 1} 期 · {esc(date)}</h1>"]
        new_names, gains = [], []
        if prev:
            prev_stars = prev.get("stars", {})
            new_names = sorted(set(stars) - set(prev_stars))
            for n, s in stars.items():
                p = prev_stars.get(n)
                if isinstance(p, (int, float)) and s > p:
                    gains.append((s - p, n, s))
            gains.sort(reverse=True)
        if prev:
            new_txt = (f"本周新增 {len(new_names)} 个项目" if new_names else "本周没有新增项目")
            parts.append('<div class="intro"><b>本期看点</b><br>'
                         f'{new_txt}，涨星最快的是 '
                         f'{esc(zh_of(gains[0][1]))}（+{gains[0][0]:,}）。</div>' if gains
                         else f'<div class="intro">本周没有明显涨星的项目（{new_txt}）。</div>')
        else:
            parts.append('<div class="intro"><b>首期基线</b><br>'
                         '这是第一份周快照，先记录全部项目的星标作为基准。'
                         '从下一期（约 7 天后）开始统计「本周新增」和「周涨星榜」。</div>')

        if gains:
            rows = "".join(
                f'<li><a href="{BASE}/p/{esc(n.split("/")[0])}-{esc(n.split("/")[1])}.html">{esc(zh_of(n))}</a>'
                f' <span class="delta">+{d:,}</span> <span class="st">（{s:,}）</span></li>'
                for d, n, s in gains[:10]
            )
            parts.append("<h2>🚀 本周涨星 Top 10</h2>\n<ol class=\"rank\">" + rows + "</ol>")

        if new_names:
            rows = "".join(
                f'<li><a href="{BASE}/p/{esc(n.split("/")[0])}-{esc(n.split("/")[1])}.html">{esc(zh_of(n))}</a></li>'
                for n in new_names[:10]
            )
            parts.append(f"<h2>🆕 本周新增（{len(new_names)} 个）</h2>\n<ol class=\"rank\">" + rows + "</ol>")

        top = sorted(stars.items(), key=lambda kv: -kv[1])[:10]
        rows = "".join(
            f'<li><a href="{BASE}/p/{esc(n.split("/")[0])}-{esc(n.split("/")[1])}.html">{esc(zh_of(n))}</a>'
            f' <span class="st">⭐ {s:,}</span></li>' for n, s in top
        )
        parts.append("<h2>🔥 当前总榜 Top 10</h2>\n<ol class=\"rank\">" + rows + "</ol>")

        stale = [(n, m.get("pa", ""), m.get("ar")) for n, m in repo_meta.items() if m.get("ar")]
        if stale:
            names = "、".join(esc(zh_of(n)) for n, _, _ in stale[:8])
            parts.append(f'<h2>⚠️ 已归档提醒</h2><p class="note">{names} 已被作者归档，不再更新。</p>')

        parts.append(f'<p class="note">数据口径：每周抓一次全库星标（UTC 日期）。共 {len(stars)} 个项目。</p>')
        parts.append(f'<nav class="sub"><a href="{BASE}/weekly/">← 全部期数</a><a href="{BASE}/">回首页</a></nav>')
        body = "\n".join(parts)
        fname = f"{date}.html"
        with open(os.path.join(W_DIR, fname), "w", encoding="utf-8", newline="\n") as f:
            f.write(page(f"每周精选 · {date} - {SITE}", "GitHub 中文发现器每周精选：本周新增、涨星榜、总榜。", body,
                         f"{BASE}/weekly/{date}"))
        issues.append({"date": date, "n": i + 1, "file": fname, "new": len(new_names), "first": i == 0,
                       "top_gain": gains[0] if gains else None})

    cards = "".join(
        f'<div class="issue"><a href="{BASE}/weekly/{esc(it["file"])}">第 {it["n"]} 期</a>'
        f'<span class="date">{esc(it["date"])}'
        + (f' · 新增 {it["new"]} 个' if it["new"] else "")
        + "</span></div>"
        for it in reversed(issues)
    )
    index_body = (
        "<h1>📮 每周精选</h1>\n"
        '<div class="intro">每周更新一期：本周新增项目、涨星最快 Top 10、当前总榜、归档提醒。'
        '也可以 <a href="' + BASE + '/feed.xml">用 RSS 订阅</a>。</div>\n'
        + (cards or '<p class="note">还没有周快照，CI 每周会自动写入。</p>')
        + f'<nav class="sub"><a href="{BASE}/">回首页</a><a href="{BASE}/c/">📚 专题合辑</a></nav>'
    )
    with open(os.path.join(W_DIR, "index.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(page(f"每周精选 - {SITE}", "GitHub 中文发现器每周精选", index_body, f"{BASE}/weekly/"))
    return issues


def build_feed(issues):
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    items = []
    for it in reversed(issues):
        pub = datetime.datetime.strptime(it["date"], "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
        desc = ("首期基线：记录全部项目的星标基准" if it.get("first") else f"第 {it['n']} 期：新增 {it['new']} 个项目")
        if it["top_gain"]:
            desc += f"，{it['top_gain'][1]} 涨星 +{it['top_gain'][0]:,}"
        items.append(
            "    <item>\n"
            f"      <title>每周精选 第 {it['n']} 期（{it['date']}）</title>\n"
            f"      <link>{BASE}/weekly/{it['file']}</link>\n"
            f"      <guid isPermaLink=\"false\">weekly-{it['date']}</guid>\n"
            f"      <pubDate>{pub.strftime('%a, %d %b %Y 00:00:00 +0000')}</pubDate>\n"
            f"      <description>{esc(desc)}</description>\n"
            "    </item>"
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<?xml-stylesheet type="text/xsl" href="feed.xsl"?>\n'
        '<rss version="2.0"><channel>\n'
        f"  <title>{SITE} · 每周精选</title>\n"
        f"  <link>{BASE}/weekly/</link>\n"
        "  <description>每周一期：新增项目、涨星榜、总榜与归档提醒</description>\n"
        "  <language>zh-cn</language>\n"
        f"  <lastBuildDate>{now}</lastBuildDate>\n"
        + "\n".join(items)
        + "\n</channel></rss>\n"
    )
    with open(FEED, "w", encoding="utf-8", newline="\n") as f:
        f.write(xml)


def build_subscribe():
    """订阅说明页：用户点「订阅更新」不该直接看到 XML"""
    os.makedirs(os.path.join(ROOT, "subscribe"), exist_ok=True)
    feed_url = BASE + "/feed.xml"
    body = (
        "<h1>📡 订阅更新</h1>\n"
        '<div class="intro">这个站每周更新一次「本周新增 + 周涨星榜」。'
        "用 RSS 订阅后，不用天天来刷——有新内容时阅读器会自己收到。<br>"
        "<b>不用注册、不留手机号、不装 App 也行。</b></div>\n"
        '<div class="cards">'
        '<div class="c-item"><div class="h"><span class="zh">订阅地址</span></div>'
        f'<div class="d" style="word-break:break-all">{esc(feed_url)}</div>'
        '<div class="d" style="margin-top:8px">把上面这个链接粘到任意阅读器里就行。</div></div>'
        "</div>\n"
        '<h2 id="install">📲 装到桌面（比 RSS 简单）</h2>\n'
        '<div class="cards">'
        '<div class="c-item"><div class="h"><span class="zh">安卓（Edge / Chrome）</span></div>'
        '<div class="d">点右上角「⋮」菜单 → 选「安装应用」或「添加到主屏幕」→ 确认。<br>'
        "之后桌面会多一个图标，点开就是完整版，和 App 一样。</div></div>"
        '<div class="c-item"><div class="h"><span class="zh">iPhone / iPad（Safari）</span></div>'
        '<div class="d">点底部「分享」按钮（方框带向上箭头）→ 往下滑选「添加到主屏幕」→ 右上角「添加」。<br>'
        "注意要用 Safari 打开；在微信里点开不会出现这个选项。</div></div>"
        '<div class="c-item"><div class="h"><span class="zh">电脑（Edge / Chrome）</span></div>'
        '<div class="d">地址栏右侧有个「安装」小图标，点一下就是独立窗口。</div></div>'
        "</div>\n"
        "<h2>RSS 怎么用（三步）</h2>\n"
        '<div class="cards">'
        '<div class="c-item"><div class="h"><span class="zh">1. 装一个阅读器</span></div>'
        '<div class="d">安卓：Feeder、Fluent Reader<br>'
        "iOS：Reeder、NetNewsWire<br>"
        "电脑：Inoreader、Feedly（网页版，免安装）</div></div>"
        '<div class="c-item"><div class="h"><span class="zh">2. 粘贴订阅地址</span></div>'
        '<div class="d">在阅读器里选「添加订阅源」，把上面那个链接粘进去。</div></div>'
        '<div class="c-item"><div class="h"><span class="zh">3. 等更新</span></div>'
        '<div class="d">之后每周出一期，阅读器里会多一条，点开就是完整内容。</div></div>'
        "</div>\n"
        '<p class="note">💡 如果不想折腾阅读器：直接来站里看 '
        f'<a href="{BASE}/weekly/">📮 每周精选</a> 也一样，内容完全一样。</p>\n'
        f'<nav class="sub" style="margin-top:24px"><a href="{BASE}/">回首页</a>'
        f'<a href="{BASE}/weekly/">📮 每周精选</a><a href="{BASE}/timeline/">🕒 更新记录</a></nav>'
    )
    html_text = page("订阅更新 - " + SITE, "用 RSS 订阅 GitHub 中文发现器的每周更新", body,
                     BASE + "/subscribe/")
    with open(os.path.join(ROOT, "subscribe", "index.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(html_text)


def main():
    data = bp.load_data()
    slugs = build_collections(data)
    build_subscribe()
    nxt = write_next_weekly()
    issues = weekly_pages(data)
    build_feed(issues)

    extra = [("c/", "weekly", "0.7"), ("timeline/", "weekly", "0.7"), ("subscribe/", "monthly", "0.6")]
    # 年度精选（人工策展页）
    try:
        _ann = json.load(open(os.path.join(ROOT, "annual.json"), encoding="utf-8"))
        extra.append(("annual/%s.html" % _ann["year"], "monthly", "0.9"))
    except Exception:
        pass
    extra += [(f"c/{s}.html", "monthly", "0.7") for s in slugs]
    extra += [("weekly/", "weekly", "0.7")]
    extra += [(f"weekly/{it['file']}", "yearly", "0.5") for it in issues]
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8", newline="\n") as f:
        f.write(bp.build_sitemap(data["repos"], data, extra))

    print(f"✅ 合辑 {len(slugs)} 个 / 周刊 {len(issues)} 期 / RSS 1 个 / 订阅页 1 个 / sitemap 含附加页 {len(extra)} 条")


if __name__ == "__main__":
    main()
