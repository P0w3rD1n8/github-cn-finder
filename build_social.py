#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_social.py — 生成小红书竖版图（1080×1440，3:4）

用法：
    python build_social.py                          # 默认读 annual.json
    python build_social.py --config social_zhuangji.json --out _shots/social-zhuangji

配置字段（都可省略，有默认值）：
    title     大标题（封面）
    kicker    封面上方小字
    subtitle  副标题
    brand     封面顶部的品牌名
    stats     [[数字, 说明], ...] 封面的三个数字
    groups    [{name, desc, items:[{n, why}]}]  分组与项目
    footer    每张底部的说明
    steps     结尾页的三步说明（列表）
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_pages as bp  # noqa: E402
import build_og as og  # noqa: E402
from PIL import ImageDraw  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1440

BG = (13, 17, 23)
CARD = (22, 27, 34)
BORDER = (48, 54, 61)
TEXT = (230, 237, 243)
DIM = (139, 148, 158)
ACCENT = (88, 166, 255)
PURPLE = (163, 113, 247)


def canvas():
    from PIL import Image

    img = Image.new("RGB", (W, H), BG)
    glow = Image.new("RGB", (W, H), BG)
    gd = ImageDraw.Draw(glow)
    gd.ellipse((-300, -380, 700, 520), fill=(26, 38, 62))
    gd.ellipse((620, 980, 1300, 1700), fill=(32, 26, 52))
    return Image.blend(img, glow, 0.92)


def footer(d, idx, total, text):
    d.line([(80, H - 150), (W - 80, H - 150)], fill=BORDER, width=2)
    f = og.font(26)
    d.text((80, H - 112), text, font=f, fill=DIM)
    tag = f"{idx}/{total}"
    d.text((W - 80 - d.textlength(tag, font=f), H - 112), tag, font=f, fill=DIM)


def chip(d, x, y, text, f, fg, bg, border):
    w = d.textlength(text, font=f) + 40
    og.rounded(d, (x, y, x + w, y + 52), 26, fill=bg, outline=border, width=2)
    d.text((x + 20, y + 10), text, font=f, fill=fg)
    return x + w + 14


def cover(cfg, zh, total_pages):
    d = ImageDraw.Draw(canvas()) if False else None  # placeholder to keep linters quiet
    img = canvas()
    d = ImageDraw.Draw(img)

    f_brand = og.font(30, bold=True)
    d.text((80, 92), cfg.get("brand", "GitHub 中文发现器"), font=f_brand, fill=ACCENT)
    d.text((80, 170), cfg.get("kicker", "年 度 榜 单"), font=og.font(26, bold=True), fill=PURPLE)

    f_t = og.font(104, bold=True)
    lines = og.wrap(cfg["title"], f_t, W - 160, d, max_lines=2)
    ty = 226
    for ln in lines:
        d.text((74, ty), ln, font=f_t, fill=TEXT if ln is lines[0] else PURPLE)
        ty += 122

    f_sub = og.font(40)
    sy = ty + 28
    for ln in og.wrap(cfg.get("subtitle", ""), f_sub, W - 180, d, max_lines=2):
        d.text((80, sy), ln, font=f_sub, fill=(201, 209, 217))
        sy += 58

    # 数字
    stats = cfg.get("stats") or [
        [str(sum(len(g["items"]) for g in cfg["groups"])), "个项目"],
        [str(len(cfg["groups"])), "个主题"],
        ["162", "个项目里挑的"],
    ]
    f_num = og.font(78, bold=True)
    f_lbl = og.font(26)
    sx = 80
    ny = max(sy + 40, 640)
    for num, lbl in stats:
        d.text((sx, ny), str(num), font=f_num, fill=PURPLE)
        d.text((sx + d.textlength(str(num), font=f_num) + 12, ny + 48), lbl, font=f_lbl, fill=DIM)
        sx += 330

    # 分组标签
    f_chip = og.font(28)
    x, y = 80, ny + 130
    for g in cfg["groups"]:
        w = d.textlength(g["name"], font=f_chip) + 40
        if x + w > W - 80:
            x, y = 80, y + 66
        x = chip(d, x, y, g["name"], f_chip, (200, 180, 255), (36, 30, 52), (86, 66, 128))

    # 代表项目
    f_pick = og.font(26)
    py = y + 110
    d.text((80, py - 56), "比如这几个：", font=og.font(24), fill=DIM)
    px = 80
    for g in cfg["groups"]:
        n = g["items"][0]["n"]
        label = zh.get(n) or n.split("/")[1]
        w = d.textlength(label, font=f_pick) + 40
        if px + w > W - 80:
            px, py = 80, py + 62
        px = chip(d, px, py, label, f_pick, TEXT, CARD, BORDER)

    f_cta = og.font(34, bold=True)
    d.text((80, H - 262), cfg.get("cover_cta", "完整清单就在站里，搜站名即可"), font=f_cta, fill=TEXT)
    d.text((80, H - 212), "p0w3rd1n8.github.io/github-cn-finder", font=og.font(24), fill=DIM)
    footer(d, 1, total_pages, cfg.get("footer", "GitHub 中文发现器"))
    return img


