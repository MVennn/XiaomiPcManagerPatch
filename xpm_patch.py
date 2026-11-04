#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小米电脑管家（非小米电脑）通用补丁工具

原理
----
安装包内嵌一段明文 JSON 清单（以 "TS\\0\\0" 头 + 4 字节长度 + JSON 的形式存放），
其中的 support_tm_list / support_nfc_list / support_distfile_list 是允许安装的机型白名单。
安装器会读 WMI 的机型，若不在白名单里就拒绝安装。

本工具不修改程序代码，只把本机真实型号插入这几个数组，并用空格填充，
保证 JSON 的字节长度完全不变，因此包内其它偏移/结构不受影响。

运行时功能开关
--------------
程序把上报给手机的机型取自注册表值 dummy_pc_model（MiScreenShare 读取）。
把它设成清单里支持的某个机型代码（例如 TM2424），即可让手机/平板把这些
"小米特色功能"当作受支持的机型放行。

用法
----
  python xpm_patch.py patch-installer "<安装包.exe>" [-o "<输出.exe>"]
  python xpm_patch.py patch-installed
  python xpm_patch.py set-model ["TM2424"]
"""

import argparse
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import winreg

LISTS = ["support_tm_list", "support_nfc_list", "support_distfile_list"]
DEFAULT_INSTALL_ROOT = r"C:\Program Files\MI\XiaomiPCManager"
SPOOF_FALLBACK = "TM2424"
REG_SUBKEYS = [
    r"SOFTWARE\Timi Personal Computing\MiScreenShare",
    r"SOFTWARE\MI\MiScreenShare",
]


# ---------------------------------------------------------------- manifest

def find_manifests(data):
    """返回 [(offset, length, text, obj)]，自动跳过非清单的 "companyName"。"""
    found = []
    start = 0
    while True:
        i = data.find(b'"companyName"', start)
        if i < 0:
            break
        start = i + 1
        j = data.rfind(b'{', 0, i)
        if j < 32:
            continue
        jlen = struct.unpack_from("<I", data, j - 4)[0]
        if jlen < 1024 or j + jlen > len(data):
            continue
        raw = data[j:j + jlen]
        try:
            text = raw.decode("utf-8")
            obj = json.loads(text)
        except Exception:
            continue
        if isinstance(obj, dict) and "companyName" in obj:
            found.append((j, jlen, text, obj))
    return found


def _patch_arrays_bytes(raw, obj, models):
    """优先在数组内部原地替换并补空格，保持总字节数不变。"""
    b = raw
    for key in LISTS:
        if key not in obj or not isinstance(obj[key], list):
            continue
        kb = ('"' + key + '"').encode()
        ki = b.find(kb)
        if ki < 0:
            return None
        lb = b.find(b"[", ki)
        rb = b.find(b"]", lb)
        if lb < 0 or rb < 0:
            return None
        inner = b[lb + 1:rb]
        keep = list(obj[key])
        for m in models:
            if m not in keep:
                keep.append(m)
        items = ", ".join(json.dumps(x, ensure_ascii=False) for x in keep).encode("utf-8")
        if len(items) > len(inner):
            return None
        b = b[:lb + 1] + items + b" " * (len(inner) - len(items)) + b[rb:]
    return b


def choose_spoof_model(candidates, real_models):
    """从白名单里挑一个受支持的机型代码（优先 TMxxxx），排除本机真实型号。"""
    blacklist = {
        "DEFAULT STRING", "SYSTEM PRODUCT NAME", "TO BE FILLED BY O.E.M.",
        "TO BE FILLED BY OEM", "NONE", "UNKNOWN", "NOT SPECIFIED", "OEM",
    }
    real = {str(m).strip().upper() for m in real_models} | blacklist
    pool = []
    for m in candidates or []:
        s = str(m).strip()
        if not s or s.upper() in real:
            continue
        pool.append(s)
    for s in pool:
        if re.fullmatch(r"TM\d{3,6}", s, re.I):
            return s
    for s in pool:
        if re.match(r"^(MI|Xiaomi|Redmi|XiaoMi)", s, re.I):
            return s
    return SPOOF_FALLBACK


def patch_manifest_bytes(raw, models):
    text = raw.decode("utf-8")
    obj = json.loads(text)
    if not isinstance(obj, dict):
        raise ValueError("manifest is not a JSON object")

    tm = obj.get("support_tm_list")
    spoof = choose_spoof_model(tm if isinstance(tm, list) else [], models)

    new = _patch_arrays_bytes(raw, obj, models)
    if new is None:
        # 数组里空间不够：紧凑重排后整体补齐
        for key in LISTS:
            if isinstance(obj.get(key), list):
                for m in models:
                    if m not in obj[key]:
                        obj[key].append(m)
        compact = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if len(compact) > len(raw):
            raise ValueError("compact manifest does not fit; refuse to patch")
        new = compact + b" " * (len(raw) - len(compact))

    if len(new) != len(raw):
        raise ValueError("patched length mismatch: %d != %d" % (len(new), len(raw)))
    json.loads(new.decode("utf-8"))  # final sanity check
    return new, spoof


def patch_file_manifest(path, models, out_path=None):
    data = open(path, "rb").read()
    menus = find_manifests(data)
    if not menus:
        raise SystemExit("未在 %s 中找到内嵌清单（可能不是小米电脑管家安装包）" % path)
    # 选最像安装清单的那个（通常只有一个，且包含 support_tm_list）
    menus.sort(key=lambda x: (0 if isinstance(x[3].get("support_tm_list"), list) else 1, -x[1]))
    off, jlen, text, obj = menus[0]
    print("清单位置: 0x%x, 长度: %d" % (off, jlen))
    print("原白名单: %s" % (obj.get("support_tm_list")))
    new_bytes, spoof = patch_manifest_bytes(data[off:off + jlen], models)

    same_target = (not out_path) or \
        os.path.abspath(out_path) == os.path.abspath(path)
    if same_target:
        # 原地写回：必须先留一份原始备份，写入中断/失败才有回滚依据
        # （patch_installed 调用前已备份过同名 .bak，这里会自动跳过）
        bak = path + ".bak"
        if not os.path.exists(bak):
            shutil.copyfile(path, bak)
            print("已备份: %s" % bak)
        with open(path, "r+b") as f:
            f.seek(off)
            f.write(new_bytes)
        dst = path
    else:
        # 输出到新文件：先写临时文件再原子替换，中断不会留下半个安装包
        tmp = out_path + ".tmp"
        try:
            shutil.copyfile(path, tmp)
            with open(tmp, "r+b") as f:
                f.seek(off)
                f.write(new_bytes)
            os.replace(tmp, out_path)
        except BaseException:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise
        dst = out_path
    print("已写入: %s" % dst)
    print("本机型号: %s" % ", ".join(models))
    print("用于运行时伪装的机型代码: %s" % spoof)
    return spoof


# ---------------------------------------------------------------- local model

def get_real_models():
    ps = (
        "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; "
        "$m=@(); "
        "try{$m+=(Get-CimInstance Win32_ComputerSystem).Model}catch{}; "
        "try{$m+=(Get-CimInstance Win32_BaseBoard).Product}catch{}; "
        "try{$m+=(Get-CimInstance Win32_ComputerSystemProduct).Name}catch{}; "
        "$m | Where-Object {$_ -and $_.Trim().Length -gt 0} | ForEach-Object {$_.Trim()} | Select-Object -Unique"
    )
    try:
        out = subprocess.check_output(["powershell.exe", "-NoProfile", "-Command", ps],
                                       stderr=subprocess.DEVNULL).decode("utf-8", "ignore")
    except Exception as e:
        raise SystemExit("读取本机型号失败: %s" % e)
    models = [x.strip() for x in out.splitlines() if x.strip()]
    if not models:
        raise SystemExit("读不到本机型号（WMI 返回空）")
    # 追加几个大小写变体，防止大小写敏感比较
    extra = []
    for m in list(models):
        if m.upper() not in [x.upper() for x in models + extra]:
            extra.append(m.upper())
    return models + extra


# ---------------------------------------------------------------- registry

def _set_value(root, subkey, name, value, wow=0):
    try:
        k = winreg.CreateKeyEx(root, subkey, 0, winreg.KEY_SET_VALUE | wow)
        winreg.SetValueEx(k, name, 0, winreg.REG_SZ, value)
        winreg.CloseKey(k)
        return True
    except OSError:
        return False


def _del_value(root, subkey, name, wow=0):
    try:
        k = winreg.OpenKeyEx(root, subkey, 0, winreg.KEY_SET_VALUE | wow)
        winreg.DeleteValue(k, name)
        winreg.CloseKey(k)
    except OSError:
        pass


def set_spoof_model(model):
    ok = []
    hives = [(winreg.HKEY_CURRENT_USER, "HKCU"), (winreg.HKEY_LOCAL_MACHINE, "HKLM")]
    for root, label in hives:
        for wow in (0, winreg.KEY_WOW64_32KEY, winreg.KEY_WOW64_64KEY):
            for sk in REG_SUBKEYS:
                # 64 位视图和 32 位视图都写一遍
                if _set_value(root, sk, "dummy_pc_model", model, wow):
                    ok.append("%s\\%s(wow=%d)" % (label, sk, wow))
    # 清掉早期测试用的 MockProduct，避免影响驱动更新
    for root, label in hives:
        for sk in (r"SOFTWARE\MI\Driver", r"SOFTWARE\WOW6432Node\MI\Driver"):
            for wow in (0, winreg.KEY_WOW64_32KEY):
                _del_value(root, sk, "MockProduct", wow)
    print("已写 dummy_pc_model=%s 到 %d 处" % (model, len(ok)))
    for line in ok[:8]:
        print("  " + line)


# ---------------------------------------------------------------- installed

def newest_version_dir(root=DEFAULT_INSTALL_ROOT):
    if not os.path.isdir(root):
        return None
    vers = [d for d in os.listdir(root) if re.fullmatch(r"\d+(\.\d+)+", d) and
            os.path.isdir(os.path.join(root, d))]
    if not vers:
        return None
    vers.sort(key=lambda v: [int(x) for x in v.split(".")])
    return os.path.join(root, vers[-1])


def patch_installed():
    vdir = newest_version_dir()
    if not vdir:
        raise SystemExit("没有找到已安装的小米电脑管家版本目录")
    print("安装目录: %s" % vdir)
    models = get_real_models()

    # 卸载器带同一套清单，打上补丁后才能在非小米电脑上正常卸载
    uninst = os.path.join(vdir, "Uninstall.exe")
    spoof = None
    if os.path.exists(uninst):
        bak = uninst + ".bak"
        if not os.path.exists(bak):
            shutil.copyfile(uninst, bak)
            print("已备份: %s" % bak)
        spoof = patch_file_manifest(uninst, models)
    else:
        print("警告: 未找到 Uninstall.exe")

    # 运行时伪装：让手机/平板把本机当作受支持的机型
    if spoof is None:
        # 从安装目录里任意带清单的 exe 中找受支持的机型代码
        spoof = SPOOF_FALLBACK
        for cand in os.listdir(vdir):
            if cand.lower().endswith(".exe"):
                try:
                    data = open(os.path.join(vdir, cand), "rb").read(64 * 1024 * 1024)
                    menus = find_manifests(data)
                    if menus:
                        spoof = choose_spoof_model(menus[0][3].get("support_tm_list"), models)
                        break
                except Exception:
                    pass
    set_spoof_model(spoof)


# ---------------------------------------------------------------- cli

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("patch-installer", help="给安装包打补丁")
    p1.add_argument("installer")
    p1.add_argument("-o", "--out")

    sub.add_parser("patch-installed", help="给已安装目录打补丁并写入运行时伪装")
    p2 = sub.add_parser("set-model", help="只写运行时伪装的机型代码")
    p2.add_argument("model", nargs="?", default=None)

    args = ap.parse_args()

    if args.cmd == "patch-installer":
        models = get_real_models()
        out = args.out
        if not out:
            base, ext = os.path.splitext(args.installer)
            out = base + "_patched" + ext
        patch_file_manifest(args.installer, models, out)
    elif args.cmd == "patch-installed":
        patch_installed()
    elif args.cmd == "set-model":
        model = args.model
        if not model:
            # 从当前安装目录的清单里挑一个受支持的机型代码
            vdir = newest_version_dir()
            model = SPOOF_FALLBACK
            if vdir:
                real = get_real_models()
                for cand in os.listdir(vdir):
                    if cand.lower().endswith(".exe"):
                        try:
                            data = open(os.path.join(vdir, cand), "rb").read(64 * 1024 * 1024)
                            menus = find_manifests(data)
                            if menus:
                                model = choose_spoof_model(menus[0][3].get("support_tm_list"), real)
                                break
                        except Exception:
                            pass
        set_spoof_model(model)


if __name__ == "__main__":
    main()
