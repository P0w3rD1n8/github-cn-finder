#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 Gitee 仓库用的 README 目录页（v1.36.0）。

背景：百度不收录 github.io，但收录 gitee.com 很好。在 Gitee 建一个仓库、把本文件
当成 README 贴进去，等于在百度有收录的域名下放了一个 172 条目的中文目录，
持续累积权重——不是一次性文章。

用法：python build_gitee_readme.py   →  输出 content/gitee-README.md
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data.js")
OUT = os.path.join(ROOT, "content", "gitee-README.md")

SITE = "https://p0w3rd1n8.github.io/github-cn-finder/"
REPO = "https://github.com/P0w3rd1n8/github-cn-finder"

CAT_ORDER = ["AI 人工智能", "实用工具", "开发者工具", "影音与直播",
             "手机 App", "学编程", "游戏娱乐", "网页界面", "后台服务"]
CAT_EMOJI = {"AI 人工智能": "🤖", "实用工具": "🛠", "开发者工具": "🧰", "影音与直播": "🎬",
             "手机 App": "📱", "学编程": "📚", "游戏娱乐": "🎮", "网页界面": "🎨",
             "后台服务": "⚙️"}


def load_data():
    src = open(DATA, encoding="utf-8").read()
    block = re.search(r"const REPOS = \[(.*?)\n\];", src, re.S).group(1)
    items = re.findall(r'\{n:"([^"]+)",d:"([^"]*)",s:(\d+),l:"([^"]*)",c:"([^"]*)"\}', block)

    def grabmap(name):
        m = re.search(r"const %s = \{(.*?)\n\};" % name, src, re.S)
        return dict(re.findall(r'"([^"]+)"\s*:\s*"([^"]*)"', m.group(1))) if m else {}

    return items, grabmap("REPO_ZH"), grabmap("CN_DESC")


def fmt_star(n):
    if n >= 10000:
        return f"{n / 10000:.1f} 万"
    return f"{n:,}"


def esc_pipe(s):
    return s.replace("|", "\\|").replace("\n", " ")


def main():
    items, zh, cndesc = load_data()
    total = len(items)
    by_cat = {}
    for n, d, s, l, c in items:
        by_cat.setdefault(c, []).append((int(s), n, d))

    out = []
    w = out.append

    w(f"# GitHub 中文发现器 · {total} 个开源项目中文索引\n")
    w("> 不懂英文，也能用好 GitHub。\n")
    w("一个给中文用户看的开源项目导航：每个项目都配了**中文四段说明**"
      "（应用场景 / 主要功能 / 适用平台 / 怎么用起来），并标注了最容易踩的坑。\n")
    w(f"- 🌐 **在线站点（可用手机打开）**：[{SITE}]({SITE})")
    w(f"- 📮 **每周精选（可 RSS 订阅）**：[{SITE}feed.xml]({SITE}feed.xml)")
    w(f"- 💻 **本项目源码**：[{REPO}]({REPO})")
    w(f"- 📊 当前收录：**{total} 个项目**，数据每小时自动同步 GitHub 真实 star\n")
    w("---\n")

    w("## 为什么会有这个项目\n")
    w("普通人打开 GitHub 想找个软件用，会连撞三堵墙：\n")
    w("1. **英文**——README 是英文，安装说明是英文，连报错都是英文；")
    w("2. **不知道下哪个**——一个项目十几个 Release 文件，没人告诉小白该点哪个；")
    w("3. **坑**——装完才发现要开命令行、装 Python、注册账号，大部分人直接关掉。\n")
    w("所以这里把每个项目都翻译成了大白话，并写清楚**它到底能不能装、装完会踩什么坑**。\n")
    w("---\n")

    w("## 分类目录\n")
    for c in CAT_ORDER:
        if c in by_cat:
            w(f"- {CAT_EMOJI.get(c, '·')} {c}（{len(by_cat[c])} 个）")
    w("")
    w("---\n")

    for c in CAT_ORDER:
        rows = by_cat.get(c)
        if not rows:
            continue
        rows.sort(reverse=True)
        w(f"## {CAT_EMOJI.get(c, '')} {c}（{len(rows)} 个）\n")
        w("| 项目 | 中文说明 | Star |")
        w("|---|---|---|")
        for s, n, d in rows:
            label = zh.get(n, n)
            desc = cndesc.get(n) or d
            w(f"| [{esc_pipe(label)}](https://github.com/{n}) | {esc_pipe(desc)} | {fmt_star(s)} |")
        w("")

    w("---\n")
    w("## 附：怎么判断一个 GitHub 项目靠不靠谱\n")
    w("高星不等于能用。下面四条能挡掉大部分坑（写内容时用得上）：\n")
    w("1. **看 fork 和 star 的比例**：正常 5%~10%；超过 30%、或 fork 比 star 还多，很可能是刷的。")
    w("2. **看最后提交时间**：仓库首页右上角的 last commit，超过一年没动基本当弃坑处理。")
    w("3. **看 open issue 和 star 的比例**：几千个 open issue 只配几万 star，说明作者处理不过来。")
    w("4. **看有没有能直接装的东西**：Release 里有 `.exe` / `.dmg` / `.apk` 才算考虑过普通用户。\n")
    w("---\n")
    w(f"*本页由脚本从项目数据自动生成，star 数为生成时的快照，实时值请看[在线站点]({SITE})。*")
    w("*项目中文介绍为人工整理，可能存在偏差；安装任何项目前请以官方文档为准。*\n")

    text = "\n".join(out).rstrip() + "\n"
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(text)

    n_cat = sum(1 for c in CAT_ORDER if c in by_cat)
    print(f"✅ 已生成 {OUT}")
    print(f"   项目 {total} 个 / 分类 {n_cat} 个 / 约 {len(text)} 字符")
    return 0


if __name__ == "__main__":
    sys.exit(main())
