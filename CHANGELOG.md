# 更新日志

本仓对外可见的重要变更记录在此。格式参考 Keep a Changelog。

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
