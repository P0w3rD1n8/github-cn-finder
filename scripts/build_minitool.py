#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重建小工具离线数据并打包。

用法：
    python scripts/build_minitool.py                    # 默认：速查工具
    python scripts/build_minitool.py --app finder       # 发现器小工具
    python scripts/build_minitool.py --check            # 只比对，不写文件
    python scripts/build_minitool.py --version 1.2.0    # 指定版本号（默认按现有 zip 自动 +1）

数据来源：
    data.js     —— 项目名 / 中文说明 / 语言 / 分类 / 用途标签 / 四段详情（人工维护）
    repos.json  —— star / fork / issue / 最近推送日 / 24 期星标历史（每日自动更新）
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT = os.path.join(ROOT, ".skill", "minitool-zip-builder", "scripts", "audit_artifact.py")
FILES = ["index.html", "app.css", "app.js", "tool-data.js"]

APPS = {
    "checker": {"dir": "minitool", "prefix": "开源项目速查"},
    "finder": {"dir": "minitool-finder", "prefix": "GitHub中文发现器"},
}


def app_dir(app: str) -> str:
    return os.path.join(ROOT, APPS[app]["dir"])


def read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def js_block(js: str, name: str) -> str:
    i = js.index("const " + name)
    j = js.index("\n};", i)
    return js[i:j]


def parse_source() -> list[list]:
    js = read(os.path.join(ROOT, "data.js"))
    repos_meta = json.loads(read(os.path.join(ROOT, "repos.json")))["repos"]

    repos = []
    for m in re.finditer(
        r'\{n:"([^"]+)",d:"((?:[^"\\]|\\.)*)",s:(\d+),l:"([^"]*)",c:"([^"]+)"\}',
        js[js.index("const REPOS"): js.index("\n};", js.index("const REPOS"))],
    ):
        repos.append({
            "name": m.group(1),
            "desc": json.loads('"' + m.group(2) + '"'),
            "stars": int(m.group(3)),
            "lang": m.group(4),
            "cat": m.group(5),
        })

    usage = {m.group(1): re.findall(r'"([^"]+)"', m.group(2))
             for m in re.finditer(r'"([^"]+)"\s*:\s*\[([^\]]*)\]', js_block(js, "USAGE"))}

    detail = {}
    for m in re.finditer(r'"([^"]+)"\s*:\s*"((?:[^"\\]|\\.)*)"', js_block(js, "DETAIL")):
        detail[m.group(1)] = json.loads('"' + m.group(2) + '"')

    zh = {}
    for m in re.finditer(r'"([^"]+)"\s*:\s*"((?:[^"\\]|\\.)*)"', js_block(js, "REPO_ZH")):
        zh[m.group(1)] = json.loads('"' + m.group(2) + '"')

    rows = []
    for r in repos:
        meta = repos_meta.get(r["name"], {})
        hist = meta.get("hist") or []
        stars = meta.get("ps") or meta.get("s") or r["stars"]
        growth = round((stars - hist[0]) / hist[0] * 100, 1) if len(hist) >= 2 and hist[0] else 0.0
        rows.append([
            r["name"], r["desc"], stars, r["lang"] or meta.get("lg", ""), r["cat"],
            meta.get("pa", ""), growth, meta.get("fk", 0), meta.get("iu", 0),
            1 if meta.get("ar") else 0,
            usage.get(r["name"], []),
            detail.get(r["name"], ""),
            zh.get(r["name"], ""),
        ])
    rows.sort(key=lambda x: -x[2])
    return rows


def render(rows: list[list]) -> str:
    out = [
        "/* 离线数据集：开源项目速查 · 数据截至 " + max(r[5] for r in rows if r[5]),
        " * 字段: [仓库名, 中文说明, star, 语言, 分类, 最近推送日, 24期涨幅%, fork, 未解决issue, 是否归档, 用途标签, 四段详情, 中文名]",
        " * 由 scripts/build_minitool.py 生成，不要手改。 */",
        "var TOOL_DATA = [",
    ]
    out += ["  " + json.dumps(r, ensure_ascii=False) + "," for r in rows]
    out[-1] = out[-1][:-1]
    out.append("];")
    return "\n".join(out) + "\n"


def latest_version(prefix: str) -> str:
    best = None
    for name in os.listdir(ROOT):
        m = re.fullmatch(re.escape(prefix) + r"-v(\d+)\.(\d+)\.(\d+)\.zip", name)
        if not m:
            continue
        key = tuple(int(x) for x in m.groups())
        if best is None or key > best:
            best = key
    return ".".join(map(str, best)) if best else "1.0.0"


def bump(version: str) -> str:
    major, minor, patch = (int(x) for x in version.split("."))
    return f"{major}.{minor}.{patch + 1}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--app", choices=sorted(APPS), default="checker")
    ap.add_argument("--check", action="store_true", help="只比对，不写文件")
    ap.add_argument("--version", help="版本号，如 1.2.0；默认在最新 zip 上 +1")
    args = ap.parse_args()

    src = app_dir(args.app)
    if not os.path.isdir(src):
        print(f"找不到小工具目录: {src}")
        return 1
    tool_data = os.path.join(src, "tool-data.js")

    rows = parse_source()
    text = render(rows)

    missing = {k: [r[0] for r in rows if not r[i]]
               for k, i in (("用途标签", 10), ("四段详情", 11), ("推送日", 5))}
    print(f"[{args.app}] 项目数: {len(rows)} | " +
          " | ".join(f"无{k}: {len(v)}" for k, v in missing.items()))
    for k, names in missing.items():
        if names:
            print(f"  ! 缺{k}: " + ", ".join(names[:8]) + (" …" if len(names) > 8 else ""))

    if args.check:
        old = read(tool_data) if os.path.exists(tool_data) else ""
        print("与现有 tool-data.js 一致" if old == text else "与现有 tool-data.js 不同（去掉 --check 可重建）")
        return 0

    # 两个小工具共用同一份数据：都写入
    for app, meta in APPS.items():
        target_dir = os.path.join(ROOT, meta["dir"])
        if not os.path.isdir(target_dir):
            continue
        with open(os.path.join(target_dir, "tool-data.js"), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    print(f"已写入 {args.app}/tool-data.js（{os.path.getsize(tool_data)} 字节）")

    version = args.version or bump(latest_version(APPS[args.app]["prefix"]))
    zip_path = os.path.join(ROOT, f"{APPS[args.app]['prefix']}-v{version}.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for name in FILES:
            z.write(os.path.join(src, name), name)
    print(f"已打包 {os.path.basename(zip_path)}（{os.path.getsize(zip_path)} 字节）")

    if os.path.exists(AUDIT):
        rc = subprocess.call([sys.executable, AUDIT, zip_path])
        if rc != 0:
            print("审计未通过，请修复后再上传")
            return rc
    else:
        print("未找到审计脚本，请手动核对包体与自检清单")
    return 0


if __name__ == "__main__":
    sys.exit(main())
