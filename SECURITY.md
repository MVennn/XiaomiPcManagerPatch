# 安全策略

> **一句话**：发现安全问题怎么报、**这套补丁会改你的机器哪些状态**、第三方 DLL 与供应链提示。

## 支持的版本

| 分支 | 收修 |
|---|---|
| `main` | ✅ 修 bug 与安全问题 |

## 怎么报告

**请不要开公开 Issue 报告安全问题。** 用 GitHub 的
「Security → Report a vulnerability」提私有报告：
<https://github.com/MVennn/XiaomiPcManagerPatch/security/advisories/new>

报告里请写清：受影响的文件 / 触发条件 / 影响面（谁能做什么）/ 你建议的修法。

## 这套补丁会改你的机器

| 操作 | 会改什么 | 触发方式 |
| --- | --- | --- |
| `xpm_patch.py patch-installer` | 生成 `*_patched.exe`（白名单等长替换）；原包不动 | 手动 |
| `Install-XiaomiPCManager.ps1` 全流程 | 静默安装电脑管家；写 HKCU/HKLM 多处注册表（机型伪装、`ProductModel`）；停用 `MiDeviceService`；改 `micont_service` 的 `ImagePath`；部署代理 DLL；给官方 DLL 打字节补丁 | 手动（自动提权） |
| `padgate_patch.py apply` | 改 `MiSmartShareDLL.dll` 两处字节（备份 `.bak-padgate`）；`taskkill` 占用进程 | 手动 |

完整清单与回退方式见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) 的「会改什么」与「回退」。

它**不会**做的事（设计约束）：

- ❌ 脚本自身不联网 —— 不下载、不上传任何数据
- ❌ 不分发小米电脑管家安装包，也不改安装包以外的任何小米程序文件（代理 DLL 除外）
- ❌ 不触碰小米云端账号与设备身份
- ❌ 仓库不保存任何日志或机器信息（`.gitignore` 已排除安装日志）

## 第三方 DLL（供应链提示）

`wmi_spoof_msimg32.dll` 是**社区发布的第三方二进制**（自签名，作者 CN=ChsBuffer），
本仓按原样收录、不重编译。它是一个 Detours 代理 DLL，会 hook 你机器上 WMI 的查询返回值。
使用前请自行评估是否信任该来源；来源与版权声明见 [NOTICE](NOTICE)。

## 其它风险

- 补丁版安装包**原厂签名失效**，杀毒软件可能报未知行为 —— 请对照 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) 确认改动范围后再放行。
- 机型伪装会让设备端把这台机器识别为小米机型；由此产生的互联行为风险由使用者自行承担。

## 凭据与日志

**本仓不存放任何凭据与安装日志**（`pcc_install_log.txt` / `install_log.txt` 已被 `.gitignore` 排除）。
如果你在任何地方看到安装日志原文、机器序列号或内网地址进入仓库，
请当作缺陷报上来 —— **不要在公开 Issue 里贴出原文本身**。
