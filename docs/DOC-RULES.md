# 文档规则

> **一句话**：docs/ 下的文档怎么分类、怎么互相引用、怎么脱敏、改动时连带改哪些 ——
> 本篇只管「怎么写、怎么保持一致」，不承载任何具体技术规则。

---

## 1. 分类与定位

docs/ 分四类（索引见 [README.md](README.md)）：

| 类别 | 收什么 | 现有成员 |
|---|---|---|
| 架构与机制 | 三层限制、补丁机制、边界与回退 | ARCHITECTURE、RESEARCH |
| 工具专项 | 文件清单、参数与退出码、踩坑 | TOOLS、PITFALLS |
| 流程与规范 | 版本、文档规则 | DOC-RULES、VERSIONING |
| 参考资料 | Release 说明 | release-notes/ |

每篇文档开头必须有一个 **「一句话」引言块**（`> **一句话**：…`）。
**例外**：根 `README.md` 与 `docs/release-notes/` 下的正文。

### 文件命名：全大写 + 连字符

`docs/` 下的 `.md` 一律 **全大写 + 连字符**：`ARCHITECTURE.md`、`DOC-RULES.md`。
混用驼峰或下划线会让索引排序和全仓搜索都跟着散。

改名三步：① `git mv` 改名；② 全仓 grep 旧文件名同步引用；③ 跑 `python tools/check-docs.py`。

例外：`docs/release-notes/` 下的文件名是版本号本身（`0.1.0.md`），**不带 `v`** ——
`v` 前缀只属于发版 tag。

## 2. 脱敏纪律（本仓红线）

**文档与脚本注释里不出现任何能定位到某台机器或某个人的信息。** 这条比格式规则优先级高。

| 不许出现 | 写成 |
|---|---|
| 安装日志原文（`pcc_install_log.txt` / `install_log.txt` 含机器信息，整文件不入库） | 只写结论 |
| 本机用户目录（`C:\Users\<真实用户名>\…`） | 相对路径或「当前用户目录」 |
| 内网 IP / 计算机名 / MAC / 序列号 | `<HOST-IP>` / `<HOST-NAME>` 等占位符 |
| 真实邮箱 | `<REDACTED-EMAIL>` |
| 真机实测原始输出、截图 | 只放本地 `.work/`，不入库 |

**允许出现**：硬件型号（如网卡、主板型号）、软件版本号、注册表键名 —— 这些是结论的一部分，不构成身份泄漏。

提交前跑 `python tools/check-secrets.py --all`。判断标准：
**这段文字贴到公开 Issue 里，会不会暴露某台机器或某个人的身份？**

## 3. 单一正本原则

**每条规则只在一篇文档里定义；其余位置只允许一句话概述 + 指向正本的链接。**

| 规则 | 正本 |
|---|---|
| 三层限制、补丁机制、会改什么、回退 | [ARCHITECTURE.md](ARCHITECTURE.md) |
| 文件清单、参数与退出码、版本适配台账 | [TOOLS.md](TOOLS.md) |
| 定位过程、实测数据、剩余问题 | [RESEARCH.md](RESEARCH.md) |
| 踩过的坑与「下次怎么避」 | [PITFALLS.md](PITFALLS.md) |
| 版本晋升、不发版不动版本号 | [VERSIONING.md](VERSIONING.md) |

## 4. 链接纪律

- 统一用**相对链接 + 锚点**，不用绝对路径。
- 改 / 删 / 合并文档后双向点验：出链目标还在、入链改到新位置。**禁止只删文档不改引用方**。
- 历史记录里的旧文件名可保留原样；正文中指向现役文档的链接必须指向现役文档。

## 5. 变更触发矩阵

| 变更 | 必须同步 |
|---|---|
| **修一个缺陷** | [PITFALLS.md](PITFALLS.md) 补一条 **现象 → 根因 → 怎么避**；CHANGELOG 不算补文档 |
| 新增 / 删除脚本 | [TOOLS.md](TOOLS.md) 文件清单与参数表、[ARCHITECTURE.md](ARCHITECTURE.md) 的「会改什么」表 |
| 补丁机制变化（特征码、注册表落点） | [ARCHITECTURE.md](ARCHITECTURE.md)，新版本实测数据进 [RESEARCH.md](RESEARCH.md) |
| 适配新的电脑管家版本 | [TOOLS.md](TOOLS.md) §6 台账、[RESEARCH.md](RESEARCH.md) 追加记录 |
| 发版 | 根 CHANGELOG、`docs/release-notes/<版本>.md` |
| 改名 / 新增 / 删除文档 | [README.md](README.md) 索引 + 全仓 grep 旧文件名 |

## 6. 体量预算与样例时效

- **单篇 ≤ 800 行。** 超了按「正文档 + 踩坑史」拆。
- 带版本标注的实测记录可容忍过时（那是历史记录，[RESEARCH.md](RESEARCH.md) 的定位就在此）；
  **文件清单、会改什么、版本适配台账**必须随代码同步。

## 7. 索引维护与孤儿零容忍

- [README.md](README.md) 是 docs/ 的唯一索引，新增 / 删除 / 改名必须同步。
- **孤儿文档零容忍**：新文档必须至少被一处既有文档引用。
