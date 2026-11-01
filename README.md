# 小米电脑管家（非小米电脑）安装 + 功能解锁

## 当前状态（2026-10-28）

- 已安装 **6.0.0.39**，旧的 5.8.1.121 已由安装程序卸载
- 旧的 MiService 4.x 历史版本目录已删除，保留 6.0 依赖的 **4.1.1.726**
- **运行时伪装已开启**：`dummy_pc_model = TM2424`
  （`MiScreenShare` 启动日志已确认读取到该值）
- **`micont_service` 的 `--model` 与平板/手机存在取舍**：`--model=0` 手机妙享桌面可用，
  但会让 Lyra 的 WiFi P2P 能力变成 0（平板镜像失败）；`--model=TM2424/TM2309`
  则 P2P 正常。详见“平板镜像”一节。
- **平板镜像多显示器限制已打补丁**（`padgate_patch.py`），不再报
  “已连接其他显示设备，请断开其他显示设备后重试”
- 实测投屏链路已走通：`kRemoteConfirm → kLocalConfirm → kConnected`，
  `LaunchMirrorApp` 带 `source_ip/local_ip` 正常拉起，`IsShareStateOn = true`

## 关键修复：micont_service --model=0

对比官方通用版 **PcContinuity 1.1.2.36** 后找到的真正差异：通用版启动服务时用

```
micont_service.exe /service --model=0
```

而电脑管家是不带参数启动的。`--model=0` 就是“通用 PC 模式”。没有它，
手机端会在 `com.xiaomi.mirror:cast` 的远端确认阶段拒绝
（Lyra 日志 `remote reject` / `kRemoteConfirm` 超时）；加上它之后，
同一台机器上投屏立即成功。

补丁位置：

```
HKLM\SYSTEM\CurrentControlSet\Services\micont_service\ImagePath
= "...\MiSmartShare\micont_service.exe" --model=0
```

一键脚本会自动写入并重启服务。另外通用版 `MiSmartShareDLL.dll` 里
**没有 `is_xiaomi_pc` 检查**（电脑管家的有），我们用 `wmi_spoof_msimg32.dll`
把 `BaseBoard.Manufacturer` 变成 `XIAOMI` 来等效绕过。

## 平板镜像（padshare.coop.dropToPad）补丁

双显示器/多显卡机器镜像到平板时，App 弹“已连接其他显示设备，请断开其他显示设备后重试”，
实际是 `MiSmartShareDLL.dll` 里 `dropToPad` 前统计本机显示设备数，`> 1` 就直接回
`exception=1` 拒绝（与平板无关，也不是“另一台电脑占用平板”）。

定位过程（动态）：Frida hook 宿主事件发布函数，抓到调用链
`MiSmartShareDLL+0x3267b7 → 0x32f1e2`，其中

```
call  <统计显示设备数>      ; 返回 2
cmp   eax, 1
jle   <正常继续>
mov   edx, 1               ; exception = 1
call  [rax+0xa0]           ; 发布 exceptionToast
```

补丁只把这条路径上的 `7E`（jle）改成 `EB`（jmp），强制走“只有 1 台显示器”的分支；
统计函数本身不动，其它功能仍按真实显示器数量工作。

```
python padgate_patch.py status   # 查看
python padgate_patch.py apply    # 打补丁（自动结束占用进程，需管理员）
python padgate_patch.py restore  # 回退（使用 .bak-padgate）
```

特征码（6.0.0.39 唯一）：

```
E8 ?? ?? ?? ?? 83 F8 01 7E ?? 49 8B 06 4C 8B C6 BA 01 00 00 00
```

打上后 `dropToPad` 不再回 `exception=1`，会继续走到 P2P/LAN 连接阶段。

### 平板镜像异常码对照（App 文案）

| code | App 文案 | 含义 |
|---|---|---|
| 1 | 已连接其他显示设备，请断开其他显示设备后重试 | 本机显示设备数 > 1（已由 padgate 补丁绕过） |
| 2 | 检测到有其他显示设备接入… | 设备侧检测到其他显示 |
| 3 | 无法连接到平板，请修改显卡设置后重试 | **NVIDIA 首选图形处理器不是“自动/集成”**，或笔记本处于独显直连模式（核显不可用） |
| 4 | 请在设备管理器中确认 Xiaomi Bus Enumerator 驱动 | 缺虚拟显示驱动 |
| 5 | 暂不支持电脑纵向显示模式 | 屏幕竖屏 |
| 6 | 无法连接到电脑，请确认蓝牙和 Wi-Fi… | 通道/连接超时 |
| 7 | 对方正忙，请稍候重试 | P2P 不可用 |

