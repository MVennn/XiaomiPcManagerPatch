#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 本仓分叉变体；上游参考：ClientTriage/tools/check-secrets.py（2026-11-01 bug 奇偶同步）
"""公开仓敏感信息扫描：凭据 + 本机路径 + 内网 IP + 真实邮箱。

用法：
    python tools/check-secrets.py            # 扫描已跟踪文件
    python tools/check-secrets.py --all      # 已跟踪 + 未跟踪一起扫（遵循 .gitignore）

退出码：0 通过 / 1 发现疑似敏感信息 / 2 自身故障（git 不可用或失败）。
本仓红线：安装日志（pcc_install_log.txt 等，见 .gitignore）不入库；正文不出现
本机用户目录、内网 IP、真实邮箱与任何凭据 —— 首个 commit 就是对外可见的起点，
提交前后各扫一遍。

比通用守卫多两条规则，都是本仓真实踩过的坑：
  - 本机用户目录（盘符开头、Users 下的真实目录）：脚本与 README 曾硬编码真实用户路径。
  - 内网 IP：README 曾带对照机的 SSH 地址。
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Windows 控制台默认 GBK，✓/✗ 等字符会直接炸 —— 统一按 UTF-8 输出
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SKIP_DIRS = {".codegraph", ".git", ".work", "__pycache__", "dist",
             "node_modules", "third-party", "venv", "vault"}
SKIP_EXT = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".gz", ".pyc", ".woff", ".woff2",
            ".zip", ".mrs"}

# 占位符与示例行不算命中
PLACEHOLDER = re.compile(
    r"REDACTED|YOUR-|REPLACE-|<[^>]+>|example\.(com|org|net)|placeholder|<用户名>", re.I)

PATTERNS = [
    ("私钥块", re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("GitHub PAT", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{22,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Anthropic key", re.compile(r"\bsk-ant-[A-Za-z0-9\-_]{10,}\b")),
    ("通用 sk- token", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("OpenCode key", re.compile(r"\boc_sk_[A-Za-z0-9]{10,}\b")),
    ("Gemini key", re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b")),
    ("GitLab PAT", re.compile(r"\bglpat-[A-Za-z0-9\-_]{20,}\b")),
    ("shadow 哈希", re.compile(r"\$[1256][aby]?\$[./A-Za-z0-9]{8,}")),
    ("代理节点 URI", re.compile(
        r"\b(?:vmess|vless|trojan|hysteria2?)://[A-Za-z0-9+/=_%.:@?&~-]{20,}", re.I)),
    ("订阅 token", re.compile(
        r"https?://[^\s'\"<>]+(?:token|subscribe|subscription)=[A-Za-z0-9._~-]{8,}", re.I)),
    # 本机用户目录：Windows 正斜杠与反斜杠两种写法
    ("本机用户目录", re.compile(r"[A-Za-z]:[\\/]Users[\\/][A-Za-z0-9._-]+")),
    # 内网 IP：10.x / 192.168.x / 172.16-31.x（README 曾带对照机的 SSH 地址）
    ("内网 IP", re.compile(
        r"\b(?:10\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3})\.\d{1,3}\b")),
    # 真实邮箱域名（GitHub noreply 不含这些域名，不会误伤）
    ("真实邮箱", re.compile(
        r"\b[A-Za-z0-9._%+-]+@(?:qq|163|126|gmail|outlook|hotmail|foxmail|sina|sohu)\.com\b")),
]

# 变更说明里引用泄漏原文是必要的（否则读者不知道该改什么），但真值仍要遮掉。
# 用户名位置被 `...` / `<...>` 取代，或用户名后紧跟 `\...` 截断的写法，视为已脱敏的
# 描述性引用，放行；完整路径一律不放行。只对文档类文件生效。
DOC_FILES = ("CHANGELOG.md", "PROGRESS.md", "SECURITY.md", "CONTRIBUTING.md")
DOC_PREFIXES = ("docs/", "evidence/")
# 描述性引用：用户名被 `...` / `<...>` 取代，或用户名后紧跟 `\...` 截断
TRUNCATED_PATH = re.compile(
    r"[A-Za-z]:[\\/]Users[\\/](?:\.\.\.|<[^>]+>|[A-Za-z0-9._-]+\\\.\.\.)")


# 占位用户名：示例文件里的 C:/Users/You/... 是给用户照着改的模板，不是本机路径。
# 反斜杠写法同样要认；旧正则只认正斜杠，且 Your 后内嵌的字面 0x08（本意 \b）随此重写移除。
PLACEHOLDER_USER = re.compile(
    r"[A-Za-z]:[\\/]Users[\\/](?:You|User|<[^>]+>|[^\\/\s<>]*[一-鿿])", re.I)


def is_doc_file(rel: str) -> bool:
    base = rel.replace("\\", "/")
    if base in DOC_FILES or base.startswith(DOC_PREFIXES):
        return True
    return base.split("/")[-1] in DOC_FILES


def tracked_files() -> list[str]:
    try:
        out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True)
    except FileNotFoundError:
        print("✗ 找不到 git 命令")
        raise SystemExit(2)
    if out.returncode != 0:
        print("✗ git ls-files 失败：" + (out.stderr or "").strip())
        raise SystemExit(2)
    return [x for x in out.stdout.splitlines() if x.strip()]


def untracked_files() -> list[str]:
    # --all 的「未跟踪」遵循 .gitignore：忽略规则交给 git 判定，
    # gitignore 排除的本地文件（安装日志等）不进扫描。
    out = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=ROOT, capture_output=True, text=True)
    if out.returncode != 0:
        print("✗ git ls-files --others 失败：" + (out.stderr or "").strip())
        raise SystemExit(2)
    return [x for x in out.stdout.splitlines() if x.strip()]


def main() -> int:
    if "--all" in sys.argv:
        files = sorted(set(tracked_files()) | set(untracked_files()))
    else:
        files = tracked_files()
    bad = []
    for rel in files:
        if os.path.splitext(rel)[1].lower() in SKIP_EXT:
            continue
        parts = rel.replace("\\", "/").split("/")
        if any(p in SKIP_DIRS for p in parts[:-1]):
            continue
        # 文档类文件允许描述性引用泄漏原文，但必须是截断形式（`...\` 之后无层级）
        allow_truncated = is_doc_file(rel)
        try:
            with open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace") as fh:
                for lineno, line in enumerate(fh, 1):
                    for name, pat in PATTERNS:
                        # finditer：一行里每个命中段都单独过豁免，不整行放行 ——
                        # search 只看首个命中，同一行里第二个真值路径会漏。
                        for m in pat.finditer(line):
                            # 占位符只豁免它自己所在的那一段，不再整行放行 ——
                            # 示例与真值写在同一行时，真值仍会被报出来。
                            if PLACEHOLDER.search(m.group(0)):
                                continue
                            if name == "本机用户目录":
                                # 只豁免命中片段本身：截断形式（C:/Users/<用户名>\...）或
                                # 占位用户名（C:/Users/You）。同一行里并排写下的
                                # 完整真实路径仍会被报出来。
                                frag = line[m.start():m.start() + 120]
                                if allow_truncated and TRUNCATED_PATH.match(frag):
                                    continue
                                if PLACEHOLDER_USER.match(frag):
                                    continue
                            bad.append((rel, lineno, name, line.strip()[:120]))
        except OSError:
            continue

    if bad:
        print(f"✗ 发现 {len(bad)} 处疑似敏感信息：")
        for rel, lineno, name, text in bad:
            print(f"   {rel}:{lineno}  [{name}]  {text}")
        print()
        print("   处理方式：凭据换成环境变量占位符；本机路径只留文件名；")
        print("   内网 IP 泛化成「内网里的对照机」一类表述；邮箱改成 <账号>。")
        return 1

    print(f"✓ 已扫描 {len(files)} 个文件，未发现疑似敏感信息")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
