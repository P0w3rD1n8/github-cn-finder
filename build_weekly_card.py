#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""每周一张「涨星榜」图（v1.36.0）。

为什么做这个：微信群里「图片能转发，链接不能」，一张好看的榜单图等于别人替你分发。
数据全部来自 weekly.json 的两期快照，不需要人介入，每周六随周刊一起自动出图。

产出（放在 weekly/ 目录，可直接用手机打开长按保存）：
  weekly/card-<日期>.png        带二维码版（发微信群 / 朋友圈）
  weekly/card-<日期>-clean.png  不带二维码版（发小红书，平台对二维码敏感）
"""
import json
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
WEEKLY = os.path.join(ROOT, "weekly.json")
DATA = os.path.join(ROOT, "data.js")
OUT_DIR = os.path.join(ROOT, "weekly")
SITE_TEXT = "p0w3rd1n8.github.io/github-cn-finder"
SITE_URL = "https://p0w3rd1n8.github.io/github-cn-finder/"

BG = (13, 17, 23)
CARD = (22, 27, 34)
BORDER = (48, 54, 61)
TEXT = (230, 237, 243)
DIM = (139, 148, 158)
ACCENT = (88, 166, 255)
GREEN = (63, 185, 80)
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

JSON_MAP = r'"(%s)"\s*:\s*"([^"]*)"'


def find_font(bold=False):
    for path, idx in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                ImageFont.truetype(path, 40, index=idx)
                return path, idx
            except Exception:
                continue
    raise SystemExit("找不到中文字体（Windows msyh / Linux Noto CJK）")


def font(size, bold=False):
    path, idx = find_font(bold)
    return ImageFont.truetype(path, size, index=idx)


def load_zh_names():
    src = open(DATA, encoding="utf-8").read()
    m = re.search(r"const REPO_ZH = \{(.*?)\n\};", src, re.S)
    if not m:
        return {}
    return dict(re.findall(JSON_MAP % r"[^\"\s]+/[^\"\s]+", m.group(1)))


def fit(draw, text, f, max_w):
    if draw.textlength(text, font=f) <= max_w:
        return text
    while text and draw.textlength(text + "…", font=f) > max_w:
        text = text[:-1]
    return text + "…"


def build_gainers(snapshots, zh):
    prev, cur = snapshots[-2], snapshots[-1]
    rows = []
    for name, s in cur.get("stars", {}).items():
        p = prev.get("stars", {}).get(name)
        if isinstance(p, (int, float)) and s > p:
            rows.append((s - p, name, s))
    rows.sort(reverse=True)
    out = []
    for gain, name, s in rows[:10]:
        out.append((zh.get(name, name), gain, s))
    return prev.get("date", ""), cur.get("date", ""), out


def render(date_prev, date_cur, rows, with_qr, out_path):
    W, H = 1080, 1440
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # 顶部装饰条
    for y in range(6):
        d.line([(0, y), (W, y)], fill=(30, 60, 110))

    d.text((56, 52), "GitHub 中文发现器", font=font(28, True), fill=ACCENT)
    d.text((56, 104), "本周涨星榜", font=font(78, True), fill=TEXT)
    d.text((58, 208), f"{date_prev} → {date_cur}", font=font(30), fill=DIM)
    d.text((W - 56 - d.textlength("全中文说明", font=font(26)), 58),
           "全中文说明", font=font(26), fill=DIM)

    d.line([(56, 268), (W - 56, 268)], fill=BORDER, width=2)

    y = 296
    ROW = 86
    for i, (name, gain, stars) in enumerate(rows):
        if i % 2 == 0:
            d.rounded_rectangle([44, y - 10, W - 44, y + ROW - 22], radius=10, fill=CARD)
        rank = str(i + 1)
        rw = d.textlength(rank, font=font(34, True))
        d.text((56 + (34 - rw) / 2, y + 4), rank, font=font(34, True),
               fill=GREEN if i < 3 else DIM)
        d.text((112, y + 2), fit(d, name, font(34, True), 560), font=font(34, True), fill=TEXT)
        gain_s = f"+{gain:,}"
        gw = d.textlength(gain_s, font=font(34, True))
        d.text((W - 220 - gw, y + 2), gain_s, font=font(34, True), fill=GREEN)
        star_s = f"{stars:,}"
        sw = d.textlength(star_s, font=font(24))
        d.text((W - 60 - sw, y + 10), star_s, font=font(24), fill=DIM)
        y += ROW

    d.line([(56, 1196), (W - 56, 1196)], fill=BORDER, width=2)

    if with_qr:
        txt_x = 56
        lines = [("每周六更新一期", 26, DIM), ("172 个开源项目 · 中文四段说明", 26, (201, 209, 217)),
                 (SITE_TEXT, 24, ACCENT)]
        ty = 1226
        for s, size, color in lines:
            d.text((txt_x, ty), s, font=font(size), fill=color)
            ty += 40
        # 二维码（标准黑码白底：反色码部分扫码器识别不了，深色底上必须垫白块）
        import qrcode
        qr = qrcode.QRCode(box_size=5, border=2)
        qr.add_data(SITE_URL)
        qr.make(fit=True)
        qimg = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        qsize = 200
        qimg = qimg.resize((qsize, qsize), Image.LANCZOS)
        qx, qy = W - 56 - qsize, 1216
        d.rounded_rectangle([qx - 10, qy - 10, qx + qsize + 10, qy + qsize + 10],
                            radius=10, fill=(255, 255, 255))
        img.paste(qimg, (qx, qy))
    else:
        ty = 1226
        lines = [("每周六更新一期", 26, DIM), ("172 个开源项目 · 中文四段说明", 26, (201, 209, 217)),
                 (SITE_TEXT, 24, ACCENT)]
        for s, size, color in lines:
            d.text((56, ty), s, font=font(size), fill=color)
            ty += 40

    img.save(out_path, "PNG", optimize=True)
    return img.size


def main():
    if not os.path.exists(WEEKLY):
        print("没有 weekly.json，跳过")
        return 0
    try:
        data = json.load(open(WEEKLY, encoding="utf-8"))
    except Exception as e:
        print(f"weekly.json 读取失败：{e}")
        return 0
    snaps = data.get("snapshots") or []
    if len(snaps) < 2:
        print(f"快照只有 {len(snaps)} 期，至少要 2 期才能算涨星，跳过")
        return 0

    zh = load_zh_names()
    date_prev, date_cur, rows = build_gainers(snaps, zh)
    if not rows:
        print("本期没有上涨项目，跳过")
        return 0

    os.makedirs(OUT_DIR, exist_ok=True)
    p1 = os.path.join(OUT_DIR, f"card-{date_cur}.png")
    p2 = os.path.join(OUT_DIR, f"card-{date_cur}-clean.png")
    print("  带二维码:", render(date_prev, date_cur, rows, True, p1), "->", os.path.basename(p1))
    print("  无二维码:", render(date_prev, date_cur, rows, False, p2), "->", os.path.basename(p2))
    print(f"✅ 涨星榜图已生成（{date_prev} → {date_cur}，Top {len(rows)}）")
    return 0


if __name__ == "__main__":
    # 出图是加分项：任何异常都只打印，不让它拖垮 build-pages 里的周刊重建
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:
        print(f"⚠️ 涨星榜图生成失败（已忽略，不影响周刊）：{type(e).__name__}: {e}")
        sys.exit(0)