实测：联想 81Y7（GTX 1660 Ti 独显直连、核显被隐藏）返回 **code 3**；
本机（AMD 核显+独显均启用）返回 6/7。平板镜像要求核显可用。



### NVIDIA 显卡检查（exception 3）

NVIDIA 机器上还会多一道检查：原生代码取显卡描述字符串，**只要包含 "NVIDIA"**
就直接回 `exception=3`（App 提示去 NVIDIA 控制面板改首选图形处理器）。
它并不真的读取 NVIDIA 设置，只是按厂商字符串拦截。

`padgate_patch.py` 的 `nvidia-gate` 把这条分支的 `je` 改成 `jmp`（跳过 exception 3），
让流程继续。实测联想 81Y7（独显直连）打上后：`exception 3` 消失，成功发出
`coop.startDrop`，`synergy` 通道也建立起来了（P2P），但 15 秒后仍因平板端不响应
而超时（exception 6，MiScreenShare 未启动）。



### 目前剩下的平板侧问题

补丁后 PC 能建立物理连接（Wi‑Fi LAN / P2P 均成功），但平板侧的应用层通道
5 秒无响应：

```
RequestConnectPhysServer success ... target medium:20(p2p)
5s 后 NtbsOnChannelFailed ... svc=com.xiaomi.mirror:synergy errmsg=unknown (channel code 3)
```

在对照机（联想 81Y7，Intel AX201）上，同一个 synergy 通道也返回 `code:3`，
所以这不是本机 MT7902 网卡或信任记录导致，而是平板端对这个版本的协同通道没有响应。
（注意：上面的 App 异常码 3 与这里 Lyra 的 channel code 3 不是同一个编号体系。）
下一步需要在平板上操作/升级“小米互联”，或换一台系统版本匹配的平板验证。



限制有**三层**：

1. **安装层**：安装包内嵌清单里的 `support_tm_list` / `support_nfc_list` /
   `support_distfile_list` 只放行小米/Timi 机型；安装器读 WMI 厂商+型号，
   不在名单里就拒绝安装。
2. **机型层**：`MiScreenShare` 会把 `dummy_pc_model`（注册表）作为“PC 机型”
   上报给手机/平板；`MiSmartShareDLL` 里还有 `is_xiaomi_pc` 检查。
3. **服务模式层**：`micont_service` 不带 `--model=0` 时，手机端拒绝投屏的
   远端确认。

现在三层都已处理：安装包白名单加入本机型号；WMI 伪装 + `dummy_pc_model`
把机型变成受支持的 `TM2424`；`micont_service` 以 `--model=0` 启动。

## 以后更新新版本：直接跑这个脚本

```powershell
# 自动找当前用户 Downloads\Archives 下最新的 XiaomiPCManager*.exe
.\Install-XiaomiPCManager.ps1

# 或指定安装包
.\Install-XiaomiPCManager.ps1 -Installer "D:\XiaomiPCManager_7.x.x.exe"

# 已经装好了，只想恢复运行时机型伪装（更新后功能又失效时用这个）
.\Install-XiaomiPCManager.ps1 -ModelOnly

# 同上，但最后不自动拉起主程序
.\Install-XiaomiPCManager.ps1 -ModelOnly -NoLaunch
```

脚本会自动（顺序执行）：

1. 提权（UAC 静默；取消提权则直接退出）
2. 用 `xpm_patch.py` 把本机型号写进安装包白名单（**字节长度不变**，不改程序代码；
   生成 `*_patched.exe`，原始安装包不改动）
3. 静默安装补丁版（`/Silent`）
4. 给已安装的 `Uninstall.exe` 打同样补丁（先备份为 `.bak`，保证以后能卸载），
   并写入 `dummy_pc_model`（HKCU/HKLM、32/64 位视图各一份，最大化版本兼容）
