# 踩坑总汇

> **一句话**：每条写清「现象 → 根因 → 怎么避」，现象那一行即搜索词；
> 定位过程与实测细节在 [RESEARCH.md](RESEARCH.md)，机制解释在 [ARCHITECTURE.md](ARCHITECTURE.md)。

---

## 安装层

### 安装包双击后提示不支持本机 / 直接拒绝安装

- **现象**：官方安装包在非小米电脑上跑不起来，提示机型不受支持。
- **根因**：安装包内嵌清单的 `support_tm_list` 等白名单只放行小米 / Timi 机型，安装器读 WMI 厂商 + 型号比对。
- **怎么避**：跑一键脚本或 `python xpm_patch.py patch-installer`（白名单字节等长加入本机型号），用补丁版 `*_patched.exe` 安装。

### 「应用和功能」里找不到卸载项

- **现象**：装好后系统设置里没有卸载入口。
- **根因**：安装包清单里 `reportUninstall: false`，不向系统注册卸载项。
- **怎么避**：直接运行 `C:\Program Files\MI\XiaomiPCManager\<版本号>\Uninstall.exe`。

### SmartScreen 拦截补丁版安装包

- **现象**：运行 `*_patched.exe` 时 SmartScreen 弹警告。
- **根因**：白名单补丁动过字节，原厂签名失效。
- **怎么避**：选「更多信息 → 仍要运行」；重复安装时预期会再弹。

## 机型层

### 程序更新后互联功能又失效

- **现象**：电脑管家自动更新 / 修复后，原来能用的功能不行了。
- **根因**：更新会写回原版清单与配置，覆盖机型伪装。
- **怎么避**：重跑 `.\Install-XiaomiPCManager.ps1 -ModelOnly`（只重做伪装相关动作：注册表、WMI DLL、服务参数与 padgate 补丁，不重装）。

### ProductModel 又变回真实型号

- **现象**：注册表里的 `ProductModel` 改了又弹回去。
- **根因**：`MiDeviceService` 启动时把真实型号写回。
- **怎么避**：一键脚本已停用该服务；手动操作的话记得一并停用。

### MiDeviceService 一直显示「正在启动」

- **现象**：服务列表里该服务长期 StartPending。
- **根因**：它是小米笔记本专属功能（场景识别、AI 亮度、固件升级）的服务，非小米硬件上起不来。
- **怎么避**：不用管，不影响手机互联；一键脚本本来就把它停用了。

### 首页「驱动管理 → 从服务器获取信息失败」「剩余电量 255%」

- **现象**：主界面两处显示异常。
- **根因**：非小米硬件的显示问题，服务器按小米机型返回信息。
- **怎么避**：无功能影响，忽略。

## 服务模式层

### 手机端投屏确认时超时 / remote reject

- **现象**：从电脑发起妙享桌面，手机端远端确认阶段失败。
- **根因**：`micont_service` 不带参数启动（电脑管家默认），手机端拒绝。
- **怎么避**：给服务 `ImagePath` 追加 `--model=0`（一键脚本步骤 6）。机制见 [ARCHITECTURE.md](ARCHITECTURE.md) §1。

### `--model=0` 之后手机能投了，平板镜像反而失败

- **现象**：加 `--model=0` 后手机妙享可用，但平板镜像的 WiFi P2P 能力变 0。
- **根因**：`--model` 取舍——`--model=0`（通用 PC 模式）牺牲 Lyra 的 P2P；`--model=TM2424/TM2309` 则 P2P 正常。
- **怎么避**：按需求选：手机妙享优先用 `--model=0`，平板镜像优先用 `--model=TM2424`。取舍说明见 [ARCHITECTURE.md](ARCHITECTURE.md) §2.5。

### 手机 / 平板「看不见这台电脑」

- **现象**：设备端的设备列表里没有这台电脑，但反过来从电脑发起可以连。
- **根因**：发现主要靠 BLE 广播；不在小米支持列表的无线网卡（如 MediaTek MT7902）主广播被禁，只剩 mDNS。机型伪装是必要条件不是充分条件。
- **怎么避**：换 Intel AX201/AX210 等受支持网卡；不换硬件就接受「从电脑端发起」的用法。A/B 对照见 [RESEARCH.md](RESEARCH.md) §5。

## 小米互传

### 「传输失败 / 传输遇到问题，请重试」（error 404 / 36018）

- **现象**：电脑管家「传输列表」里任务立刻变红，提示「传输失败 / 传输遇到问题，请重试」；
  设备能被发现、文件选择也正常，但发送进度从没开始。
- **根因**：`micont_service --model=0`（通用 PC 模式）把 Lyra 的 WiFi P2P 能力上报成 0，
  互传通道 `com.miui.mishare.connectivity:miLyraShareTransfer` 在 P2P 协商阶段直接被拒：
  `err_code=36018 "p2p nego wifi capability not supported"` -> `task set error 404` -> `kFailed`。
  日志里同一时刻有 `wifi_capabilities=0` 与 `netcard_medium_type=0`，与无线网卡本身是否支持
  Wi-Fi Direct 无关（`netsh wlan show wirelesscapabilities` 可验）。轮转日志里能进 `kFileSending`
  的旧记录与全量 404 的新记录形成 A/B 对照，见 [RESEARCH.md](RESEARCH.md) §7。
