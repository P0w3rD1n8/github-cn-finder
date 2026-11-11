#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_timeline.py — 收录时间线（更新记录页）

数据来源：git 历史里每次 data.js 的变更，对比前后 REPOS 名单，得出「哪天新增/下架了哪些」。
输出：timeline/index.html
用法：python build_timeline.py
注意：CI 里 checkout 需要 fetch-depth: 0，否则只有 1 个提交、时间线为空。
"""
import html as html_mod
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_pages as bp  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(ROOT, "timeline")

EXTRA_CSS = """
.tl-intro{background:var(--card);border:1px solid var(--border);border-left:3px solid var(--accent);
  border-radius:8px;padding:12px 14px;font-size:13.5px;line-height:1.7;margin:14px 0}
.tl-day{margin:22px 0 0}
.tl-date{font-size:15px;font-weight:700;color:var(--text);margin-bottom:6px}
.tl-date .cnt{font-weight:400;font-size:12px;color:var(--text2);margin-left:8px}
.tl-ev{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:10px 12px;margin:8px 0}
.tl-sub{font-size:12px;color:var(--text2);margin-bottom:6px}
.tl-add a,.tl-del span{display:inline-block;margin:2px 8px 2px 0;font-size:13px;color:var(--accent);text-decoration:none}
.tl-del span{color:#8b949e;text-decoration:line-through}
.tl-tag{display:inline-block;font-size:11px;border-radius:6px;padding:1px 7px;margin-left:6px}
.tl-tag.add{background:rgba(63,185,80,.14);color:#3fb950;border:1px solid rgba(63,185,80,.35)}
.tl-tag.del{background:rgba(248,81,73,.14);color:#f85149;border:1px solid rgba(248,81,73,.35)}
"""


def git(*args):
    r = subprocess.run(["git", "-C", ROOT] + list(args), capture_output=True)
    if r.returncode != 0:
        return ""
    return r.stdout.decode("utf-8", "replace")


def names_in(text):
    m = re.search(r"const REPOS = \[(.*?)\n\];", text, re.S)
    if not m:
        return set()
    return set(re.findall(r'\{n:"([^"]+)"', m.group(1)))


def build_events():
    raw = git("log", "--format=%H|%ad|%s", "--date=short", "--", "data.js").strip()
    if not raw:
        return [], 0
    lines = raw.splitlines()
    lines.reverse()  # 从最早开始
    prev = set()
    events = []
    for line in lines:
        parts = line.split("|", 2)
        if len(parts) < 3:
            continue
        sha, date, subject = parts
        text = git("show", sha + ":data.js")
        if not text:
            continue
        cur = names_in(text)
        added = sorted(cur - prev)
        removed = sorted(prev - cur)

        # 把「只换了 owner/大小写」的配对识别成改名，不算新增/下架
        renames = []
        rm_by_repo = {}
        for n in removed:
            rm_by_repo.setdefault(n.split("/")[-1].lower(), []).append(n)
        real_added = []
        for n in added:
            key = n.split("/")[-1].lower()
            if rm_by_repo.get(key):
                old = rm_by_repo[key].pop(0)
                renames.append((old, n))
                removed.remove(old)
            else:
                real_added.append(n)

        if real_added or removed or renames:
            # 第二遍：同一 owner 下的「删一个加一个」多半也是改名（Qwen2.5→Qwen3、lobe-chat→lobehub）
            if removed and real_added:
                by_owner = {}
                for n in removed:
                    by_owner.setdefault(n.split("/")[0].lower(), []).append(n)
                still = []
                for n in real_added:
                    key = n.split("/")[0].lower()
                    if by_owner.get(key):
                        old = by_owner[key].pop(0)
                        renames.append((old, n))
                        removed.remove(old)
                    else:
                        still.append(n)
                real_added = still

        if real_added or removed or renames:
            events.append({
                "sha": sha[:7], "date": date, "subject": subject,
                "added": real_added, "removed": removed, "renames": renames,
            })
        prev = cur
    return events, len(prev)


def esc(s):
    return html_mod.escape(str(s), quote=True)


def main():
    data = bp.load_data()
    zh = data["repo_zh"]
    star = {r["n"]: r.get("s", 0) for r in data["repos"]}
    events, total = build_events()
    if not events:
        print("⚠️ 没有可用的 git 历史（CI 里需要 fetch-depth: 0），跳过时间线生成")
        return

    # 按日期分组
    by_date = {}
    for ev in events:
        by_date.setdefault(ev["date"], []).append(ev)

    parts = []
    total_added = sum(len(e["added"]) for e in events)
    for date in sorted(by_date, reverse=True):
        evs = by_date[date]
        add_n = sum(len(e["added"]) for e in evs)
        del_n = sum(len(e["removed"]) for e in evs)
        ren_n = sum(len(e["renames"]) for e in evs)
        chips = []
        if add_n:
            chips.append(f'<span class="tl-tag add">新增 {add_n}</span>')
        if del_n:
            chips.append(f'<span class="tl-tag del">下架 {del_n}</span>')
        if ren_n:
            chips.append(f'<span class="tl-tag">改名 {ren_n}</span>')
        parts.append(f'<div class="tl-day"><div class="tl-date">{esc(date)}'
                     f'<span class="cnt">{"".join(chips)}</span></div>')
        for ev in evs:
            bits = [f'<div class="tl-sub">{esc(ev["subject"])}</div>']
            if ev["added"]:
                links = "".join(
                    f'<a href="../p/{esc(n.split("/")[0])}-{esc(n.split("/")[1])}.html" '
                    f'title="{esc(n)}">+ {esc(zh.get(n) or n.split("/")[1])}</a>'
                    for n in ev["added"]
                )
                bits.append(f'<div class="tl-add">{links}</div>')
            if ev["removed"]:
                links = "".join(f'<span>{esc(n)}</span>' for n in ev["removed"])
                bits.append(f'<div class="tl-del">下架：{links}</div>')
            if ev["renames"]:
                pairs = "、".join(f'{esc(o)} → {esc(nn)}' for o, nn in ev["renames"])
                bits.append(f'<div class="tl-del">改名：{pairs}</div>')
            parts.append('<div class="tl-ev">' + "".join(bits) + "</div>")
        parts.append("</div>")

    body = (
        "<h1>🕒 更新记录</h1>\n"
        f'<div class="tl-intro">这个站一直在加东西：共 <b>{len(events)}</b> 次内容更新，'
        f'累计新增 <b>{total_added}</b> 个项目，目前收录 <b>{total}</b> 个。<br>'
        f'下面是按日期倒序的全部记录（下架的多为版权风险或低人气项目，改名的是作者换了仓库地址）。</div>\n'
        + "".join(parts)
        + f'<nav class="sub" style="margin-top:24px"><a href="../">回首页</a>'
          f'<a href="../c/">📚 专题合辑</a><a href="../weekly/">📮 每周精选</a></nav>'
    )

    os.makedirs(OUT_DIR, exist_ok=True)
    # 供首页读取的轻量数据（更新状态条 + 最近上新）
    upd = {
        "generated": events[-1]["date"] if events else "",
        "latest": events[-1]["date"] if events else "",
        "total_added": total_added,
        "total_now": total,
        "events": [
            {"date": e["date"], "subject": e["subject"], "added": e["added"],
             "removed": e["removed"], "renames": e["renames"]}
            for e in reversed(events)  # 新的在前
        ],
    }
    with open(os.path.join(ROOT, "updates.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(upd, f, ensure_ascii=False, separators=(",", ":"))

    html = (
        '<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        "<title>更新记录 - GitHub 中文发现器</title>\n"
        '<meta name="description" content="GitHub 中文发现器的收录时间线：哪天新增了哪些项目、下架了哪些、哪些仓库改了名。">\n'
        f'<link rel="canonical" href="{bp.BASE_URL}/timeline/">\n'
        f'<link rel="icon" href="{bp.BASE_URL}/icon.svg" type="image/svg+xml">\n'
        '<meta name="theme-color" content="#0d1117">\n'
        f"<style>\n{bp.PAGE_CSS}{EXTRA_CSS}\n</style>\n</head>\n<body>\n"
        '<header class="site-head"><span class="logo">🧭 GitHub 中文发现器</span>'
        f'<a class="back" href="{bp.BASE_URL}/">← 返回首页</a></header>\n'
        f'<main class="container">\n{body}\n</main>\n</body>\n</html>\n'
    )
    with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    print(f"✅ 更新记录：{len(events)} 次更新 / 累计新增 {total_added} / 当前 {total} 个项目")


if __name__ == "__main__":
    main()
