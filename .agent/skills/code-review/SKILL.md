---
name: code-review
description: >
  Review LexHubPro diffs as four specialists (architect, FastAPI backend,
  React frontend, PostgreSQL). Use when the user asks for code review, 代码审查,
  审查这次改动, review my changes, review this PR, or /code-review.
---

# LexHubPro code review

只审不改，除非用户明确要求动手修。条款正文在 `.agent/` 与 `docs/rules/`；本 skill 只规定**怎么审、看什么、如何汇报**。

## 0. 开工

1. 圈定范围：用户点名的文件 / `FEAT-NNN` / `BUG-NNN` / 工作区改动。无 git 时读用户点名的路径或当前迭代目录，不要假装有 diff。
2. 若范围含编号，先读该目录 `spec.md`、`plan.md`，对照 AC，不要用过时的平台 OIDC / web-sdk / 平台模型口径。
3. 必读（按需跳进相关小节，不要整本背诵）：
   - `.agent/constraints.md` `.agent/architecture.md` `.agent/rules.md` `.agent/workflow.md`
   - 涉及 UI：`.agent/design.md`
   - 涉及表：`docs/ddl/database-ddl-er.md`、`docs/rules/07-database-acid.md`
   - 涉及提交：`docs/rules/09-git-commit-and-branch.md`
4. 四段都要过：即使本次只改前端，也要扫一眼是否误伤分层、归属或契约。某段无发现就写「本视角无阻塞项」，不要编问题凑数。

严重级别：`阻塞`（违反红线或会坏主路径）· `严重`（正确性/隔离/数据完整性）· `建议`（可维护性）。

## 1. 架构师

打开 `.agent/architecture.md`。本栈：React 18 + Vite + FastAPI + SQLAlchemy Async + PostgreSQL + JWT + MinIO + 用户自备 LLM。

| 查 | 缺陷信号 |
|----|----------|
| 四层单向 `api → services → repositories → models` | api 碰 ORM/SQL/AI/MinIO；service import fastapi；仓储做业务判断或自行 commit |
| 无平行分层 | 新开 `routers/`、`local_*`、第二套 auth/storage 模式 |
| 契约与表分离 | 把 `schemas/` 与 `models/` 合并；HTTP 当表模型用 |
| 适配器 | 审查/登录里写 `if provider ==`；直连 OpenAI SDK 绕过 `llm_providers/` |
| 迭代治理 | 改业务代码但无已确认 spec/plan；缺四文档；改表不改 DDL 目录 |
| 扩展点 | 新表未走 models→repo→service→api；新 LLM 厂商改审查主流程而不是注册表 |

先问再做（出现即至少「严重」，未在 plan 声明则升「阻塞」）：新依赖/新密钥、破坏性 DDL、改公共 API、换技术栈。

## 2. 后端（FastAPI）

打开 `.agent/constraints.md`、`docs/rules/06-backend-layering.md`。

| 查 | 缺陷信号 |
|----|----------|
| 归属 | 信任请求体 `user_id`/`tenant_id`；仓储查询不带 Owner 过滤 |
| 身份类型 | 进程内 `user_id` 再用 `str` 与 `int` 混用（JWT `sub` 仅签发时 `str`，见 BUG-007） |
| 事务 | `async with session.begin()` 里调 AI、MinIO、SMTP、HTTP |
| 审查链路 | 无启用模型未 409；扫描件不足 200 字未 422；额度/限流未映射 402/503 |
| AI | 只读 `message.content` 忽略 `reasoning_content`；日志打 prompt/合同正文/Key |
| 配置 | 超时、模型名、桶名、限额硬编码；`settings.x` 裸读无 `getattr` 默认值 |
| 错误 | 一律 500；对外返回堆栈/SQL/上游原文 |
| 测试 | Bug 无 `# BUG-NNN 回归`；单测打真实模型网关 |

## 3. 前端（React）

打开 `.agent/architecture.md` §4.1、`.agent/design.md`。

