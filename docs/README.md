# docs/ 索引

> **一句话**：这里只有索引与定位，不放正文 —— 每篇文档一句话说明「它管什么」，
> 规则本身按 [DOC-RULES.md](DOC-RULES.md) 的单一正本原则只在对应文档里定义。

文档分四类。每篇开头都有一个「一句话」引言块，先看它再决定要不要往下读。
带 **（正本）** 标记的文档是该主题的**唯一权威定义处**；别处只留一句话概述 + 指向它的链接。

---

## 一、架构与机制

| 文档 | 一句话定位 |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | 边界（**正本**）：三层限制与对应补丁、每个补丁改了哪里、会动机器哪些状态、怎么回退、版本适配 |
| [RESEARCH.md](RESEARCH.md) | 定位过程与实测记录：`--model=0` 的发现、Frida 定位与特征码、异常码对照、A/B 对照、剩余问题 |

## 二、工具专项

| 文档 | 一句话定位 |
|---|---|
| [TOOLS.md](TOOLS.md) | 工具清单（**正本**）：每个文件是什么、脚本参数与退出码、版本适配台账 |
| [PITFALLS.md](PITFALLS.md) | 踩坑总汇（**正本**）：每条写清「现象 → 根因 → 怎么避」，现象那一行即搜索词 |

## 三、流程与规范

| 文档 | 一句话定位 |
|---|---|
| [DOC-RULES.md](DOC-RULES.md) | 文档规则（**正本**）：分类定位、脱敏纪律、单一正本映射表、链接纪律、变更触发矩阵、孤儿零容忍 |
| [VERSIONING.md](VERSIONING.md) | 版本规则（**正本**）：三段式进位、什么算功能更新、不发版不动号 |

## 四、参考资料

| 位置 | 一句话定位 |
|---|---|
| 仓库根 [README.md](../README.md) | 门面：这是什么、环境要求、使用、反馈、免责声明、开源鸣谢、许可证 |
| 仓库根 [AGENTS.md](../AGENTS.md) | 机器协议：PROGRESS 归属、脱敏红线、CodeGraph |
| 仓库根 [CONTRIBUTING.md](../CONTRIBUTING.md) | 参与贡献：怎么跑起来、改脚本守什么规矩、提交前跑什么 |
| 仓库根 [SECURITY.md](../SECURITY.md) | 安全策略：安全问题怎么报、这套补丁会改机器哪些状态、第三方 DLL 提示 |
| 仓库根 [CHANGELOG.md](../CHANGELOG.md) | 开发者记录；**版本号本身**在这里维护，**进位规则**见 [VERSIONING.md](VERSIONING.md) |
| 仓库根 [PROGRESS.md](../PROGRESS.md) | 本仓进度台账（追加式批次日志，不入库） |
| 仓库根 [NOTICE](../NOTICE) | 第三方声明：WMI 伪装 DLL 的来源与版权 |
| 仓库根 [LICENSE](../LICENSE) | 许可证全文（**Apache-2.0**） |
| [release-notes/](release-notes/README.md) | 面向使用者的 Release 说明，**文件名 = 版本号**（不带 `v` 前缀）；格式规范在它的 README |

---

> 新增 / 删除文档后**必须同步更新本索引**（规则见 [DOC-RULES.md](DOC-RULES.md)）；
> 新文档至少要被一处既有文档引用，不允许孤儿。