5. 部署 `wmi_spoof_msimg32.dll` 到 `<版本号>\MiSmartShare\` 并写 `SmartSharePatch` 配置
6. 给 `micont_service` 的 `ImagePath` 追加 `--model=0`（通用 PC 模式）
7. 运行 `padgate_patch.py apply`（平板镜像补丁；会自动结束占用进程）
8. 写入 `ProductModel=TM2309` 并停用 `MiDeviceService`（避免它用真实型号覆盖）
9. 重启相关服务并启动应用（加 `-NoLaunch` 只重启服务、不拉起主程序）

日志写在同目录 `install_log.txt`。

## 也可以手动用

```powershell
python xpm_patch.py patch-installer "原版安装包.exe" -o "输出.exe"
python xpm_patch.py patch-installed        # 需管理员
python xpm_patch.py set-model TM2424       # 需管理员
```

## 社区 WMI 伪装补丁（wmi_spoof_msimg32.dll）

这是一个第三方（自签名 CN=ChsBuffer）的 Detours 代理 DLL：伪装成 `msimg32.dll`，
被 `MiSmartShareHost` 加载后 hook WMI 的 `CWbemObject::Get`，把
`Win32_BaseBoard.Manufacturer` 改成 `XIAOMI`、`Win32_BaseBoard.Product` 改成 `TM2424`。

- 配置：`HKCU\Software\SmartSharePatch` 的 `SpoofManufacturer` / `SpoofDevice`
  （默认就是 `XIAOMI` / `TM2424`）
- 部署：一键脚本会自动复制到 `<版本号>\MiSmartShare\msimg32.dll`
- 实测效果：`MiSmartShareHost` 日志变为
  `Get pc_manufacturer XIAOMI ... pc model TM2424`，
  传给 `MiScreenShare` 的 `--pc_model` 也变成 `TM2424`
- 限制：只有加载 `MiSmartShareDLL` 的进程（`MiSmartShareHost`）生效。
  `micont_service`（对外 Mi Connect 广播）和 `XiaomiService`（云端 SKU）不加载它，
  所以**手机/平板"看不见这台电脑"的问题不会因此解决**——那取决于蓝牙 BLE 广播
  和云端设备身份，见下面"注意事项"。

## A/B 对照：为什么手机看得见另一台电脑

用 WindowsRemoteOps（SSH 到内网里的对照机）对比了另一台“手机能看见”的电脑：

| 项 | 对照机（手机可见） | 本机（手机不可见） |
|---|---|---|
| 硬件 | Lenovo 81Y7 / **Intel AX201** | 精粤 B650M / **MediaTek MT7902** |
| 电脑管家 | 5.5.0.57（旧版） | 6.0.0.39 |
| MiDeviceService | **未安装** | 已安装（启动时把 ProductModel 写回真实型号） |
| ProductModel | **TM2309** | 已改为 TM2309，MiDeviceService 已停用 |
| micont_service | 无 `--model=0` | 已加 `--model=0` |
| BLE 广播 | 正常 | 主广播 `adv not allow by env` |

结论：手机端“小米互联”发现电脑主要依赖 **BLE 广播**。对照机的 Intel AX201
BLE 正常，所以手机能看见；本机 MT7902 的主 BLE 广播被 Lyra 判为不允许，
只剩 mDNS，所以手机看不见。机型伪装（ProductModel / `--model=0`）是必要条件，
但不是充分条件。

**可靠解法**：换 Intel AX201/AX210（或受支持的 USB 蓝牙适配器）。换完后配合本脚本的
补丁，手机端应该就能发现这台电脑；不换硬件的话，从电脑端发起妙享桌面仍然可用
（已实测成功）。

## 注意事项

- 手机端需要**在线并解锁**；首次连接时手机/平板可能会弹出确认，请在设备上点允许。
- **手机/平板"看不见这台电脑"**：本机的 Lyra BLE 广播/扫描被环境禁用
  （`adv not allow by env`，网卡是 MediaTek MT7902，不在小米厂商支持列表），
  对外只剩 mDNS，Mi Connect 广播能力只有 `apps=[5]`。不过实测加上
  `micont_service --model=0` 后，**从电脑端发起妙享桌面已经可以成功**
  （手机确认后正常投屏）；手机端列表是否显示不影响从电脑端发起。
  如果坚持要手机/平板能主动列出这台电脑，最可靠的解法仍是换 Intel/Realtek 等
  受支持的无线网卡。
- 补丁版安装包的原厂签名会失效，重复运行时若遇 SmartScreen，选“更多信息 → 仍要运行”。
- 程序自动更新/修复会写回原版清单，届时重新跑一次上面的脚本即可。
- `MiDeviceService` 会一直显示“正在启动”（StartPending），它是小米笔记本专属功能
  （场景识别、AI 亮度、固件升级）的服务，不影响手机互联。
- 首页“驱动管理 → 从服务器获取信息失败”“剩余电量 255%”是非小米硬件的显示问题。
- 卸载：运行 `C:\Program Files\MI\XiaomiPCManager\<版本号>\Uninstall.exe`
  （安装包清单里 `reportUninstall: false`，所以“应用和功能”里没有卸载项）。
