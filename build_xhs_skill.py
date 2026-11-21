#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成小红书 Red Skill 用的项目目录 + 打包 zip（v1.39.0）。

产出：
  content/xhs-skill/references/catalog.md   —— 按用途分类的项目目录（供选型助手推荐替代方案）
  content/xhs-skill.zip                     —— 可直接上传到创作服务平台的文件

合规：目录里**只有项目名、仓库路径、一句话说明**，不含任何网址 ——
小红书对站外链接判定很严（手册 §5.7 有 11/15 被判违规的记录）。

用法：python build_xhs_skill.py
"""
import io
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data.js")
SKILL_DIR = os.path.join(ROOT, "content", "xhs-skill")
OUT_MD = os.path.join(SKILL_DIR, "references", "catalog.md")
OUT_ZIP = os.path.join(ROOT, "content", "xhs-skill.zip")

CAT_ORDER = ["实用工具", "AI 人工智能", "影音与直播", "手机 App",
             "学编程", "开发者工具", "网页界面", "后台服务", "游戏娱乐"]
CAT_DESC = {
    "实用工具": "装机、文件处理、系统辅助",
    "AI 人工智能": "本地模型、AI 绘画、智能体",
    "影音与直播": "播放器、录制、剪辑、转码",
    "手机 App": "安卓应用、手机工具",
    "学编程": "教程、路线图、算法",
    "开发者工具": "编辑器、命令行、开发辅助",
    "网页界面": "前端框架、组件库",
    "后台服务": "自托管服务、服务端框架",
    "游戏娱乐": "开源游戏、游戏工具",
}


def load():
    src = io.open(DATA, encoding="utf-8").read()
    block = re.search(r"const REPOS = \[(.*?)\n\];", src, re.S).group(1)
    items = re.findall(r'\{n:"([^"]+)",d:"([^"]*)",s:(\d+),l:"([^"]*)",c:"([^"]*)"\}', block)

    def grabmap(name):
        m = re.search(r"const %s = \{(.*?)\n\};" % name, src, re.S)
        return dict(re.findall(r'"([^"]+)"\s*:\s*"([^"]*)"', m.group(1))) if m else {}

    return items, grabmap("REPO_ZH"), grabmap("CN_DESC")


def main():
    items, zh, cndesc = load()
    by_cat = {}
    for n, d, s, l, c in items:
        by_cat.setdefault(c, []).append((int(s), n, d))

    out = []
    w = out.append
    w("# 开源项目中文目录")
    w("")
    w(f"共 **{len(items)}** 个开源项目，每个都有中文说明。按用途分类，可用于给用户推荐替代方案。")
    w("")
    w("> 推荐时用法：先说「你要的功能属于哪一类」，再从对应分类里挑 2-3 个名字相符的项目；")
    w("> 如果这一类里没有合适的，直接说「暂无可替代」，不要硬凑。")
    w(">")
    w("> 名字后面的 `（owner/repo）` 是它在 GitHub 上的唯一标识，用户可据此自行搜索。")
    w("")

    for cat in CAT_ORDER:
        rows = by_cat.get(cat)
        if not rows:
            continue
        rows.sort(reverse=True)
        w(f"## {cat}（{len(rows)} 个）")
        w("")
        w(f"*{CAT_DESC.get(cat, '')}*")
        w("")
        for s, n, d in rows:
            label = zh.get(n) or n.split("/")[1]
            desc = (cndesc.get(n) or d or "").strip()
            w(f"- **{label}**（{n}）—— {desc}")
        w("")

    # 其余分类兜底
    for cat, rows in by_cat.items():
        if cat in CAT_ORDER:
            continue
        rows.sort(reverse=True)
        w(f"## {cat}（{len(rows)} 个）")
        w("")
        for s, n, d in rows:
            label = zh.get(n) or n.split("/")[1]
            desc = (cndesc.get(n) or d or "").strip()
            w(f"- **{label}**（{n}）—— {desc}")
        w("")

    text = "\n".join(out).rstrip() + "\n"
    os.makedirs(os.path.dirname(OUT_MD), exist_ok=True)
    io.open(OUT_MD, "w", encoding="utf-8", newline="\n").write(text)
    print(f"✅ 目录已生成：{OUT_MD}")
    print(f"   项目 {len(items)} 个 / 分类 {len(by_cat)} 个 / {len(text)} 字符")

    # 打包（平台限制：单文件 10MB，总计 30MB）
    def make_zip(out_path, skip_catalog=False):
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
            for dirpath, _, files in os.walk(SKILL_DIR):
                for f in sorted(files):
                    if skip_catalog and f == "catalog.md":
                        continue
                    full = os.path.join(dirpath, f)
                    rel = os.path.relpath(full, os.path.dirname(SKILL_DIR))
                    z.write(full, rel.replace(os.sep, "/"))
        return os.path.getsize(out_path)

    full_size = make_zip(OUT_ZIP)
    print(f"✅ 完整版：{OUT_ZIP}（{full_size / 1024:.1f} KB，含 catalog）")

    # 安全版：去掉 catalog.md。
    # 原因：catalog 里有 172 条 owner/repo 项目标识，还包含影视下载、去广告这类项目，
    # 被平台判「外部平台信息」的风险最高。审核不通过时先摘掉它排查。
    safe_path = os.path.join(ROOT, "content", "xhs-skill-safe.zip")
    safe_size = make_zip(safe_path, skip_catalog=True)
    print(f"✅ 安全版：{safe_path}（{safe_size / 1024:.1f} KB，无 catalog）")

    if max(full_size, safe_size) > 30 * 1024 * 1024:
        print("⚠️ 超过平台 30MB 限制")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
