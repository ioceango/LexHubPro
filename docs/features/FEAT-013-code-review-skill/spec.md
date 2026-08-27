# Spec：LexHubPro 四视角 code-review skill

## 基本信息

| 项 | 内容 |
|----|------|
| 迭代号 | FEAT-013-code-review-skill |
| 类型 | 需求 |
| 优先级 | P1 |
| 提出人 | 用户 |
| 创建日期 | 2026-08-28 |
| 确认状态 | ✅ 已确认（用户「feat: … 实现」，2026-08-28） |

## 1. 背景与问题

仓库已约定技能正文只放 `.agent/skills/`，但目录里还没有业务 skill。通用 `/review` 不懂本仓库的四层、JWT、MinIO、用户 LLM、表注释与前端 `lib/http.ts`。需要一份按本项目架构与技术栈写的 code-review 流程，让工具用前端、后端、架构、数据库四个视角审同一份改动。

## 2. 范围

### 2.1 本次要做

- 新增 `.agent/skills/code-review/SKILL.md`：可触发的审查流程 + 四视角检查清单（指向 `.agent/` 与 `docs/rules`，不复制红线全文）。
- 更新 `.agent/skills/README.md` 登记该 skill。
- 不把 skill 正文复制进 `.grok/skills`。

### 2.2 本次明确不做

- 不实现 GitHub PR 自动评论机器人。
- 不替代 `scripts/verify.sh` 与 Playwright。
- 不改业务运行时代码与表。
- 不把 `.agent/constraints.md` 全文粘进 skill。

## 3. 用户故事

- 作为开发者，我说「code review / 审查这次改动 / /code-review」，工具按本仓库口径从四个角色出问题清单。
- 作为架构师，我看到分层越界、双轨认证、事务跨 AI 会被标为缺陷，而不是泛泛的风格意见。
- 作为数据库负责人，我看到缺 `tb_*` 注释、缺 DDL 目录、user_id 类型分裂会被抓住。

## 4. 功能需求

| 编号 | 需求描述 | 输入 | 期望输出 |
|------|----------|------|----------|
| F-01 | 自动触发：code review、审查改动、/code-review | 用户话语 | 加载本 skill |
| F-02 | 四视角：前端、后端、架构、数据库 | 改动文件 | 分角色发现，带文件与行号 |
| F-03 | 检查项对齐现行栈 | JWT+MinIO+用户 LLM+四层 | 不按 web-sdk / OIDC / 平台模型审 |
| F-04 | 只读审查 | 默认不改代码 | 除非用户明确要求修 |

## 5. 验收标准

- [x] AC-01：存在 `.agent/skills/code-review/SKILL.md`，frontmatter 含 name/description 与触发语。
- [x] AC-02：流程含架构 / 后端 / 前端 / 数据库四段，且引用 `.agent/architecture.md`、`constraints.md`、`rules.md`、`docs/ddl/database-ddl-er.md`，不整篇复制红线。
- [x] AC-03：输出格式规定严重级别、文件路径、建议；默认不改业务代码。
- [x] AC-04：`.agent/skills/README.md` 列出该 skill；`.grok/skills` 无拷贝。
- [x] AC-05：`bash scripts/verify.sh --docs-only` 通过。
- [x] AC-06：Playwright 截图 S01 起。
- [x] AC-07：每次审查必须在对应 FEAT/BUG 目录下创建 `review-report/R<2位>-<YYYY-MM-DD>.md`，写明发现与改进建议；不得覆盖已有编号文件。

## 6. 影响面

| 维度 | 影响 |
|------|------|
| 页面/接口/表 | 无 |
| 工具行为 | Grok 经 `[skills].paths` 发现本 skill |

## 确认记录

| 日期 | 确认人 | 结论 |
|------|--------|------|
| 2026-08-28 | 用户 | 实现 |
