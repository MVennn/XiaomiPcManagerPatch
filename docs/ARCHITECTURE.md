# 架构与边界

> **一句话**：三层限制分别是什么、每个补丁改了哪里、会动机器哪些状态、怎么回退 ——
> 本篇是**正本**，README 与其他文档只留概述 + 指向这里。

---

## 1. 三层限制与对应补丁

非小米电脑用小米电脑管家，拦路的有三层，仓库各给了一个补丁：

| 层 | 谁在拦 | 补丁 | 所在文件 |
|---|---|---|---|
| **安装层** | 安装包内嵌清单的 `support_tm_list` / `support_nfc_list` / `support_distfile_list` 只放行小米 / Timi 机型，安装器读 WMI 厂商 + 型号，不在名单直接拒绝安装 | 白名单加入本机型号（**字节等长**替换，不改程序代码），生成 `*_patched.exe`，原包不动 | `xpm_patch.py patch-installer` |
| **机型层** | ① `MiScreenShare` 把 `dummy_pc_model`（注册表）作为「PC 机型」上报给手机 / 平板；② `MiSmartShareDLL.dll` 里有 `is_xiaomi_pc` 检查；③ `MiDeviceService` 启动时会把真实型号写回 `ProductModel` | `dummy_pc_model` 写成受支持机型（HKCU/HKLM、32/64 位视图各一份）；`MiDeviceService` 停用 + `ProductModel=TM2309`；WMI 伪装 DLL 把 `BaseBoard.Manufacturer` 变 `XIAOMI` | `xpm_patch.py` + `wmi_spoof_msimg32.dll` |
| **服务模式层** | `micont_service` 不带参数启动时（电脑管家默认），手机端在 `com.xiaomi.mirror:cast` 远端确认阶段拒绝（`remote reject` / `kRemoteConfirm` 超时） | 给服务 `ImagePath` 追加 `--model=0`（通用 PC 模式），等效官方通用版 PcContinuity 的启动方式 | 一键脚本步骤 6 |

另有一个独立补丁：**平板镜像拦截**（`padgate_patch.py`），见 §2.4。

## 2. 各补丁的机制

### 2.1 安装包白名单补丁（xpm_patch.py patch-installer）

在安装包里定位内嵌清单的机型白名单，把本机型号**等长替换**进去——字节长度不变，程序代码零改动。输出到 `-o` 指定的 `*_patched.exe`，原始安装包不碰。

### 2.2 运行时机型伪装（xpm_patch.py patch-installed / set-model）

- `dummy_pc_model` 写到 `HKCU` / `HKLM` 的
  `SOFTWARE\Timi Personal Computing\MiScreenShare` 与 `SOFTWARE\MI\MiScreenShare`
  （各含 WOW6432Node 视图），这是 `MiScreenShare` 上报机型时读的值；
- `ProductModel=TM2309` 写到 `SOFTWARE\MI\Driver`（含 WOW6432Node），并停用
  `MiDeviceService` —— 否则它启动时会把真实型号写回去；
- 给已安装的 `Uninstall.exe` 打同样的白名单补丁（先备份 `.bak`），保证以后能正常卸载。

### 2.3 WMI 伪装（wmi_spoof_msimg32.dll）

第三方 Detours 代理 DLL：伪装成 `msimg32.dll` 被 `MiSmartShareHost` 加载后，hook WMI 的
`CWbemObject::Get`，把 `Win32_BaseBoard.Manufacturer` 改成 `XIAOMI`、`Win32_BaseBoard.Product`
改成 `TM2424`，等效绕过 `MiSmartShareDLL.dll` 里的 `is_xiaomi_pc` 检查（通用版的 DLL 没有这个检查）。

- 配置：`HKCU\Software\SmartSharePatch` 的 `SpoofManufacturer` / `SpoofDevice`（默认即 `XIAOMI` / `TM2424`）；
- 部署位置：`<版本号>\MiSmartShare\msimg32.dll`（一键脚本自动复制）；
- **作用域限制**：只对加载 `MiSmartShareDLL` 的进程（`MiSmartShareHost`）生效。
  `micont_service`（对外 Mi Connect 广播）与 `XiaomiService`（云端 SKU）不加载它 ——
  手机 / 平板「看不见这台电脑」的问题不由它解决，那取决于 BLE 广播与云端设备身份（见 [RESEARCH.md](RESEARCH.md) §5）。

