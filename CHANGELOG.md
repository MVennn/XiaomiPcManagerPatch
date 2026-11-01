# 更新日志

> **一句话**：本仓的开发者记录 —— 每个版本改了什么、为什么、怎么验。
> 顶部的版本命名规则是**摘要**，**正本见 [docs/VERSIONING.md](docs/VERSIONING.md)**。

本仓对外可见的重要变更记录在此。格式参考 Keep a Changelog。

## [未发布]

### Added

- 门面对齐系列仓通用规则（对照 QQBotStack / WindowsRemoteOps 同款）：
  - 根 `README.md` 重写为七段式门面；原 README 的实测记录**下沉不删除**——
    定位过程与 A/B 对照进 `docs/RESEARCH.md`，注意事项进 `docs/PITFALLS.md`
  - 新增 `docs/`（ARCHITECTURE / TOOLS / PITFALLS / RESEARCH / DOC-RULES / VERSIONING /
    README 索引 / release-notes 模板）
  - 新增 `CONTRIBUTING.md`、`SECURITY.md`、`NOTICE`、`AGENTS.md`
  - 新增 `.github/ISSUE_TEMPLATE/`（bug_report / feature_request / config）与 CI（`ci.yml`）
  - 新增 `assets/` 门面（icon.svg / logo.png / social-preview.png）与 `tools/make_social_preview.py`
  - 新增 `tools/check-docs.py`（守卫分叉副本，与全系列奇偶同步）、`.gitattributes`

## [0.1.0] - 2026-11-01

### Added

- 建仓：导入脱敏后的小米电脑管家（非小米电脑）补丁工具
  - `xpm_patch.py` —— 安装包机型白名单补丁 + 运行时机型伪装
  - `padgate_patch.py` —— 平板镜像多显示器 / 独显拦截补丁
  - `Install-XiaomiPCManager.ps1` —— 一键补丁 / 安装脚本
  - `wmi_spoof_msimg32.dll` —— 社区 WMI 伪装代理 DLL（作者 CN=ChsBuffer）
  - `README.md` —— 原理、用法与实测记录
- 新增 `.gitignore`（安装日志与补丁产物不入库）、`LICENSE`（Apache-2.0）、
  `tools/check-secrets.py`（敏感信息扫描守卫）
