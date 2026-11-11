#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_annual.py — 年度精选页 + 分享封面

读取 annual.json（人工策展）+ data.js（中文名/star/分类）
输出：annual/<year>.html、annual/index.html（跳转）、og/annual-<year>.png
用法：python build_annual.py
"""
import html as html_mod
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_pages as bp  # noqa: E402
import build_og as og  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(ROOT, "annual")
SRC = os.path.join(ROOT, "annual.json")

EXTRA_CSS = """
.ann-hero{background:linear-gradient(135deg,rgba(88,166,255,.18),rgba(163,113,247,.14));
  border:1px solid var(--border);border-radius:14px;padding:18px 20px;margin:14px 0 22px}
.ann-hero h1{font-size:26px;margin:0 0 6px}
.ann-hero .sub{color:var(--text2);font-size:13.5px;line-height:1.7}
.ann-hero .meta{margin-top:10px;font-size:12px;color:var(--text2)}
.ann-group{margin:26px 0 0}
.ann-group h2{font-size:18px;margin:0 0 4px}
.ann-group .gdesc{font-size:13px;color:var(--text2);margin-bottom:12px;line-height:1.7}
.ann-item{display:flex;gap:12px;background:var(--card);border:1px solid var(--border);border-radius:12px;
  padding:12px 14px;margin-bottom:10px;text-decoration:none;color:var(--text)}
.ann-item:hover{border-color:var(--accent)}
.ann-no{flex:0 0 28px;height:28px;border-radius:8px;background:var(--card2);color:var(--text2);
  font-size:13px;font-weight:700;display:flex;align-items:center;justify-content:center}