- **怎么避**：把服务 `ImagePath` 的 `--model=0` 换成 `--model=TM2424`（或 `TM2309`）后重启
  `micont_service`，P2P 能力恢复；取舍见 [ARCHITECTURE.md](ARCHITECTURE.md) §2.5。
  别再跑 `Install-XiaomiPCManager.ps1 -ModelOnly`，它会把 `--model=0` 写回去；管家自动更新
  覆盖后重做这一组即可。

### 右键「使用小米互传发送」点击无反应

- **现象**：右键文件能看到「使用小米互传发送」，点击后什么也不发生，互传窗口不弹、日志里
  也没有右键来源的 `HandleCreateSendTask`。
- **根因**：这是 Win11 新右键下的 COM 激活链断点，不是单点故障——
  ① 菜单键 `HKCR\*\shell\MiDropExtMenu` 与 `HKCR\Directory\shell\MiDropExtMenu` 带
     `LegacyDisable`，传统动词只落到「显示更多选项」；
  ② `ExplorerCommandHandler` 指向的 CLSID `{504d69c0-...}` 未登记进
     `Shell Extensions\Approved`，`tasklist /m MiDropShellExt.dll` 零进程加载；
  ③ 菜单文案来自 MSIX 包（`Windows.ShareTarget` + `PackagedCom\Server\0`），但该 CLSID
     在 `PackagedCom\ClassIndex` 下没有条目，Win32 COM 与 MSIX 两套注册未打通；
  ④ `MiDropShellExt.dll` 用 `CreateProcessW` 启动同目录 `\Launch.exe --contextmenu_dropfile=1`，
     而版本目录 `<版本号>\MiSmartShare\Launch.exe` 缺失（根目录 `Launch.exe` 不处理该参数）。
- **怎么避**：立即可用的入口是「显示更多选项」（或 `Shift+F10`）与系统共享菜单里的
  「小米互传」；要让旧动词可用，把根目录 `Launch.exe` 复制到 `MiSmartShare\` 与版本目录、
  把该 CLSID 补进 `Shell Extensions\Approved`、重启 `explorer.exe`。一级新菜单需补
  PackagedCom 映射或装适配组件（社区实测见 [RESEARCH.md](RESEARCH.md) §7）。

### `ProductModel` 的 64 位视图被回写成真实主板型号

- **现象**：`reg query "HKLM\SOFTWARE\MI\MiDeviceService" /v ProductModel /reg:64` 是真实
  主板型号，`/reg:32` 与 `WOW6432Node` 却是脚本写入的 `TM2309`。
- **根因**：`MiDeviceService` 已停用，但外部 `MiService` 仍运行；一键脚本只写了 32 位视图
  与 `WOW6432Node`，64 位视图由其它进程按真实硬件回写。
- **怎么避**：需要全视图一致时，管理员执行
  `reg add "HKLM\SOFTWARE\MI\MiDeviceService" /v ProductModel /t REG_SZ /d TM2309 /reg:64 /f`。

## 平板镜像

### 「已连接其他显示设备，请断开其他显示设备后重试」（exception 1）

- **现象**：镜像到平板时弹这个错，但根本没有别的显示设备。
- **根因**：`MiSmartShareDLL.dll` 在 `dropToPad` 前统计本机显示设备数，`> 1` 直接拒绝，与平板无关。
- **怎么避**：`python padgate_patch.py apply`（display-gate 补丁）。

### 「无法连接到平板，请修改显卡设置后重试」（exception 3）

- **现象**：NVIDIA 机器上平板镜像报这个错。
- **根因**：DLL 按显卡描述字符串含 `NVIDIA` 就直接拦，并不真读 NVIDIA 设置；笔记本独显直连模式（核显被隐藏）也会触发。
- **怎么避**：`padgate_patch.py apply` 已含 nvidia-gate；但平板镜像要求核显可用，独显直连需在 BIOS / 控制面板恢复核显输出。

### 补丁写入失败：文件被占用

- **现象**：`padgate_patch.py apply` 报写入失败。
- **根因**：`MiSmartShareDLL.dll` 被运行中的进程加载。
- **怎么避**：`apply` 会自动 `taskkill` 占用进程；仍失败就先退出小米电脑管家，或用管理员重跑。

### 补丁后连接建立了，15 秒 / 5 秒后仍超时

- **现象**：`exception 3` 消失、P2P 通道建立，但平板端应用层无响应（`NtbsOnChannelFailed`）。
- **根因**：平板端对当前版本协同通道没有响应——对照机同样复现，与本机网卡无关（截至 6.0.0.39 实测）。
- **怎么避**：等平板侧「小米互联」更新后重测；进展记录在 [RESEARCH.md](RESEARCH.md) §6。

## 工具脚本

### 门禁脚本在 GBK 控制台下抛 `UnicodeEncodeError`，退出码 1

- **现象**：Windows 中文控制台（cp936）跑 `python -I tools/make_social_preview.py` / 门禁脚本，
  打结论的那一行抛 `UnicodeEncodeError: 'gbk' codec can't encode character`，脚本以退出码 1 结束。
- **根因**：`✓` U+2713 / `✗` U+2717 不在 cp936 码表；`python -I` 忽略 `PYTHONIOENCODING` /
  `PYTHONUTF8`，环境变量救不回来。
- **怎么避**：结论行只用 ASCII（`[OK]` / `[FAIL]`）；入口加
  `if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(errors="replace")` 兜底。
  同一问题首次记录见 ZcodeAIModels 仓「踩坑总汇」第 36 节（跨仓引用，非本仓路径）。
- **验证**：`python -I` 重跑同一命令 → 退出码 0、无 traceback。
