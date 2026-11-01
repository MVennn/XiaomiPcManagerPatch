# AGENTS —— 机器协议

> **一句话**：三条硬规矩 —— **PROGRESS 按逻辑任务分家**、**机器与身份信息不入仓**、
> **有 CodeGraph 就先用 CodeGraph**。其它都能从 [docs/](docs/README.md) 里查到。

---

## 1. PROGRESS：路径由逻辑任务决定，不是物理目录

- 每个逻辑任务目录内有**且仅有一个** `PROGRESS.md`（追加式批次日志）。
  本仓的 `PROGRESS.md` 已被 `.gitignore` 排除，**不入库**。
- 子代理**只写自己的分片文件**（`evidence/agent-<name>.md` 这类），
  **绝不写任何共享文件**。
- 分片写完同步根 `PROGRESS.md`。

## 2. 机器与身份信息不入仓（脱敏红线）

**不许把下面这些写进源码、文档、示例、日志、提交信息**：

| 类别 | 例子 | 处理 |
|---|---|---|
| **安装日志** | `pcc_install_log.txt`、`install_log.txt`（含机器信息） | 整文件不入库（`.gitignore` 已排除） |
| 本机用户目录 | `C:\Users\<你>` / `/home/<你>` | 相对路径或「当前用户目录」 |
| 内网 IP / 计算机名 / MAC / 序列号 | — | 占位符 `<HOST-IP>` / `<HOST-NAME>` |
| 真实邮箱 / 凭据 | — | 哪都不该放 |
| 真机实测原始输出、截图 | 探测输出、补丁 dump | `.work/`（不入库） |

**允许出现**：硬件型号、软件版本号、注册表键名 —— 是结论的一部分，不构成身份泄漏。

**占位符写法**：`<REDACTED-...>`（敏感值）、`<REPLACE-...>`（需要用户自己填的值）、
`<HOST-IP>`（机器标识）。

判断标准：**这段文字贴到公开 Issue 里，会不会暴露某台机器或某个人的身份？**

## 3. CodeGraph

仓库根有 `.codegraph/` 时，**先 `codegraph_explore` 找代码，再 grep**。
没有就跳过 —— 别为此手动建索引。

---

## 其他约定（详见 docs/DOC-RULES.md）

- 每篇文档开头必须有 `> **一句话**：…` 引言块（根 README 与 `docs/release-notes/` 除外）。
- 相对链接；改文档后跑 `python tools/check-docs.py`。
- 提交前跑 `python tools/check-secrets.py --all` —— 脱敏红线的可执行版本。
- `.ps1` 含中文**必须带 UTF-8 BOM**（PowerShell 5.1 按 ANSI 解码无 BOM 文件）；`tools/*.ps1` 纯 ASCII。
- 补丁纪律：字节等长、先备份、临时文件 + 原子替换、特征码命中才写（见 [CONTRIBUTING.md](CONTRIBUTING.md) §2）。
- **不**把小米电脑管家的安装包、解包内容或小米二进制放进仓库。
- 提交信息用 Conventional Commits，**按对象拆行**。