.ann-main{flex:1;min-width:0}
.ann-name{font-size:15px;font-weight:600;color:var(--text)}
.ann-repo{font-size:11.5px;color:var(--text2);margin-left:8px}
.ann-why{font-size:13px;color:#c9d1d9;line-height:1.7;margin-top:4px}
.ann-meta{font-size:11.5px;color:var(--star);margin-top:5px}
.ann-foot{margin-top:26px;font-size:12.5px;color:var(--text2);line-height:1.8}
"""


def esc(s):
    return html_mod.escape(str(s), quote=True)


def build_cover(year, title, subtitle, path):
    from PIL import Image, ImageDraw

    W, H = 1200, 630
    img = Image.new("RGB", (W, H), og.BG)
    glow = Image.new("RGB", (W, H), og.BG)
    gd = ImageDraw.Draw(glow)
    gd.ellipse((-200, -280, 700, 500), fill=(26, 38, 62))
    gd.ellipse((820, 360, 1360, 900), fill=(30, 26, 52))
    img = Image.blend(img, glow, 0.9)
    d = ImageDraw.Draw(img)
    og.rounded(d, (36, 36, W - 36, H - 36), 24, fill=og.CARD, outline=og.BORDER, width=2)

    f_brand = og.font(28, bold=True)
    d.text((76, 76), "GitHub 中文发现器", font=f_brand, fill=og.ACCENT)
    f_year = og.font(22)
    d.text((W - 76 - d.textlength("2026", font=f_year), 78), str(year), font=f_year, fill=og.DIM)

    f_t = og.font(88, bold=True)
    d.text((76, 186), title, font=f_t, fill=og.TEXT)
    f_s = og.font(34)
    for i, ln in enumerate(og.wrap(subtitle, f_s, W - 200, d, max_lines=2)):
        d.text((78, 320 + i * 48), ln, font=f_s, fill=(201, 209, 217))

    d.line([(76, H - 150), (W - 76, H - 150)], fill=og.BORDER, width=1)
    f_small = og.font(26)
    d.text((78, H - 108), "一整年，20 个值得知道的项目", font=f_small, fill=og.DIM)
    site = "p0w3rd1n8.github.io/github-cn-finder"
    d.text((W - 78 - d.textlength(site, font=f_small), H - 108), site, font=f_small, fill=og.DIM)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, "PNG", optimize=True)


def main():
    with open(SRC, encoding="utf-8") as f:
        cfg = json.load(f)
    data = bp.load_data()
    zh = data["repo_zh"]
    meta = {r["n"]: r for r in data["repos"]}
    year = cfg["year"]

    parts = [
        '<div class="ann-hero">',
        f'<h1>{esc(cfg["title"])}</h1>',
        f'<div class="sub">{esc(cfg["subtitle"])}</div>',
        f'<div class="sub" style="margin-top:8px">{esc(cfg["intro"])}</div>',
        f'<div class="meta">共 {sum(len(g["items"]) for g in cfg["groups"])} 个项目 · 由人工挑选 · 更新于 {esc(cfg.get("updated", ""))}</div>',
        "</div>",
    ]

    no = 0
    for g in cfg["groups"]:
        parts.append(f'<div class="ann-group"><h2>{esc(g["name"])}</h2>'
                     f'<div class="gdesc">{esc(g.get("desc", ""))}</div>')
        for it in g["items"]:
            no += 1
            n = it["n"]
            m = meta.get(n, {})
            owner, repo = n.split("/")
            star = m.get("s", 0)
            parts.append(
                f'<a class="ann-item" href="../p/{esc(owner)}-{esc(repo)}.html">'
                f'<span class="ann-no">{no}</span>'
                f'<span class="ann-main">'
                f'<span class="ann-name">{esc(zh.get(n) or repo)}</span>'
                f'<span class="ann-repo">{esc(n)}</span>'
                f'<div class="ann-why">{esc(it["why"])}</div>'
                f'<div class="ann-meta">⭐ {int(star):,} · {esc(m.get("c", ""))}</div>'
                f"</span></a>"
            )
        parts.append("</div>")

    parts.append(
        '<div class="ann-foot">这份榜单是人工挑的，标准是「中文用户用得上」而不是 star 高。'
        '没选上的不代表不好——全部 162 个都在 <a href="../list.html">完整清单</a> 里。<br>'
        f'<a href="../">← 回首页</a> · <a href="../timeline/">🕒 更新记录</a> · <a href="../c/">📚 专题合辑</a></div>'
    )

    body = "\n".join(parts)
    page = (
        '<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f'<title>{esc(cfg["title"])} - GitHub 中文发现器</title>\n'
        f'<meta name="description" content="{esc(cfg["subtitle"])}">\n'
        f'<link rel="canonical" href="{bp.BASE_URL}/annual/{year}.html">\n'
        f'<link rel="icon" href="{bp.BASE_URL}/icon.svg" type="image/svg+xml">\n'
        f'<meta property="og:title" content="{esc(cfg["title"])} - GitHub 中文发现器">\n'
        f'<meta property="og:description" content="{esc(cfg["subtitle"])}">\n'
        f'<meta property="og:image" content="{bp.BASE_URL}/og/annual-{year}.png">\n'
        '<meta name="theme-color" content="#0d1117">\n'
        f"<style>\n{bp.PAGE_CSS}{EXTRA_CSS}\n</style>\n</head>\n<body>\n"
        '<header class="site-head"><span class="logo">🧭 GitHub 中文发现器</span>'
        f'<a class="back" href="{bp.BASE_URL}/">← 返回首页</a></header>\n'
        f'<main class="container">\n{body}\n</main>\n</body>\n</html>\n'
    )

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, f"{year}.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(page)
    # 目录索引：直接跳当年
    with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(
            '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">'
            f'<meta http-equiv="refresh" content="0;url={year}.html">'
            f"<title>{esc(cfg['title'])}</title></head><body>"
            f'<a href="{year}.html">{esc(cfg["title"])}</a></body></html>'
        )
    build_cover(year, cfg["title"], cfg["subtitle"],
                os.path.join(ROOT, "og", f"annual-{year}.png"))
    print(f"✅ 年度精选：{no} 个项目 / {len(cfg['groups'])} 组 → annual/{year}.html + og/annual-{year}.png")


if __name__ == "__main__":
    main()
