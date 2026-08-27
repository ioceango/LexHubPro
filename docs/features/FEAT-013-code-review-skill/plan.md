# Plan：FEAT-013 code-review skill

## 基本信息

| 项 | 内容 |
|----|------|
| 迭代号 | FEAT-013-code-review-skill |
| 对应 Spec | `./spec.md` |
| 确认状态 | ✅ 已确认 |

## 1. 方案概述

在 `.agent/skills/code-review/SKILL.md` 写可执行的审查流程：先圈定改动与迭代编号，再按架构师 → 后端 → 前端 → DBA 四段检查。条款不重复 `.agent/` 正文，只写「看什么、打开哪份规约、何种现象算缺陷」。输出固定为分级 findings。Grok 已配置 `[skills] paths = [".agent/skills"]`。

### 备选

| 方案 | 采用 |
|------|------|
| A：项目 skill，四视角 + 指向 SSOT | ✅ |
| B：复制通用 `/review`（GitHub PR 编排） | ❌ 不懂本栈 |
| C：把红线全文贴进 skill | ❌ 与 FEAT-011 冲突 |

## 2. 文件

| 文件 | 改动 |
|------|------|
| `.agent/skills/code-review/SKILL.md` | 新增；补充 §7 归档到 `review-report/Rnn-日期.md` |
| `.agent/skills/code-review/references/review-report-template.md` | 新增报告模板 |
| `.agent/skills/README.md` | 登记 |
| 本迭代四文档 + 索引 + `.atoms/` | 同步 |

## 3. 数据库变更

无。

## 4. 实施顺序

1. 写 SKILL.md 与 skills README。
2. 登记 FEAT 索引。
3. docs-only + Playwright。
