#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_og.py — 为每个项目生成分享封面图（1200×630 PNG）

为什么不用 Playwright 截图：162 张逐页截图要几分钟且依赖浏览器；
Pillow 直接画，1 秒级完成，CI 里也只需要 pillow + 一个中文字体。

输出：og/<owner>-<repo>.png（供 p/ 页面 og:image 使用）
用法：python build_og.py [--force] [--only owner/repo]
依赖：Pillow；中文字体自动探测（Windows msyh / Linux Noto CJK）
"""
import argparse
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "og")
W, H = 1200, 630

BG = (13, 17, 23)
CARD = (22, 27, 34)
BORDER = (48, 54, 61)
TEXT = (230, 237, 243)
DIM = (139, 148, 158)
ACCENT = (88, 166, 255)
STAR = (240, 180, 41)

FONT_CANDIDATES = [
    (r"C:\Windows\Fonts\msyh.ttc", 0),
    (r"C:\Windows\Fonts\msyhbd.ttc", 0),
    (r"C:\Windows\Fonts\NotoSansSC-VF.ttf", 0),
    (r"C:\Windows\Fonts\simhei.ttf", 0),
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 0),
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", 0),
    ("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", 0),
    ("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 1),
    ("/System/Library/Fonts/PingFang.ttc", 0),
]

_BOLD = None
_REG = None


def find_font(bold=False):
    global _BOLD, _REG
    if bold and _BOLD:
        return _BOLD
    if not bold and _REG:
        return _REG
    for path, idx in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                f = ImageFont.truetype(path, 40, index=idx)
                if bold:
                    _BOLD = path, idx
                else:
                    _REG = path, idx
                return path, idx
            except Exception:
                continue
    raise SystemExit("找不到可用的中文字体，无法生成 OG 图")


def font(size, bold=False):
    path, idx = find_font(bold)
    return ImageFont.truetype(path, size, index=idx)


PUNCT = "，。、；：！？）》】…·"


def wrap(text, f, max_w, draw, max_lines=2):
    lines, cur = [], ""
    consumed = 0
    for i, ch in enumerate(text):
        fits = draw.textlength(cur + ch, font=f) <= max_w
        # 标点悬挂：句号/逗号等不要单独掉到下一行开头，允许略微超宽
        if not fits and ch in PUNCT and cur:
            cur += ch
            consumed = i + 1
            continue
        if fits:
            cur += ch
            consumed = i + 1
        else:
            lines.append(cur)
            cur = ch
            consumed = i + 1
            if len(lines) == max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    if consumed < len(text) and lines:
        # 只有真的被截断才补省略号
        last = lines[-1]
        while last and draw.textlength(last + "…", font=f) > max_w:
            last = last[:-1]
        lines[-1] = last + "…"
    return lines


def rounded(draw, box, r, fill=None, outline=None, width=1):
    draw.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def render(zh, full, cat, desc, stars, path):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # 背景氛围：左上角大圆 + 右下角小圆（低对比，不抢字）
    glow = Image.new("RGB", (W, H), BG)
    gd = ImageDraw.Draw(glow)
    gd.ellipse((-260, -320, 620, 420), fill=(23, 34, 52))
    gd.ellipse((760, 380, 1320, 900), fill=(20, 28, 40))
    img = Image.blend(img, glow, 0.85)
    d = ImageDraw.Draw(img)

    # 卡片边框
    rounded(d, (36, 36, W - 36, H - 36), 24, fill=CARD, outline=BORDER, width=2)

    # 顶部：站点名 + 分类 pill
    f_brand = font(28, bold=True)
    d.text((76, 76), "GitHub 中文发现器", font=f_brand, fill=ACCENT)
    f_cat = font(24)
    cw = d.textlength(cat, font=f_cat)
    rounded(d, (W - 76 - cw - 44, 70, W - 76, 118), 12, fill=(30, 40, 56), outline=(45, 60, 82), width=1)
    d.text((W - 76 - cw - 22, 80), cat, font=f_cat, fill=(159, 179, 204))

    # 中文名（最多两行）
    f_title = font(66, bold=True)
    lines = wrap(zh, f_title, W - 190, d, max_lines=2)
    y = 176 if len(lines) > 1 else 210
    for ln in lines:
        d.text((76, y), ln, font=f_title, fill=TEXT)
        y += 82

    # 仓库名
    f_repo = font(34)
    d.text((78, y + 10), full, font=f_repo, fill=DIM)

    # 简介（最多两行）
    f_desc = font(30)
    dlines = wrap(desc, f_desc, W - 190, d, max_lines=2)
    dy = y + 76
    for ln in dlines:
        d.text((78, dy), ln, font=f_desc, fill=(201, 209, 217))
        dy += 44

    # 底部：分隔线 + 说明 + 域名（不放 star 数：star 每小时变，图会一直过期）
    d.line([(76, H - 150), (W - 76, H - 150)], fill=BORDER, width=1)
    f_small = font(26)
    d.text((78, H - 108), "精选开源项目 · 全部中文介绍", font=f_small, fill=DIM)
    site = "p0w3rd1n8.github.io/github-cn-finder"
    sw = d.textlength(site, font=f_small)
    d.text((W - 78 - sw, H - 108), site, font=f_small, fill=DIM)

    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, "PNG", optimize=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--force", action="store_true", help="已存在的图也重新生成")
    args = ap.parse_args()

    sys.path.insert(0, ROOT)
    import build_pages as bp
    data = bp.load_data()

    made = skipped = 0
    for r in data["repos"]:
        n = r["n"]
        if args.only and n != args.only:
            continue
        owner, repo = n.split("/")
        zh = data["repo_zh"].get(n) or repo
        desc = data["cn_desc"].get(n) or r.get("d", "")
        path = os.path.join(OUT, f"{owner}-{repo}.png")
        if os.path.exists(path) and not args.only and not args.force:
            skipped += 1
            continue
        render(zh, n, r.get("c", ""), desc, r.get("s", 0), path)
        made += 1
    print(f"✅ OG 图：新生成 {made} 张，跳过已存在 {skipped} 张 → {OUT}")


if __name__ == "__main__":
    main()
