# 工具清单

> **一句话**：仓库里每个文件是什么、脚本参数怎么给、退出码怎么读、版本适配到哪 ——
> 本篇是**正本**，原理与「会改什么」在 [ARCHITECTURE.md](ARCHITECTURE.md)。

---

## 1. 文件清单

```
XiaomiPcManagerPatch/
├── Install-XiaomiPCManager.ps1   一键补丁 / 安装脚本（自动提权）
├── xpm_patch.py                  安装包白名单补丁 + 运行时机型伪装
├── padgate_patch.py              平板镜像拦截补丁（display-gate + nvidia-gate）
├── wmi_spoof_msimg32.dll         社区 WMI 伪装代理 DLL（第三方，见 NOTICE）
└── tools/
    ├── check-docs.py             文档自检（链接 / 锚点 / 引言块 / 孤儿）
    ├── check-secrets.py          敏感信息扫描守卫
    └── make_social_preview.py    渲染 assets/ 门面图（需 numpy + Pillow）
```

运行期产物（都不入库，见 `.gitignore`）：`*_patched.exe`、`install_log.txt`、
目标机上的 `*.bak` / `*.bak-padgate`。

## 2. Install-XiaomiPCManager.ps1

一键全流程。步骤清单见 [ARCHITECTURE.md](ARCHITECTURE.md) §3。

| 参数 | 作用 |
|---|---|
| `-Installer <路径>` | 指定安装包；缺省自动找当前用户 `Downloads\Archives` 下最新的 `XiaomiPCManager*.exe` |
| `-ModelOnly` | 跳过安装，只恢复运行时机型伪装（程序更新后功能失效时用） |
| `-NoLaunch` | 结束时不拉起主程序（只重启服务） |

- 自动提权（UAC 静默）；取消提权则直接退出。
- 日志写在脚本同目录 `install_log.txt`。
- 退出码：`0` 成功；非 0 见日志尾部的失败步骤。

## 3. xpm_patch.py

| 子命令 | 作用 | 权限 |
|---|---|---|
| `patch-installer <安装包> [-o 输出]` | 给安装包白名单加本机型号（字节等长），输出 `*_patched.exe`，原包不动 | 普通用户 |
| `patch-installed` | 给已安装目录的 `Uninstall.exe` 打补丁（先备份 `.bak`）并写运行时伪装 | 管理员 |
| `set-model [机型]` | 只写 `dummy_pc_model` 运行时伪装（缺省 TM2424） | 管理员 |

- `-o` 与输入同路径时**原地改写**（先备份同名 `.bak`）；其他路径走临时文件 + 原子替换，失败不落半成品。想保住原版安装包就别用同路径，先另存一份。
- 退出码：`0` 成功；`1` 致命错误（未找到内嵌清单 / 读不到本机型号 / 没找到已安装版本目录，错误信息走 stderr）。

## 4. padgate_patch.py

对 `<安装目录>\<版本号>\MiSmartShare\MiSmartShareDLL.dll` 打平板镜像拦截补丁。
两个补丁（`display-gate`、`nvidia-gate`）的机制见 [ARCHITECTURE.md](ARCHITECTURE.md) §2.4；
`apply` 一次打两个，写回走临时文件 + `os.replace`，失败自动清理。

| 子命令 | 作用 | 权限 |
|---|---|---|
| `status`（缺省） | 只读，输出两个补丁各自状态：`original` / `patched` / `mixed` / `not-found` | 普通用户 |
| `apply` | 打补丁；先 `taskkill` 占用进程（小米电脑管家 / MiSmartShareHost / MiScreenShare），备份 `.bak-padgate` | 管理员 |
| `restore` | 从 `.bak-padgate` 回退 | 管理员 |

退出码：`0` 成功；`1` 找不到 DLL（未安装）或用法错误；`2` 找不到备份文件；`4` 文件被占用（先退出电脑管家或用管理员重试）。

## 5. wmi_spoof_msimg32.dll

第三方（自签名，作者 CN=ChsBuffer）Detours 代理 DLL，随社区发布原样收录，本仓不修改、不重编译。
机制、配置键与作用域限制见 [ARCHITECTURE.md](ARCHITECTURE.md) §2.3；版权与来源声明见根 [NOTICE](../NOTICE)。

## 6. 版本适配台账

| 电脑管家版本 | 适配状态 | 备注 |
|---|---|---|
| 6.0.0.39 | ✅ 全量实测 | 特征码、白名单、注册表落点都按此版本验证 |
| 5.8.1.121 | 历史经过 | 早期版本，已被 6.x 安装程序自动卸载，不再验证 |
| 其他版本 | ❓ 未验证 | 先跑 `padgate_patch.py status` 看特征码是否命中；白名单补丁需重验清单格式 |

换版本后实测结论写进 [RESEARCH.md](RESEARCH.md)，适配状态更新到本表（规则见 [DOC-RULES.md](DOC-RULES.md) 的变更触发矩阵）。
