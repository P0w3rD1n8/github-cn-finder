#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_social.py — 生成小红书竖版图（1080×1440，3:4）

1 张封面 + 每组一张 + 1 张引导，共 7 张，输出到 _shots/social/。
读取 annual.json（策展）+ data.js（中文名/star）。
用法：python build_social.py
"""
import html as html_mod
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_pages as bp  # noqa: E402
import build_og as og  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "_shots", "social")
W, H = 1080, 1440

BG = (13, 17, 23)
CARD = (22, 27, 34)
BORDER = (48, 54, 61)
TEXT = (230, 237, 243)
DIM = (139, 148, 158)
ACCENT = (88, 166, 255)
PURPLE = (163, 113, 247)
STAR = (240, 180, 41)


def canvas():
    img = Image.new("RGB", (W, H), BG)
    glow = Image.new("RGB", (W, H), BG)
    gd = ImageDraw.Draw(glow)
    gd.ellipse((-300, -380, 700, 520), fill=(26, 38, 62))
    gd.ellipse((620, 980, 1300, 1700), fill=(32, 26, 52))
    return Image.blend(img, glow, 0.92)


def footer(d, idx):
    d.line([(80, H - 150), (W - 80, H - 150)], fill=BORDER, width=2)
    f = og.font(26)
    d.text((80, H - 112), "GitHub 中文发现器 · 2026 年度精选", font=f, fill=DIM)
    tag = f"{idx}/7"
    d.text((W - 80 - d.textlength(tag, font=f), H - 112), tag, font=f, fill=DIM)


def chip(d, x, y, text, f, fg, bg, border):
    w = d.textlength(text, font=f) + 40
    og.rounded(d, (x, y, x + w, y + 52), 26, fill=bg, outline=border, width=2)
    d.text((x + 20, y + 10), text, font=f, fill=fg)
    return x + w + 14


def cover(cfg, zh):
    img = canvas()
    d = ImageDraw.Draw(img)
    f_brand = og.font(30, bold=True)
    d.text((80, 92), "GitHub 中文发现器", font=f_brand, fill=ACCENT)
    f_badge = og.font(26, bold=True)
    d.text((80, 170), "年 度 榜 单", font=f_badge, fill=PURPLE)

    f_t = og.font(104, bold=True)
    d.text((76, 226), "2026", font=f_t, fill=TEXT)
    d.text((76, 348), "年度精选", font=f_t, fill=PURPLE)

    f_sub = og.font(40)
    for i, ln in enumerate(og.wrap(cfg["subtitle"], f_sub, W - 180, d, max_lines=2)):
        d.text((80, 500 + i * 58), ln, font=f_sub, fill=(201, 209, 217))

    # 五组标签
    f_chip = og.font(28)
    x, y = 80, 650
    for g in cfg["groups"]:
        w = d.textlength(g["name"], font=f_chip) + 40
        if x + w > W - 80:
            x, y = 80, y + 66
        x = chip(d, x, y, g["name"], f_chip, (200, 180, 255), (36, 30, 52), (86, 66, 128))

    # 中段三个数字，填满空白
    total = sum(len(g["items"]) for g in cfg["groups"])
    stats = [(str(total), "个项目"), (str(len(cfg["groups"])), "个主题"), ("162", "里挑出来的")]
    f_num = og.font(78, bold=True)
    f_lbl = og.font(26)
    sx = 80
    for num, lbl in stats:
        d.text((sx, 790), num, font=f_num, fill=PURPLE)
        d.text((sx + d.textlength(num, font=f_num) + 12, 838), lbl, font=f_lbl, fill=DIM)
        sx += 330

    # 每组抽一个代表，填中下段
    f_pick = og.font(26)
    px, py = 80, 960
    d.text((80, 900), "比如这几个：", font=og.font(24), fill=DIM)
    for g in cfg["groups"]:
        n = g["items"][0]["n"]
        label = zh.get(n) or n.split("/")[1]
        w = d.textlength(label, font=f_pick) + 40
        if px + w > W - 80:
            px, py = 80, py + 62
        px = chip(d, px, py, label, f_pick, TEXT, CARD, BORDER)

    f_cta = og.font(34, bold=True)
    d.text((80, H - 260), "20 个项目 · 每个都写了为什么值得装", font=f_cta, fill=TEXT)
    f_small = og.font(26)
    d.text((80, H - 210), "完整清单 → 搜「GitHub 中文发现器」", font=f_small, fill=DIM)
    footer(d, 1)
    return img


def group_page(cfg, g, idx, zh, meta):
    img = canvas()
    d = ImageDraw.Draw(img)
    f_kicker = og.font(26, bold=True)
    d.text((80, 92), f"{idx - 1} / {len(cfg['groups'])}", font=f_kicker, fill=PURPLE)

    f_title = og.font(66, bold=True)
    d.text((76, 140), g["name"], font=f_title, fill=TEXT)
    f_desc = og.font(28)
    yy = 226
    for ln in og.wrap(g.get("desc", ""), f_desc, W - 160, d, max_lines=2):
        d.text((80, yy), ln, font=f_desc, fill=DIM)
        yy += 40

    f_no = og.font(34, bold=True)
    f_name = og.font(40, bold=True)
    f_repo = og.font(22)
    f_why = og.font(27)
    y = 330
    for i, it in enumerate(g["items"], 1):
        n = it["n"]
        name = zh.get(n) or n.split("/")[1]
        star = meta.get(n, {}).get("s", 0)
        og.rounded(d, (72, y, W - 72, y + 212), 20, fill=CARD, outline=BORDER, width=2)

        og.rounded(d, (100, y + 30, 156, y + 86), 14, fill=(38, 32, 58))
        no = str(i)
        d.text((100 + (56 - d.textlength(no, font=f_no)) / 2, y + 40), no, font=f_no, fill=PURPLE)

        tx = 180
        d.text((tx, y + 26), name, font=f_name, fill=TEXT)
        d.text((tx, y + 78), f"{n}   ★ {int(star):,}", font=f_repo, fill=DIM)

        wy = y + 114
        for ln in og.wrap(it["why"], f_why, W - tx - 110, d, max_lines=2):
            d.text((tx, wy), ln, font=f_why, fill=(201, 209, 217))
            wy += 40
        y += 226

    footer(d, idx)
    return img


def cta(cfg, total, idx):
    img = canvas()
    d = ImageDraw.Draw(img)
    f_k = og.font(28, bold=True)
    d.text((80, 120), "怎 么 找", font=f_k, fill=PURPLE)

    f_t = og.font(76, bold=True)
    d.text((76, 180), "收藏这篇，", font=f_t, fill=TEXT)
    d.text((76, 280), "换电脑时照着装", font=f_t, fill=TEXT)

    f_step = og.font(34)
    steps = [
        ("1", "搜索「GitHub 中文发现器」"),
        ("2", "进站后点顶部「2026 年度精选」"),
        ("3", f"{total} 个项目都有中文说明和国内镜像"),
    ]
    y = 460
    for no, txt in steps:
        og.rounded(d, (80, y, 132, y + 52), 12, fill=(38, 32, 58))
        d.text((80 + (52 - d.textlength(no, font=f_k)) / 2, y + 10), no, font=f_k, fill=PURPLE)
        d.text((156, y + 4), txt, font=f_step, fill=TEXT)
        y += 92

    og.rounded(d, (72, 860, W - 72, 1230), 22, fill=CARD, outline=BORDER, width=2)
    f_q = og.font(30, bold=True)
    d.text((104, 896), "这 20 个分成 5 组：", font=f_q, fill=DIM)
    f_g = og.font(32)
    yy = 960
    for g in cfg["groups"]:
        d.text((104, yy), "· " + g["name"], font=f_g, fill=TEXT)
        names = "、".join((g["items"][0]["n"].split("/")[1], g["items"][1]["n"].split("/")[1]))
        d.text((104 + d.textlength("· " + g["name"], font=f_g) + 16, yy + 4), names + " …", font=og.font(24), fill=DIM)
        yy += 52

    footer(d, idx)
    return img


def main():
    with open(os.path.join(ROOT, "annual.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    data = bp.load_data()
    zh = data["repo_zh"]
    meta = {r["n"]: r for r in data["repos"]}

    os.makedirs(OUT, exist_ok=True)
    imgs = [("01-cover.png", cover(cfg, zh))]
    for i, g in enumerate(cfg["groups"], 2):
        imgs.append((f"{i:02d}-group-{i-1}.png", group_page(cfg, g, i, zh, meta)))
    total = sum(len(g["items"]) for g in cfg["groups"])
    imgs.append((f"{len(imgs)+1:02d}-cta.png", cta(cfg, total, len(imgs) + 1)))

    for name, img in imgs:
        img.save(os.path.join(OUT, name), "PNG", optimize=True)
    print(f"✅ 生成 {len(imgs)} 张 1080×1440 → {OUT}")
    for name, _ in imgs:
        print("   ", name)


if __name__ == "__main__":
    main()