def group_page(cfg, g, idx, total_pages, zh, meta):
    img = canvas()
    d = ImageDraw.Draw(img)
    d.text((80, 92), f"{idx - 1} / {len(cfg['groups'])}", font=og.font(26, bold=True), fill=PURPLE)
    d.text((76, 140), g["name"], font=og.font(66, bold=True), fill=TEXT)

    yy = 226
    for ln in og.wrap(g.get("desc", ""), og.font(28), W - 160, d, max_lines=2):
        d.text((80, yy), ln, font=og.font(28), fill=DIM)
        yy += 40

    f_no = og.font(34, bold=True)
    f_name = og.font(40, bold=True)
    f_repo = og.font(22)
    f_why = og.font(26)
    # 按条目数把卡片块垂直居中，避免 3 条时下方一片空
    block_h = len(g["items"]) * 226 - 14
    y = 330 + max(0, (932 - block_h) // 2)
    for i, it in enumerate(g["items"], 1):
        n = it["n"]
        name = zh.get(n) or n.split("/")[1]
        star = meta.get(n, {}).get("s", 0)
        og.rounded(d, (72, y, W - 72, y + 212), 20, fill=CARD, outline=BORDER, width=2)
        og.rounded(d, (100, y + 30, 156, y + 86), 14, fill=(38, 32, 58))
        d.text((100 + (56 - d.textlength(str(i), font=f_no)) / 2, y + 40), str(i), font=f_no, fill=PURPLE)

        tx = 180
        d.text((tx, y + 26), name, font=f_name, fill=TEXT)
        d.text((tx, y + 78), f"{n}   ★ {int(star):,}", font=f_repo, fill=DIM)
        wy = y + 114
        for ln in og.wrap(it["why"], f_why, W - tx - 72, d, max_lines=2):
            d.text((tx, wy), ln, font=f_why, fill=(201, 209, 217))
            wy += 40
        y += 226

    footer(d, idx, total_pages, cfg.get("footer", "GitHub 中文发现器"))
    return img


def cta_page(cfg, idx, total_pages, zh):
    img = canvas()
    d = ImageDraw.Draw(img)
    d.text((80, 120), cfg.get("cta_kicker", "怎 么 找"), font=og.font(28, bold=True), fill=PURPLE)
    f_t = og.font(72, bold=True)
    d.text((76, 180), cfg.get("cta_title", "收藏这篇，"), font=f_t, fill=TEXT)
    d.text((76, 274), cfg.get("cta_title2", "换电脑时照着装"), font=f_t, fill=TEXT)

    steps = cfg.get("steps") or [
        ["1", "搜索「GitHub 中文发现器」"],
        ["2", "进站后点顶部「2026 年度精选」"],
        ["3", "20 个项目都有中文说明和国内镜像"],
    ]
    f_step = og.font(32)
    f_k = og.font(28, bold=True)
    y = 440
    for no, txt in steps:
        og.rounded(d, (80, y, 132, y + 52), 12, fill=(38, 32, 58))
        d.text((80 + (52 - d.textlength(no, font=f_k)) / 2, y + 10), no, font=f_k, fill=PURPLE)
        for j, ln in enumerate(og.wrap(txt, f_step, W - 260, d, max_lines=2)):
            d.text((156, y + 4 + j * 42), ln, font=f_step, fill=TEXT)
        y += 92 if len(txt) < 22 else 128

    og.rounded(d, (72, 830, W - 72, 1210), 22, fill=CARD, outline=BORDER, width=2)
    d.text((104, 866), cfg.get("cta_box_title", "这几组分别是："), font=og.font(30, bold=True), fill=DIM)
    f_g = og.font(32)
    f_s = og.font(24)
    yy = 934
    for g in cfg["groups"]:
        d.text((104, yy), "· " + g["name"], font=f_g, fill=TEXT)
        x2 = 104 + d.textlength("· " + g["name"], font=f_g) + 16
        names = "、".join(it["n"].split("/")[1] for it in g["items"][:2])
        d.text((x2, yy + 4), names + " …", font=f_s, fill=DIM)
        yy += 52

    footer(d, idx, total_pages, cfg.get("footer", "GitHub 中文发现器"))
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="annual.json")
    ap.add_argument("--out", default=os.path.join("_shots", "social"))
    args = ap.parse_args()

    cfg_path = args.config if os.path.isabs(args.config) else os.path.join(ROOT, args.config)
    out_dir = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    data = bp.load_data()
    zh = data["repo_zh"]
    meta = {r["n"]: r for r in data["repos"]}

    total_pages = 1 + len(cfg["groups"]) + 1
    os.makedirs(out_dir, exist_ok=True)
    imgs = [("01-cover.png", cover(cfg, zh, total_pages))]
    for i, g in enumerate(cfg["groups"], 2):
        imgs.append((f"{i:02d}-group-{i-1}.png", group_page(cfg, g, i, total_pages, zh, meta)))
    imgs.append((f"{len(imgs)+1:02d}-cta.png", cta_page(cfg, len(imgs) + 1, total_pages, zh)))

    for name, img in imgs:
        img.save(os.path.join(out_dir, name), "PNG", optimize=True)
    print(f"✅ {len(imgs)} 张 1080×1440 → {out_dir}")
    for name, _ in imgs:
        print("   ", name)


if __name__ == "__main__":
    main()
