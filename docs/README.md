# LexHubPro 工程规范索引（Vibecoding Rules）

本目录是 **LexHubPro** 项目的开发规则与流程模板集合。**所有需求与 Bug 迭代都必须遵循本目录规范**。

## 规范三层关系（执行优先级）

| 层 | 位置 | 读者 | 职责 |
|----|------|------|------|
| 执行硬约束 | [`.agent/`](../.agent/README.md) | AI 编码工具 | **单一事实源**；任何冲突以此为准 |
| 工具入口 | [`AGENTS.md`](../AGENTS.md)、[`CLAUDE.md`](../CLAUDE.md)、[`.grok/rules/`](../.grok/rules/00-lexhubpro-rules.md) | 各工具自动加载 | **纯路标**：只含必读清单与验证命令，禁止抄写红线条款 |
| 细则全文 | 本目录 `rules/0X-*.md` | 人与工具展开阅读 | 场景、范例与检查清单；**不得**与 `.agent/` 矛盾，矛盾时改本目录 |

技能包权威目录：`.agent/skills/`。MCP 通用清单：仓库根 `.mcp.json`；Grok 专有超时/环境变量写在 `.grok/config.toml`。

本目录 01 / 03 / 05 / 06 已按 FEAT-011 与现行 JWT + MinIO + 用户自备模型对齐（不再把 web-sdk / AIHub / claude-opus-5 / `routers/` 当作现行方案）。

## 技术栈基线（已确认，不得擅自变更）

| 层次 | 技术选型 | 说明 |
|------|----------|------|
| 前端 | React 18 + TypeScript + Vite + shadcn/ui + Tailwind CSS | 现存栈，**保持不变，不引入 Vue** |
| 后端 | FastAPI + SQLAlchemy Async + PostgreSQL | 与 Atoms Cloud 后端脚手架一致 |
| 认证 | 自建邮箱密码 + JWT | 用户/业务表落 `models/`，表名 `tb_*` |
| 存储 | MinIO | 仅持久化 `object_key`，禁止持久化签名 URL |
| AI | 用户自备 DeepSeek / OpenRouter，审查只用当前启用的一个模型 | 无平台模型兜底 |
| 部署 | Docker Compose 自托管 | 认证 JWT + MinIO |

## 规则文档

| 编号 | 文档 | 内容 |
|------|------|------|
| 01 | [开发规范总纲](rules/01-development-standards.md) | 分层架构、设计模式使用场景、高内聚低耦合、禁止堆砌代码判定标准、注释与命名 |
| 02 | [日志与链路追踪规范](rules/02-logging-and-tracing.md) | 日志分级、`trace_id` 贯穿、AI/DB 关键埋点、错误上报与脱敏 |
| 03 | [配置管理规范](rules/03-configuration.md) | 可配置项清单、`.env.example`、禁止硬编码、平台注入变量保护 |
| 04 | [需求与 Bug 迭代流程](rules/04-iteration-workflow.md) | `spec.md` → `plan.md` → 用户确认 → 开发 → 验证 → 报告 |
| 05 | [自动化测试验证规范](rules/05-testing-and-automation.md) | 测试分层、用例编写要求、lint/build/测试执行顺序、报告生成 |
| 06 | [后端分层规范（FastAPI + PostgreSQL）](rules/06-backend-layering.md) | router / service / repository / model 职责与禁止事项、事务边界 |
| 07 | [数据库设计规范（ACID）](rules/07-database-acid.md) | 事务边界、隔离级别、约束与索引、并发写入与幂等；改表须同步 [DDL/ER 目录](ddl/database-ddl-er.md) |
| 08 | [部署规范](rules/08-deployment.md) | 平台 Publish 流程 + Docker Compose 自托管参考 |
| 09 | [Git 提交与分支规范](rules/09-git-commit-and-branch.md) | 提交/分支必须对齐 FEAT/BUG 编号目录；单迭代单分支；revert 回滚 |

## 文档模板

| 模板 | 用途 | 产出位置 |
|------|------|----------|
| [spec-template.md](templates/spec-template.md) | 需求/Bug 规格说明 | `<迭代目录>/spec.md` |
| [plan-template.md](templates/plan-template.md) | 技术实现方案与任务拆分 | `<迭代目录>/plan.md` |
| [checklist-template.md](templates/checklist-template.md) | 完成度与验证清单 | `<迭代目录>/checklist.md` |
| [test-report-template.md](templates/test-report-template.md) | 测试验证报告 | `<迭代目录>/test-report.md` |

## 迭代目录约定（编号目录制）

```
docs/
├── features/                        # 需求
│   ├── README.md                    # 需求索引（新增需求必须登记）
│   └── FEAT-001-contract-review-platform/
│       ├── spec.md                  # 第 1 步：写完等用户确认
│       ├── plan.md                  # 第 2 步：写完等用户确认
│       ├── checklist.md             # 第 3 步：开发同步勾选
│       └── test-report.md           # 第 4 步：验证后生成
└── bug-fix/                         # Bug 修复
    ├── README.md                    # 缺陷索引（新增 Bug 必须登记）
    └── BUG-002-ai-review-failure/
        ├── spec.md
        ├── plan.md
        ├── checklist.md
        └── test-report.md
```

- 需求目录：`docs/features/FEAT-<3位序号>-<英文短slug>/`
- Bug 目录：`docs/bug-fix/BUG-<3位序号>-<英文短slug>/`
- 序号全局单调递增、不复用；四份文档缺一不可且不得留占位。
- 详细规则见 [04 迭代流程](rules/04-iteration-workflow.md#2-目录与命名编号目录制强约束)，由 `bash scripts/verify.sh --docs-only` 强制校验。

## AI 编码工具约束入口

所有 AI 编码工具统一经指针进入 [`.agent/`](../.agent/README.md)：

- 通用 / Codex / dsh / Cursor 等：根 [`AGENTS.md`](../AGENTS.md)
- Claude Code：[`CLAUDE.md`](../CLAUDE.md)
- Grok Build / Grok CLI：根 `AGENTS.md` **加上** [`.grok/rules/00-lexhubpro-rules.md`](../.grok/rules/00-lexhubpro-rules.md)（Grok 官方始终扫描 `.grok/rules/`，故该指针必须保留）

指针不含独立规则。执行以 `.agent/` 为准。

## 硬性红线（违反即视为交付不合格）

1. **未经用户确认 `spec.md` 与 `plan.md`，不得开始写业务代码。**
2. 产品名 LexHubPro。认证仅自建 JWT，存储仅 MinIO。禁止平台 OIDC / web-sdk / entities / 平台 OSS。
3. 后端四层：`api → services → repositories → models`；新表 `tb_<业务>`，表与字段必须有用途 comment，DDL 含 COMMENT ON。禁止 `local_` 业务文件名。前端访问后端必须走统一封装。
4. 数据库事务不得跨越 AI 调用（见 06、07）。
5. 任何可变参数（URL、超时、模型名、限额）不得硬编码在业务代码里（见 03）。
6. 交付前必须通过：前端 `pnpm run lint && pnpm run build`；后端 `python -m py_compile` + 已有测试。