### 2.4 平板镜像拦截补丁（padgate_patch.py）

`MiSmartShareDLL.dll` 在 `dropToPad` 前统计本机显示设备数，`> 1` 直接回 `exception=1`
（「已连接其他显示设备」）；显卡描述字符串含 `NVIDIA` 也直接回 `exception=3`。
两条拦截都靠特征码定位，把条件跳转改成无条件跳转：

| 补丁名 | 改动 | 效果 |
|---|---|---|
| `display-gate` | `7E`（jle）→ `EB`（jmp） | 强制走「只有 1 台显示器」分支，统计函数本身不动 |
| `nvidia-gate` | `74`（je）→ `EB`（jmp） | 跳过 NVIDIA 厂商字符串拦截 |

特征码与 6.0.0.39 绑定（换版本不保证命中）。`apply` 一次打两个补丁，备份 `.bak-padgate`；
`status` 只读看两个补丁各自的状态（original / patched / mixed / not-found）；`restore` 从备份回退。

### 2.5 `--model=0` 的取舍

`micont_service --model=0` 让手机妙享桌面可用，但会让 Lyra 的 WiFi P2P 能力变成 0
（平板镜像失败）；`--model=TM2424/TM2309` 则 P2P 正常。一键脚本写的是 `--model=0`
（手机优先）。平板镜像定位与剩余问题见 [RESEARCH.md](RESEARCH.md)。

## 3. 会改什么

一键脚本按顺序做以下事（`-ModelOnly` 只做 4、8、9 中与机型相关的部分）：

| # | 动作 | 落点 |
|---|---|---|
| 1 | 提权（UAC 静默，取消则退出） | — |
| 2 | 生成补丁版安装包 | 当前目录 `*_patched.exe`（原包不动） |
| 3 | 静默安装补丁版 | `C:\Program Files\MI\XiaomiPCManager\<版本号>\` |
| 4 | 补 `Uninstall.exe` 白名单 + 写 `dummy_pc_model` + 写 `ProductModel`、停用 `MiDeviceService` | 同上目录；HKCU/HKLM 注册表（含 WOW6432Node） |
| 5 | 部署 WMI 伪装 DLL | `<版本号>\MiSmartShare\msimg32.dll`；`HKCU\Software\SmartSharePatch` |
| 6 | `micont_service` 的 `ImagePath` 追加 `--model=0` | `HKLM\SYSTEM\CurrentControlSet\Services\micont_service` |
| 7 | 打平板镜像补丁 | `<版本号>\MiSmartShare\MiSmartShareDLL.dll`（备份 `.bak-padgate`） |
| 8 | 重启相关服务 | micont_service 等 |
| 9 | 启动应用（`-NoLaunch` 则不拉起） | — |

日志写在脚本同目录 `install_log.txt`（`.gitignore` 已排除，不入库）。

## 4. 回退

| 想撤什么 | 怎么做 |
|---|---|
| 平板镜像补丁 | `python padgate_patch.py restore`（用 `.bak-padgate`） |
| 机型伪装 / `--model=0` | 重装原版安装包，或手动删注册表值、还原服务 `ImagePath` |
| 补丁版安装包 | 删 `*_patched.exe`，原包从未被改动 |
| 整个电脑管家 | 运行 `<版本号>\Uninstall.exe`（清单里 `reportUninstall: false`，所以「应用和功能」里没有卸载项） |
| WMI 伪装 DLL | 删 `<版本号>\MiSmartShare\msimg32.dll` |

## 5. 版本适配

- 实测基准：6.0.0.39（旧 5.8.1.121 已由安装程序自动卸载）。
- `padgate_patch.py` 的两条特征码来自 6.0.0.39 的字节布局；新版本先用 `status` 验证。
- 安装包白名单补丁只依赖清单格式，跨版本存活概率更高，但同样需重验。