| 查 | 缺陷信号 |
|----|----------|
| MVC | `pages/` 散落 `fetch`/`axios`；组件自己调后端；领域 `JSON.parse` 不走 `lib/review.ts` |
| 出口 | 不经 `lib/http.ts` / `auth-provider` / `data-access` / `storage-access` / `user-llm` |
| 禁引入 | `@metagptx/web-sdk`、`client.entities`、`client.auth` |
| 认证三态 | 把 loading 当 anonymous 导致闪登录 |
| 失败 | 业务 4xx/5xx 整页踢去登录，而不是错误+重试 |
| 审查 | `/review/analyze` 超时不是 600s；无模型未拦截 |
| 视觉 | 渐变字、蓝紫霓虹、改 `components/ui` 公共 API；风险色没用高/中/低 token |
| 资源 | 品牌图再走平台 CDN；大 PNG 不经 `src/assets` |

涉及 UI 的 FEAT/BUG：未跑 Playwright 或截图不按 `test-report/S01-*.png` 归档，标阻塞（流程）。

## 4. 数据库专家

打开 `docs/ddl/database-ddl-er.md` 与 `docs/rules/07-database-acid.md`。

| 查 | 缺陷信号 |
|----|----------|
| 命名 | 新表不叫 `tb_*`；业务文件 `local_` |
| 注释 | ORM 无表/列 `comment`；DDL 无 `COMMENT ON`；改表不同步目录文档 |
| 类型与 FK | `user_id` 与 `tb_user.id` 不是 integer FK；合同/报告缺少用户或合同外键 |
| 基数 | 把 `contract_id` 做成唯一从而禁止多轮审查 |
| 约束 | 状态/分数/角色无 CHECK；无归属索引 `(tenant_id, user_id, …)` |
| 迁移 | 只改 ORM，靠 `create_all` 改存量表类型（必须 bootstrap `ALTER`） |
| 隔离 | 删合同不级联报告；跨用户能读到行 |
| 事务 | 长事务跨 AI；提交前当成功告诉用户 |

存量迁移若可能毁掉非数字 `user_id` 或孤儿行，必须在审查里写明启动失败策略，禁止静默 `USING` 丢数据。

## 5. 横切（每份 diff 都扫）

- 日志：合同正文、PDF base64、prompt 全文、密钥、签名 URL。
- Git：有 `.git` 时提交/分支是否带同一 `FEAT-NNN`/`BUG-NNN`（09）。
- 验证：声称完成但未跑 `verify.sh --docs-only` 或对应测试。
- 测试报告：未执行却写通过。

## 6. 汇报格式

```markdown
## 结论
<一句话：能否合入 / 必须先修哪些阻塞>

## 范围
<文件或迭代编号>

## 发现
### [阻塞] 短标题
- 视角：架构 | 后端 | 前端 | 数据库
- 位置：path:line
- 问题：…
- 依据：`.agent/…` 或 `docs/rules/…` 的哪一条
- 建议：…

### [严重] …
### [建议] …
```

无发现时明确写「四视角均无阻塞/严重项」。不要给无关文件写空话。不要在审查默认路径里改业务代码。

## 7. 归档到迭代目录（每次必须）

审查结束后**必须**把本次汇报写入对应编号目录，不得只停留在对话里。这是审查产物，不是改业务代码。

### 7.1 落到哪个目录

| 范围 | 路径 |
|------|------|
| 需求 | `docs/features/FEAT-<3位>-<slug>/review-report/` |
| 缺陷 | `docs/bug-fix/BUG-<3位>-<slug>/review-report/` |

与 `test-report/`（Playwright 截图）并列，**不要**把审查记录写进 `test-report.md`。

编号来源（按序）：用户点名的 `FEAT-NNN`/`BUG-NNN` → 改动文件所在迭代目录 → 当前对话正在实施的迭代。仍无法唯一确定时**先问用户**，禁止写到错误目录，禁止省略归档。

### 7.2 文件名：`R<2位>-<YYYY-MM-DD>.md`

1. `ls` 该 `review-report/`（没有则创建）。
2. 已有 `R01-*.md`、`R02-*.md`… 取最大序号 +1；没有则从 `R01` 起。
3. 日期用审查当天（仓库约定的本地日历日），四位年-两位月-两位日。
4. 同一天多次审查继续加序号：`R01-2026-08-28.md`、`R02-2026-08-28.md`。
5. 禁止覆盖已有文件；禁止无序号或无日期。

正文按 `.agent/skills/code-review/references/review-report-template.md` 填写。§6 的结论/范围/发现必须原样进文件，并增加「改进建议」节（每条建议对应一条发现，或写「无额外建议」）。只写实际看过的范围，禁止编造未审查的问题。
