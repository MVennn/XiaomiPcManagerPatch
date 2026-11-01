#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
平板镜像（padshare.coop.dropToPad）“已连接其他显示设备” 补丁

背景
----
MiSmartShareDLL.dll 在 dropToPad 前会统计本机显示设备数量，
返回值 > 1 就直接回 exception=1，App 映射成
“已连接其他显示设备，请断开其他显示设备后重试。”
双显示器 / 多显卡的机器因此永远无法镜像到平板。

补丁
----
把该判断的 `jle`（7E）改成无条件 `jmp`（EB），只影响 dropToPad 这一条路径，
不改动显示器数量统计函数本身（其它功能仍按真实数量工作）。

特征码（对 6.0.0.39 唯一）：
  E8 ?? ?? ?? ??        call  <统计显示设备数>
  83 F8 01              cmp   eax, 1
  7E ??                 jle   <继续>
  49 8B 06              mov   rax, [r14]
  4C 8B C6              mov   r8, rsi
  BA 01 00 00 00        mov   edx, 1        ; exception = 1
  FF 50 A0              call  [rax+0xa0]     ; 发布 exceptionToast

用法
----
  python padgate_patch.py apply     # 打补丁（会自动结束占用进程）
  python padgate_patch.py status    # 查看状态
  python padgate_patch.py restore   # 从 .bak-padgate 回退
"""

import os
import re
import shutil
import subprocess
import sys

ROOT = r"C:\Program Files\MI\XiaomiPCManager"
BACKUP_SUFFIX = ".bak-padgate"

# call rel32 + cmp eax,1 + jle + 后续固定指令
ORIG = re.compile(
    rb"\xe8....\x83\xf8\x01\x7e.\x49\x8b\x06\x4c\x8b\xc6\xba\x01\x00\x00\x00", re.S
)
PATCHED = re.compile(
    rb"\xe8....\x83\xf8\x01\xeb.\x49\x8b\x06\x4c\x8b\xc6\xba\x01\x00\x00\x00", re.S
)

# 显卡描述字符串里含 "NVIDIA" 时直接回 exception=3（App 提示去改 NVIDIA 控制面板）。
# testb r15b,r15b; je ...; mov (%r14),rax; mov rsi,r8; mov $3,edx; mov r14,rcx; call *0xa0(rax)
ORIG_NV = re.compile(
    rb"\x45\x84\xff\x74.\x49\x8b\x06\x4c\x8b\xc6\xba\x03\x00\x00\x00"
    rb"\x49\x8b\xce\xff\x90\xa0\x00\x00\x00", re.S
)
PATCHED_NV = re.compile(
    rb"\x45\x84\xff\xeb.\x49\x8b\x06\x4c\x8b\xc6\xba\x03\x00\x00\x00"
    rb"\x49\x8b\xce\xff\x90\xa0\x00\x00\x00", re.S
)

# name, 原特征, 已补特征, 要改的字节相对偏移, 原值, 新值
PATCHES = [
    ("display-gate", ORIG, PATCHED, 8, 0x7E, 0xEB),
    ("nvidia-gate", ORIG_NV, PATCHED_NV, 3, 0x74, 0xEB),
]


def find_dll():
    if not os.path.isdir(ROOT):
        return None
    versions = [
        d for d in os.listdir(ROOT)
        if re.match(r"^\d+(\.\d+)+$", d) and os.path.isdir(os.path.join(ROOT, d))
    ]
    versions.sort(key=lambda s: [int(x) for x in s.split(".")], reverse=True)
    for v in versions:
        p = os.path.join(ROOT, v, "MiSmartShare", "MiSmartShareDLL.dll")
        if os.path.exists(p):
            return p
    return None


def stop_holders():
    for exe in ("XiaomiPCManager.exe", "MiSmartShareHost.exe", "MiScreenShare.exe"):
        subprocess.run(["taskkill", "/F", "/IM", exe],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def status(path):
    data = open(path, "rb").read()
    parts = []
    for name, orig, patched, *_ in PATCHES:
        o, p = len(orig.findall(data)), len(patched.findall(data))
        if p and not o:
            st = "patched"
        elif o and not p:
            st = "original"
        elif o and p:
            st = "mixed"
        else:
            st = "not-found"
        parts.append("%s=%s" % (name, st))
    return ", ".join(parts)


def apply_patch(path):
    data = bytearray(open(path, "rb").read())
    changed = 0
    for name, orig, patched, delta, old, new in PATCHES:
        hits = list(orig.finditer(data))
        if not hits:
            if patched.search(data):
                print("[%s] 已是补丁状态，跳过" % name)
            else:
                print("[%s] 未找到特征码（版本可能变化），跳过" % name)
            continue
        if len(hits) > 1:
            print("[%s] 特征码命中 %d 处，出于安全考虑不自动修改" % (name, len(hits)))
            continue
        off = hits[0].start() + delta
        if data[off] != old:
            print("[%s] 偏移校验失败（0x%02X != 0x%02X），跳过" % (name, data[off], old))
            continue
        data[off] = new
        changed += 1
        print("[%s] 已修改 offset 0x%X" % (name, off))

    if not changed:
        print("没有需要修改的内容")
        return 0

    bak = path + BACKUP_SUFFIX
    if not os.path.exists(bak):
        shutil.copy2(path, bak)
        print("已备份 -> %s" % bak)
    stop_holders()
    try:
        with open(path, "wb") as f:
            f.write(data)
    except PermissionError:
        print("写入失败：文件被占用。请先退出小米电脑管家后重试（或以管理员身份运行）")
        return 4
    print("已写入：%s" % path)
    return 0


def restore(path):
    bak = path + BACKUP_SUFFIX
    if not os.path.exists(bak):
        print("找不到备份：%s" % bak)
        return 2
    stop_holders()
    try:
        shutil.copy2(bak, path)
    except PermissionError:
        print("写入失败：文件被占用。请先退出小米电脑管家后重试（或以管理员身份运行）")
        return 4
    print("已回退：%s" % path)
    return 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    path = find_dll()
    if not path:
        print("找不到 MiSmartShareDLL.dll（未安装？）")
        return 1
    print("目标：%s" % path)
    if cmd == "status":
        print("状态：%s" % status(path))
        return 0
    if cmd == "apply":
        return apply_patch(path)
    if cmd == "restore":
        return restore(path)
    print("用法：python padgate_patch.py [apply|status|restore]")
    return 1


if __name__ == "__main__":
    sys.exit(main())
