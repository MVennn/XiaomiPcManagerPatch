# 定位过程与实测记录

> **一句话**：每个补丁是怎么定位的、实测数据与对照结论、当前还剩什么没打通 ——
> 带版本标注的内容是**历史记录**，可容忍过时；当前适配状态以 [TOOLS.md](TOOLS.md) §6 为准。

---

## 1. `micont_service --model=0` 的发现

对比官方通用版 **PcContinuity 1.1.2.36** 找到真正差异：通用版启动服务用
`micont_service.exe /service --model=0`，而电脑管家不带参数。`--model=0` 就是「通用 PC 模式」。

没有它，手机端在 `com.xiaomi.mirror:cast` 的远端确认阶段拒绝（Lyra 日志
`remote reject` / `kRemoteConfirm` 超时）；加上后同一台机器投屏立即成功。

通用版 `MiSmartShareDLL.dll` 里**没有 `is_xiaomi_pc` 检查**（电脑管家的有），
所以用 WMI 伪装 DLL（`BaseBoard.Manufacturer → XIAOMI`）等效绕过，见 [ARCHITECTURE.md](ARCHITECTURE.md) §2.3。

## 2. 平板镜像多显示器拦截的定位（display-gate）

现象：双显示器机器镜像到平板报「已连接其他显示设备」，实际与平板无关。

动态定位：Frida hook 宿主事件发布函数，抓到调用链 `MiSmartShareDLL+0x3267b7 → 0x32f1e2`：

```
call  <统计显示设备数>      ; 返回 2
cmp   eax, 1
jle   <正常继续>
mov   edx, 1               ; exception = 1
call  [rax+0xa0]           ; 发布 exceptionToast
```

补丁只把这条路径的 `7E`（jle）改 `EB`（jmp），强制走「只有 1 台显示器」分支；
统计函数不动，其它功能仍按真实显示器数量工作。

特征码（6.0.0.39 唯一）：

```
E8 ?? ?? ?? ?? 83 F8 01 7E ?? 49 8B 06 4C 8B C6 BA 01 00 00 00
```

## 3. NVIDIA 拦截的定位（nvidia-gate）

原生代码取显卡描述字符串，**只要包含 "NVIDIA"** 就直接回 `exception=3`
（App 提示去 NVIDIA 控制面板改首选图形处理器）——它不真读 NVIDIA 设置，只按厂商字符串拦截。

`nvidia-gate` 把这条分支的 `je` 改 `jmp`。实测联想 81Y7（独显直连）打上后：
`exception 3` 消失，成功发出 `coop.startDrop`，`synergy` 通道建立（P2P），
但 15 秒后仍因平板端不响应而超时（exception 6，MiScreenShare 未启动）。

## 4. 平板镜像异常码对照（App 文案）

| code | App 文案 | 含义 |
|---|---|---|
| 1 | 已连接其他显示设备，请断开其他显示设备后重试 | 本机显示设备数 > 1（已由 display-gate 绕过） |
| 2 | 检测到有其他显示设备接入… | 设备侧检测到其他显示 |
| 3 | 无法连接到平板，请修改显卡设置后重试 | NVIDIA 字符串拦截（已由 nvidia-gate 绕过），或独显直连导致核显不可用 |
| 4 | 请在设备管理器中确认 Xiaomi Bus Enumerator 驱动 | 缺虚拟显示驱动 |
| 5 | 暂不支持电脑纵向显示模式 | 屏幕竖屏 |
| 6 | 无法连接到电脑，请确认蓝牙和 Wi-Fi… | 通道 / 连接超时 |
| 7 | 对方正忙，请稍候重试 | P2P 不可用 |

注意：这里的 App 异常码与 Lyra 日志里的 channel code **不是同一套编号**。

## 5. A/B 对照：为什么手机看得见另一台电脑

用 WindowsRemoteOps（SSH 到内网对照机）对比了另一台「手机能看见」的电脑：

| 项 | 对照机（手机可见） | 本机（手机不可见） |
|---|---|---|
| 硬件 | 联想 81Y7 / Intel AX201 | 精粤 B650M / MediaTek MT7902 |
| 电脑管家 | 5.5.0.57（旧版） | 6.0.0.39 |
| MiDeviceService | 未安装 | 已安装（启动时把 ProductModel 写回真实型号） |
| ProductModel | TM2309 | 已改为 TM2309，MiDeviceService 已停用 |
| micont_service | 无 `--model=0` | 已加 `--model=0` |
| BLE 广播 | 正常 | 主广播 `adv not allow by env` |

**结论**：手机端「小米互联」发现电脑主要依赖 **BLE 广播**。对照机 AX201 正常所以可见；
本机 MT7902 主广播被 Lyra 判为不允许，只剩 mDNS。机型伪装（`ProductModel` / `--model=0`）
是必要条件，不是充分条件。可靠解法是换 Intel AX201/AX210 等受支持网卡；
不换硬件时从电脑端发起妙享桌面仍然可用（已实测成功）。

## 6. 目前剩下的平板侧问题（截至 6.0.0.39）

补丁后 PC 能建立物理连接（Wi-Fi LAN / P2P 均成功），但平板侧应用层通道 5 秒无响应：

```
RequestConnectPhysServer success ... target medium:20(p2p)
5s 后 NtbsOnChannelFailed ... svc=com.xiaomi.mirror:synergy errmsg=unknown (channel code 3)
```

在对照机（联想 81Y7，Intel AX201）上同一个 synergy 通道也返回 `code:3`——
所以不是本机 MT7902 网卡或信任记录的问题，而是平板端对这个版本的协同通道没有响应。
下一步：在平板上操作 / 升级「小米互联」，或换一台系统版本匹配的平板验证。
