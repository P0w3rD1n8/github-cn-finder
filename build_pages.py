#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_pages.py — GitHub 中文发现器静态项目页生成器（v1.19）

从 data.js 提取全部精选数据，生成：
  p/<owner>-<repo>.html    每个项目的独立静态页（SEO 长尾 / 单项目分享落地页）
  list.html                全量项目清单（站点根，供访客索引与爬虫）
  sitemap.xml              站点地图（首页 + 全部项目页 + 清单页）

纯 Python 标准库，无第三方依赖；幂等（内容不变时输出不变，git diff 干净）。
用法：
  python build_pages.py
"""

import json
import os
import re
import sys
import datetime
import html as html_mod

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_JS = os.path.join(ROOT, "data.js")
OUT_DIR = os.path.join(ROOT, "p")
BASE_URL = "https://p0w3rd1n8.github.io/github-cn-finder"
OG_IMAGE = "https://cdn.jsdelivr.net/gh/P0w3rD1n8/github-cn-finder@main/og-cover.png"

PAGE_CSS = """\
:root{--bg:#0d1117;--card:#161b22;--text:#e6edf3;--text2:#8b949e;--border:#30363d;--accent:#58a6ff;--star:#f0b429}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;line-height:1.7;padding:0 0 40px}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
.site-head{background:var(--card);border-bottom:1px solid var(--border);padding:12px 16px;display:flex;align-items:center;gap:10px;position:sticky;top:0;z-index:10}
.site-head .logo{font-weight:700;font-size:15px}
.site-head .back{margin-left:auto;font-size:13px;color:var(--text2)}
.container{max-width:760px;margin:0 auto;padding:24px 16px}
h1{font-size:24px;line-height:1.4;margin-bottom:4px}
h1 .en{color:var(--text2);font-size:14px;font-weight:400}
.meta-row{color:var(--text2);font-size:13px;margin:8px 0 16px;display:flex;flex-wrap:wrap;gap:8px}
.meta-row .tag{background:var(--card);border:1px solid var(--border);border-radius:999px;padding:2px 10px}
.meta-row .star{color:var(--star)}
.desc{font-size:15px;margin:0 0 18px}
.detail{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px;font-size:13.5px;white-space:pre-wrap;margin-bottom:18px}
.detail-tip{font-size:12px;color:var(--text2);margin-top:8px;padding-top:6px;border-top:1px dashed var(--border)}
.links{display:flex;flex-wrap:wrap;gap:10px;margin:18px 0}
.btn{display:inline-block;background:var(--accent);color:#0d1117;font-weight:600;padding:10px 18px;border-radius:10px;font-size:14px}
.btn.ghost{background:var(--card);color:var(--accent);border:1px solid var(--accent)}
.foot-note{font-size:12px;color:var(--text2);border-top:1px dashed var(--border);padding-top:12px;margin-top:24px}
footer{text-align:center;font-size:12px;color:var(--text2);margin-top:32px}
.list-item{display:flex;align-items:baseline;gap:10px;padding:10px 0;border-bottom:1px dashed var(--border)}
.list-item .nm{font-weight:600;font-size:14.5px}
.list-item .ds{color:var(--text2);font-size:13px;flex:1}
.list-item .st{color:var(--star);font-size:12px;white-space:nowrap}
"""


def read_const(text, name):
    """提取 const NAME = ...; 的原始文本（'=' 之后到配平 ';'）"""
    m = re.search(r"\bconst\s+" + re.escape(name) + r"\s*=\s*", text)
    if not m:
        raise ValueError("data.js 缺少 const " + name)
    body = text[m.end():]
    depth = 0
    i = 0
    n = len(body)
    in_str = False
    esc = False
    while i < n:
        c = body[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c in "[{(":
                depth += 1
            elif c in "])}":
                depth -= 1
                if depth == 0:
                    return body[: i + 1]
        i += 1
    raise ValueError("const " + name + " 未闭合")


def quote_keys(js_text):
    """把 JS 对象字面量里的裸键名补引号、去尾随逗号（字符串字面量内的内容原样保留）"""
    parts = re.split(r'("(?:[^"\\]|\\.)*")', js_text)
    out = []
    for p in parts:
        if p.startswith('"'):
            out.append(p)
        else:
            p = re.sub(r"(?<!\w)([A-Za-z_$][\w$]*)(\s*:)", r'"\1"\2', p)
            p = re.sub(r",(\s*)([}\]])", r"\1\2", p)  # JS 允许尾随逗号，JSON 不允许
            out.append(p)
    return "".join(out)


def parse_obj(text):
    """解析 { ... } JS 对象 → dict"""
    return json.loads(quote_keys(text))


def parse_repos_array(text):
    """解析 [ {..}, {..} ] 数组 → list[dict]（逐元素配平，兼容注释/字符串内花括号）"""
    out = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == "{":
            depth = 0
            j = i
            in_str = False
            esc = False
            while j < n:
                cc = text[j]
                if in_str:
                    if esc:
                        esc = False
                    elif cc == "\\":
                        esc = True
                    elif cc == '"':
                        in_str = False
                else:
                    if cc == '"':
                        in_str = True
                    elif cc == "{":
                        depth += 1
                    elif cc == "}":
                        depth -= 1
                        if depth == 0:
                            break
                j += 1
            out.append(parse_obj(text[i : j + 1]))
            i = j + 1
        else:
            i += 1
    return out


def load_data():
    with open(DATA_JS, "r", encoding="utf-8") as f:
        text = f.read()
    repos = parse_repos_array(read_const(text, "REPOS"))
    detail = parse_obj(read_const(text, "DETAIL"))
    repo_zh = parse_obj(read_const(text, "REPO_ZH"))
    cn_desc = parse_obj(read_const(text, "CN_DESC"))
    authors = parse_obj(read_const(text, "AUTHORS"))
    gc = parse_obj(read_const(text, "GC_MIRRORS"))
    gt = parse_obj(read_const(text, "GT_MIRRORS"))
    return {
        "repos": repos,
        "detail": detail,
        "repo_zh": repo_zh,
        "cn_desc": cn_desc,
        "authors": authors,
        "gc": gc,
        "gt": gt,
    }


def esc(s):
    return html_mod.escape(str(s), quote=True)


def build_project_page(n, r, ctx):
    owner = n.split("/")[0]
    repo = n.split("/")[1]
    fname = owner + "-" + repo + ".html"
    zh = ctx["repo_zh"].get(n) or repo
    desc = ctx["cn_desc"].get(n) or r.get("d", "")
    det = ctx["detail"].get(n)
    author_bio = ctx["authors"].get(owner)
    mkey = n.lower()
    gc_url = ctx["gc"].get(mkey)
    gt_url = ctx["gt"].get(mkey)

    meta_row = []
    if r.get("c"):
        meta_row.append('<span class="tag">' + esc(r["c"]) + "</span>")
    if r.get("l"):
        meta_row.append('<span class="tag">' + esc(r["l"]) + "</span>")
    meta_row.append('<span class="star">⭐ ' + esc("{:,}".format(int(r.get("s") or 0))) + " 星标</span>")
    meta_html = " · ".join(meta_row) if meta_row else ""

    detail_html = ""
    if det:
        detail_html = '<section class="detail">' + esc(det) + "</section>"
    else:
        detail_html = '<section class="detail">暂无中文详情，可前往 GitHub 查看项目原文介绍。</section>'

    author_html = ""
    if author_bio:
        # AUTHORS 条目是结构化对象 {t: 类型(org/user), b: 简介正文}，需取 b 字段，避免把对象原样渲染成 {'t':..., 'b':...}
        bio = author_bio.get("b", "") if isinstance(author_bio, dict) else author_bio
        if bio:
            author_html = (
                '<div class="detail-tip">👤 维护者 <a href="https://github.com/'
                + esc(owner)
                + '" target="_blank" rel="noopener">'
                + esc(owner)
                + "</a>："
                + esc(bio)
                + "</div>"
            )

    mirror_html = ""
    if gc_url:
        mirror_html = (
            '<a class="btn ghost" href="'
            + esc(gc_url)
            + '" target="_blank" rel="noopener">⚡ GitCode 国内镜像</a>'
        )
    elif gt_url:
        mirror_html = (
            '<a class="btn ghost" href="'
            + esc(gt_url)
            + '" target="_blank" rel="noopener">⚡ Gitee 国内镜像</a>'
        )

    page = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__TITLE__</title>
<meta name="description" content="__DESC__">
<link rel="canonical" href="__CANONICAL__">
<meta property="og:site_name" content="GitHub 中文发现器">
<meta property="og:type" content="article">
<meta property="og:title" content="__OGT__">
<meta property="og:description" content="__DESC__">
<meta property="og:image" content="__OGIMG__">
<meta name="theme-color" content="#0d1117">
<style>
__CSS__
</style>
</head>
<body>
<header class="site-head">
  <span class="logo">🧭 GitHub 中文发现器</span>
  <a class="back" href="__HOME__">← 返回首页</a>
</header>
<main class="container">
  <h1>__ZH__ <span class="en">__N__</span></h1>
  <div class="meta-row">__META__</div>
  <p class="desc">__DESC__</p>
  __DETAIL__
  <div class="links">
    <a class="btn" href="https://github.com/__N__" target="_blank" rel="noopener">去 GitHub 查看 ↗</a>
    __MIRROR__
  </div>
  __AUTHOR__
  <div class="foot-note">💡 说明：中文介绍与星标数据由「GitHub 中文发现器」人工整理与自动采集，仅供学习参考；安装/使用请以项目官方文档为准。</div>
</main>
<footer>© GitHub 中文发现器 · <a href="__HOME__">返回全部精选</a></footer>
</body>
</html>
"""
    return (
        page.replace("__CSS__", PAGE_CSS)
        .replace("__HOME__", BASE_URL + "/")
        .replace("__ZH__", esc(zh))
        .replace("__N__", esc(n))
        .replace("__TITLE__", esc(zh) + " - GitHub 中文发现器")
        .replace("__OGT__", esc(zh) + "（" + esc(n) + "）- GitHub 中文发现器")
        .replace("__DESC__", esc(desc))
        .replace("__CANONICAL__", BASE_URL + "/p/" + esc(fname))
        .replace("__OGIMG__", OG_IMAGE)
        .replace("__META__", meta_html)
        .replace("__DETAIL__", detail_html)
        .replace("__MIRROR__", mirror_html)
        .replace("__AUTHOR__", author_html)
    ), fname


def build_list_page(repos, ctx):
    items = []
    for r in repos:
        n = r["n"]
        owner, repo = n.split("/")
        fname = owner + "-" + repo + ".html"
        zh = ctx["repo_zh"].get(n) or repo
        desc = ctx["cn_desc"].get(n) or r.get("d", "")
        items.append(
            '<div class="list-item"><span class="nm"><a href="p/'
            + esc(fname)
            + '">'
            + esc(zh)
            + '</a></span><span class="ds">'
            + esc(desc)
            + '</span><span class="st">⭐ '
            + esc("{:,}".format(int(r.get("s") or 0)))
            + "</span></div>"
        )
    today = datetime.date.today().isoformat()
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>全部精选 - GitHub 中文发现器</title>
<meta name="description" content="GitHub 中文发现器：全部精选开源项目清单，共 __CNT__ 个，全中文介绍。">
<link rel="canonical" href="__BASE__/list.html">
<meta name="theme-color" content="#0d1117">
<style>
__CSS__
</style>
</head>
<body>
<header class="site-head">
  <span class="logo">🧭 GitHub 中文发现器</span>
  <a class="back" href="__BASE__/">← 返回首页</a>
</header>
<main class="container">
  <h1>全部精选项目（__CNT__ 个）</h1>
  <p class="desc" style="font-size:13px;color:var(--text2)">清单生成于 __TODAY__ · 每条都有大白话中文介绍，点击进入项目详情</p>
  __ITEMS__
</main>
<footer>© GitHub 中文发现器</footer>
</body>
</html>
""".replace(
        "__CSS__", PAGE_CSS
    ).replace(
        "__BASE__", BASE_URL
    ).replace(
        "__CNT__", str(len(repos))
    ).replace(
        "__TODAY__", today
    ).replace(
        "__ITEMS__", "".join(items)
    )


def build_sitemap(repos, ctx):
    urls = []
    # v1.19.2：去掉 lastmod（每次构建标"今天"会让搜索引擎判定字段不可信）
    urls.append(
        "  <url>\n    <loc>" + BASE_URL + "/</loc>\n    <changefreq>daily</changefreq>\n    <priority>1.0</priority>\n  </url>"
    )
    urls.append(
        "  <url>\n    <loc>" + BASE_URL + "/list.html</loc>\n    <changefreq>weekly</changefreq>\n    <priority>0.9</priority>\n  </url>"
    )
    for r in repos:
        n = r["n"]
        owner, repo = n.split("/")
        fname = owner + "-" + repo + ".html"
        urls.append(
            "  <url>\n    <loc>" + BASE_URL + "/p/" + fname + "</loc>\n    <changefreq>weekly</changefreq>\n    <priority>0.8</priority>\n  </url>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>\n"
    )


def main():
    data = load_data()
    repos = data["repos"]
    os.makedirs(OUT_DIR, exist_ok=True)

    # 幂等自检：项目页文件名必须唯一（owner/repo 含连字符时可能碰撞）
    seen = {}
    for r in repos:
        n = r["n"]
        owner, repo = n.split("/")
        fname = owner + "-" + repo + ".html"
        if fname in seen:
            sys.exit("文件名冲突：" + fname + "（" + seen[fname] + " 与 " + n + "）")
        seen[fname] = n

    pages = {}
    for r in repos:
        n = r["n"]
        html_text, fname = build_project_page(n, r, data)
        pages[fname] = html_text
        with open(os.path.join(OUT_DIR, fname), "w", encoding="utf-8") as f:
            f.write(html_text)

    with open(os.path.join(ROOT, "list.html"), "w", encoding="utf-8") as f:
        f.write(build_list_page(repos, data))
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(build_sitemap(repos, data))

    print("✅ 已生成 {} 个静态项目页 + list.html + sitemap.xml（共 {} 项）".format(len(pages), len(repos)))


if __name__ == "__main__":
    main()
