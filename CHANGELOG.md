# 更新日志

> **一句话**：本仓的开发者记录 —— 每个版本改了什么、为什么、怎么验。
> 顶部的版本命名规则是**摘要**，**正本见 [docs/VERSIONING.md](docs/VERSIONING.md)**。

本仓对外可见的重要变更记录在此。格式参考 Keep a Changelog。

## [未发布]

### 门禁脚本 GBK 控制台自毁修复（2026-11-04）

- 修 `tools/make_social_preview.py` 的结论行 `✓` / `✗` / `⚠` → ASCII `[OK]` / `[FAIL]` / `[!]`：Windows 中文控制台
  （cp936）下这些字符不在 GBK 码表，`print` 抛 `UnicodeEncodeError`，脚本即便检查全过也以
  **退出码 1** 结束；`python -I` 会忽略 `PYTHONIOENCODING` / `PYTHONUTF8`，环境变量救不回来，
  只能改脚本本身。
- 入口补兜底 `if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(errors="replace")`：
  以后任何非 GBK 字符降级成 `?`，不再让门禁误判失败。
- 验证：`python -I` 逐个跑上述脚本 → `[OK] …`、退出码 0、无 traceback；反证：把 `✓` 改回原样，
  同一命令退出码 1 并抛 `UnicodeEncodeError`。

### 中文系统编码与文档订正（2026-11-04）

- `xpm_patch.py` 读取本机型号时给 PowerShell 命令加
  `[Console]::OutputEncoding=[System.Text.Encoding]::UTF8`（原先按 UTF-8 解码 cp936 输出，
  中文 DMI 机型字符串会乱码/删空，白名单失效或误报「WMI 返回空」）
- `docs/TOOLS.md` 订正 `-o` 与输入同路径的实际行为（原地改写 + 先备份 `.bak`，不是「拒绝」）
- `docs/ARCHITECTURE.md` 订正 `ProductModel` 落点（`SOFTWARE\MI\MiDeviceService`，
  不是 `SOFTWARE\MI\Driver`）

### P3 清理（2026-11-04 审查遗留项）

- `xpm_patch.py` / `padgate_patch.py` 安装根支持 `XPM_INSTALL_ROOT` 环境变量覆盖
  （自定义安装路径不再不可用）
- `set_spoof_model` 对写入失败计数并在 stderr 告警（非管理员时 HKLM 写不进去，
  不再只打印「已写 N 处」的半成品）
- `Install-XiaomiPCManager.ps1` 改 `micont_service` ImagePath 前把原值写进日志
- `docs/ARCHITECTURE.md` / `docs/PITFALLS.md` 订正 `-ModelOnly` 的实际范围
  （含 4.5/4.6/4.65：WMI DLL、服务参数、padgate 补丁）
- `.gitignore` 挡原版安装包名（`XiaomiPCManager*.exe`）
- 两处 `open().read()` 改 `with` 上下文（`xpm_patch.py` / `padgate_patch.py`）

## [0.1.0] - 2026-11-01

面向用户的说明见 [docs/release-notes/0.1.0.md](docs/release-notes/0.1.0.md)。

### Added

- 建仓：导入脱敏后的小米电脑管家（非小米电脑）补丁工具
  - `xpm_patch.py` —— 安装包机型白名单补丁 + 运行时机型伪装
  - `padgate_patch.py` —— 平板镜像多显示器 / 独显拦截补丁
  - `Install-XiaomiPCManager.ps1` —— 一键补丁 / 安装脚本
  - `wmi_spoof_msimg32.dll` —— 社区 WMI 伪装代理 DLL（作者 CN=ChsBuffer）
  - `README.md` —— 原理、用法与实测记录
- 新增 `.gitignore`（安装日志与补丁产物不入库）、`LICENSE`（Apache-2.0）、
  `tools/check-secrets.py`（敏感信息扫描守卫）
- 门面对齐系列仓通用规则（对照 QQBotStack / WindowsRemoteOps 同款）：
  - 根 `README.md` 重写为七段式门面；原 README 的实测记录**下沉不删除**——
    定位过程与 A/B 对照进 `docs/RESEARCH.md`，注意事项进 `docs/PITFALLS.md`
  - 新增 `docs/`（ARCHITECTURE / TOOLS / PITFALLS / RESEARCH / DOC-RULES / VERSIONING /
    README 索引 / release-notes 模板）
  - 新增 `CONTRIBUTING.md`、`SECURITY.md`、`NOTICE`、`AGENTS.md`
  - 新增 `.github/ISSUE_TEMPLATE/`（bug_report / feature_request / config）与 CI（`ci.yml`）
  - 新增 `assets/` 门面（icon.svg / logo.png / social-preview.png）与 `tools/make_social_preview.py`
  - 新增 `tools/check-docs.py`（守卫分叉副本，与全系列奇偶同步）、`.gitattributes`
