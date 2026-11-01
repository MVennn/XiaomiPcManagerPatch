<div align="center">

<img src="https://raw.githubusercontent.com/MVennn/XiaomiPcManagerPatch/main/assets/logo.png" width="128" alt="XiaomiPcManagerPatch">

# XiaomiPcManagerPatch

**小米电脑管家在非小米电脑上的安装与功能解锁补丁**

白名单放行、机型伪装、平板镜像解锁 —— 全部原地补丁、字节等长、可回退。

![CI](https://github.com/MVennn/XiaomiPcManagerPatch/actions/workflows/ci.yml/badge.svg) ![源码仓库](https://img.shields.io/badge/源码仓库-GitHub-181717?logo=github&logoColor=white) ![问题反馈](https://img.shields.io/badge/问题反馈-Issues-181717?logo=github&logoColor=white) ![Windows](https://img.shields.io/badge/Windows-10%20%2F%2011-0078D4?logo=windows&logoColor=white) ![实测版本](https://img.shields.io/badge/实测版本-6.0.0.39-FF6900) ![License](https://img.shields.io/badge/License-Apache--2.0-blue)

</div>

---

## 这是什么

小米电脑管家的安装包内嵌机型白名单，非小米电脑装不上；装上了（用其它手段），互联功能也会被逐层拦住。本仓库把解锁手段整理成三个补丁工具，对应**三层限制**——安装层白名单、机型层上报、服务模式层——另含平板镜像的多显示器 / 独显拦截补丁。

仓库只含补丁脚本、一个第三方代理 DLL 与文档，**不含也不分发小米电脑管家本身**，安装包需自备。

| 文件 | 干什么 |
|---|---|
| `Install-XiaomiPCManager.ps1` | 一键全流程：补丁安装包 → 静默安装 → 机型伪装 → 部署 DLL → 平板镜像补丁 |
| `xpm_patch.py` | 安装包白名单补丁 + 运行时机型伪装（写注册表） |
| `padgate_patch.py` | `MiSmartShareDLL.dll` 的平板镜像拦截补丁（特征码定位） |
| `wmi_spoof_msimg32.dll` | 社区 WMI 伪装代理 DLL（来源见 [NOTICE](NOTICE)） |

每层限制的原理、补丁改了什么、会动机器哪些状态、怎么回退，见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)；脚本参数与退出码见 [docs/TOOLS.md](docs/TOOLS.md)。

## 环境要求

| 项 | 要求 |
|---|---|
| 系统 | Windows 10 / 11（x64）；安装与补丁步骤需要管理员权限 |
| 运行时 | Python 3.8+（补丁脚本只用标准库） |
| 安装包 | 自备小米电脑管家官方安装包（一键脚本会在当前用户 `Downloads\Archives` 下自动找） |
| 版本适配 | 实测 **6.0.0.39**。平板镜像补丁靠特征码定位，换版本不保证命中——先跑 `padgate_patch.py status` 看 |

## 使用

一键脚本（自动提权；取消 UAC 则直接退出）：

```powershell
.\Install-XiaomiPCManager.ps1                                       # 自动找安装包，全流程
.\Install-XiaomiPCManager.ps1 -Installer "D:\XiaomiPCManager_7.x.x.exe"   # 指定安装包
.\Install-XiaomiPCManager.ps1 -ModelOnly                            # 更新后功能失效时：只恢复机型伪装
.\Install-XiaomiPCManager.ps1 -ModelOnly -NoLaunch                  # 同上，但不拉起主程序
```

它逐步做什么、写哪些注册表和服务，见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) 的「会改什么」；日志写在脚本同目录 `install_log.txt`（不入库）。

只想手动打单个补丁：

```sh
python xpm_patch.py patch-installer "原版安装包.exe" -o "输出.exe"   # 安装包白名单补丁（原包不动）
python xpm_patch.py patch-installed                                 # 已装目录打补丁 + 运行时伪装（需管理员）
python xpm_patch.py set-model TM2424                                # 只写运行时机型（需管理员）
python padgate_patch.py status                                      # 平板镜像补丁状态（只读）
python padgate_patch.py apply                                       # 打补丁（需管理员，自动结束占用进程）
python padgate_patch.py restore                                     # 回退
```

补丁版安装包的原厂签名会失效；SmartScreen 拦截时选「更多信息 → 仍要运行」。

## 反馈

装不上、补丁没命中、想要新版本适配，到 [Issues](https://github.com/MVennn/XiaomiPcManagerPatch/issues) 反馈。请带上：

- Windows 版本（`winver`）与电脑管家版本号
- 用的哪个脚本与完整命令
- 输出原文（贴前抹掉机器名、用户名与序列号）

已知坑按「现象 → 根因 → 怎么避」整理在 [docs/PITFALLS.md](docs/PITFALLS.md)；定位过程与实测记录见 [docs/RESEARCH.md](docs/RESEARCH.md)。想参与贡献见 [CONTRIBUTING](CONTRIBUTING.md)，安全问题按 [SECURITY](SECURITY.md) 报告。

## 免责声明

本项目仅供学习与个人使用。

- **会改系统状态**：写注册表（机型伪装、服务启动参数）、改服务 `ImagePath`、给官方 DLL 打字节补丁。执行前先读 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) 的「会改什么」，回退方式在同一篇。
- **补丁版安装包签名失效**；程序自动更新 / 修复会写回原版清单，届时重跑脚本即可。
- 本仓库不分发小米电脑管家安装包，也不修改其安装包以外的程序文件；使用自备安装包的许可与风险自行承担。
- 所有结论都在特定硬件与 6.0.0.39 上实测，换版本、换硬件**必须重新验证**。
- 本项目与小米无隶属或合作关系。「小米电脑管家」等名称与标识的权利归其权利人所有。

## 开源鸣谢

本仓库使用了这个第三方组件（详见 [NOTICE](NOTICE)）：

| 组件 | 用途 | 来源 |
|---|---|---|
| `wmi_spoof_msimg32.dll` | WMI 机型伪装代理 DLL（作者 ChsBuffer，基于 Microsoft Detours） | 社区发布，原样收录 |

## 许可证

本仓库以 [Apache License 2.0](LICENSE) 发布；第三方组件的版权与来源见 [NOTICE](NOTICE)。
