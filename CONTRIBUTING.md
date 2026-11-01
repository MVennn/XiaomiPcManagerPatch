# 参与贡献

> **一句话**：怎么把补丁跑起来、改脚本守什么规矩、提交前跑什么。

## 跑起来

```powershell
# 一键全流程（自动提权；会改注册表、服务与官方 DLL，先读 docs/ARCHITECTURE.md 的「会改什么」）
.\Install-XiaomiPCManager.ps1

# 或只手动打单个补丁
python xpm_patch.py patch-installer "原版安装包.exe" -o "输出.exe"
python padgate_patch.py status        # 只读
```

需要自备小米电脑管家官方安装包（本仓不分发）；实测基准 6.0.0.39。
参数与退出码见 [docs/TOOLS.md](docs/TOOLS.md)。

## 硬规矩

### 1. 机器与身份相关的信息一律不入仓（脱敏红线）

**不许**把下面这些写进源码、文档、示例、日志、提交信息：

| 类别 | 例子 | 处理 |
|---|---|---|
| 安装日志 | `pcc_install_log.txt`、`install_log.txt`（含机器信息） | 整文件不入库（`.gitignore` 已排除） |
| 本机用户目录 | `C:\Users\<你>\…` | 相对路径或「当前用户目录」 |
| 内网 IP / 计算机名 / MAC / 序列号 | — | 占位符 `<HOST-IP>` 等 |
| 真实邮箱、凭据 | — | 哪都不该放 |

提交前跑 `python tools/check-secrets.py --all` —— 这是红线的可执行版本。

### 2. 补丁纪律

- 字节补丁必须**等长替换**、**先备份后写回**、写回走临时文件 + 原子替换（现有实现即如此，改的时候别退化）。
- 特征码与电脑管家版本绑定：新版本先 `padgate_patch.py status` 验证，命中才写。
- **不把小米电脑管家的安装包、解包内容或任何小米二进制放进本仓**（第三方 DLL 除外，见 [NOTICE](NOTICE)）。

### 3. 格式

- `.ps1` 含中文时**必须带 UTF-8 BOM**（PowerShell 5.1 会把无 BOM 文件按 ANSI 解码）；`tools/*.ps1` 一律纯 ASCII。
- Python 只用标准库（`tools/make_social_preview.py` 例外，需要 numpy + Pillow）。
- 所有文本文件 LF 换行（`.gitattributes` 已锁）。

## 文档

规则见 [docs/DOC-RULES.md](docs/DOC-RULES.md)（单一正本、每篇开头一句话引言块、
索引唯一、孤儿零容忍）。改完跑：

```bash
python tools/check-docs.py
```

## 提交前自检

```bash
# Python 语法
python -c "import ast,glob; [ast.parse(open(f,encoding='utf-8').read(), f) for f in glob.glob('**/*.py', recursive=True)]"

# PowerShell 编码（含中文必须带 BOM）
python -c "import glob,sys; bad=[p for p in glob.glob('**/*.ps1', recursive=True) if any(b>127 for b in open(p,'rb').read()) and open(p,'rb').read(3)!=b'\xef\xbb\xbf']; sys.exit(1 if bad else 0)"

# PowerShell 语法
pwsh -NoProfile -Command '$e=$null; [System.Management.Automation.Language.Parser]::ParseFile((Resolve-Path "Install-XiaomiPCManager.ps1").Path,[ref]$null,[ref]$e)|Out-Null; if($e.Count){$e; exit 1}'

# 文档 + 脱敏
python tools/check-docs.py
python tools/check-secrets.py --all
```

CI（`.github/workflows/ci.yml`）跑的就是这几样。

## 提交信息

Conventional Commits：`feat:` `fix:` `docs:` `chore:` `refactor:` `test:` `perf:`。
多个改动**按对象拆行**（一行一个对象）。
