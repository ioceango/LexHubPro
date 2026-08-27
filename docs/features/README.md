# 需求迭代索引（FEAT）

> 每个需求一个编号目录，命名 `FEAT-<3位序号>-<英文短slug>/`，序号全局单调递增、不复用、不回填。
> 每个目录固定四份文档：`spec.md`、`plan.md`、`checklist.md`、`test-report.md`。
> **新增需求必须先在本表登记，再开始写代码。** 流程见 [`../rules/04-iteration-workflow.md`](../rules/04-iteration-workflow.md)。

## 索引表

| 编号 | 标题 | 状态 | 日期 | 负责人 | 文档 |
|------|------|------|------|--------|------|
| FEAT-001 | 合同审查平台首期（首页/上传审查/报告详情/历史/认证隔离） | 已完成 | 2026-08-26 | Alex | [目录](FEAT-001-contract-review-platform/) · [spec](FEAT-001-contract-review-platform/spec.md) · [plan](FEAT-001-contract-review-platform/plan.md) · [checklist](FEAT-001-contract-review-platform/checklist.md) · [报告](FEAT-001-contract-review-platform/test-report.md) |
| FEAT-002 | vibecoding 工程规范体系（rules + templates + verify.sh） | 已完成 | 2026-08-26 | Alex | [目录](FEAT-002-vibecoding-standards/) · [spec](FEAT-002-vibecoding-standards/spec.md) · [plan](FEAT-002-vibecoding-standards/plan.md) · [checklist](FEAT-002-vibecoding-standards/checklist.md) · [报告](FEAT-002-vibecoding-standards/test-report.md) |
| FEAT-003 | 编号化迭代文档规范生效改造（AGENTS.md + 文档 gate） | 已完成 | 2026-08-26 | Alex | [目录](FEAT-003-numbered-iteration-governance/) · [spec](FEAT-003-numbered-iteration-governance/spec.md) · [plan](FEAT-003-numbered-iteration-governance/plan.md) · [checklist](FEAT-003-numbered-iteration-governance/checklist.md) · [报告](FEAT-003-numbered-iteration-governance/test-report.md) |
| FEAT-004 | 跨工具统一 `.agent/` 规约（单一事实源 + 指针入口 + 门禁扩展） | 已完成 | 2026-08-26 | Alex | [目录](FEAT-004-unified-agent-rules/) · [spec](FEAT-004-unified-agent-rules/spec.md) · [plan](FEAT-004-unified-agent-rules/plan.md) · [checklist](FEAT-004-unified-agent-rules/checklist.md) · [报告](FEAT-004-unified-agent-rules/test-report.md) |
| FEAT-005 | 可插拔认证与对象存储（平台/自建 PG 认证 + 平台/MinIO 存储 + 规约中立化） | 验证中 | 2026-08-27 | Alex | [目录](FEAT-005-pluggable-auth-storage/) · [spec](FEAT-005-pluggable-auth-storage/spec.md) · [plan](FEAT-005-pluggable-auth-storage/plan.md) · [checklist](FEAT-005-pluggable-auth-storage/checklist.md) · [报告](FEAT-005-pluggable-auth-storage/test-report.md) |
| FEAT-006 | 后端四层与表命名规约（api/services/repositories/models + tb_* 注释；废止禁改 models） | 验证中 | 2026-08-27 | Alex | [目录](FEAT-006-backend-layering-table-naming/) · [spec](FEAT-006-backend-layering-table-naming/spec.md) · [plan](FEAT-006-backend-layering-table-naming/plan.md) · [checklist](FEAT-006-backend-layering-table-naming/checklist.md) · [报告](FEAT-006-backend-layering-table-naming/test-report.md) |
| FEAT-007 | 清除平台认证与硬约束，统一为自建登录与自托管架构 | 开发中 | 2026-08-27 | Alex | [目录](FEAT-007-self-hosted-only/) · [spec](FEAT-007-self-hosted-only/spec.md) · [plan](FEAT-007-self-hosted-only/plan.md) · [checklist](FEAT-007-self-hosted-only/checklist.md) · [报告](FEAT-007-self-hosted-only/test-report.md) |
| FEAT-008 | 用户自备 DeepSeek / OpenRouter 模型配置并作为合同审查默认模型 | 已完成 | 2026-08-27 | Alex | [目录](FEAT-008-user-llm-config/) · [spec](FEAT-008-user-llm-config/spec.md) · [plan](FEAT-008-user-llm-config/plan.md) · [checklist](FEAT-008-user-llm-config/checklist.md) · [报告](FEAT-008-user-llm-config/test-report.md) |
| FEAT-009 | 后端分层清理（去脚手架）与表 DDL/ER 目录规范 | 已完成 | 2026-08-28 | Alex | [目录](FEAT-009-backend-layer-cleanup-ddl/) · [spec](FEAT-009-backend-layer-cleanup-ddl/spec.md) · [plan](FEAT-009-backend-layer-cleanup-ddl/plan.md) · [checklist](FEAT-009-backend-layer-cleanup-ddl/checklist.md) · [报告](FEAT-009-backend-layer-cleanup-ddl/test-report.md) |
| FEAT-010 | 前端资源迁移、图片加载优化与 MVC 分层清理 | 已完成 | 2026-08-28 | Alex | [目录](FEAT-010-frontend-assets-mvc/) · [spec](FEAT-010-frontend-assets-mvc/spec.md) · [plan](FEAT-010-frontend-assets-mvc/plan.md) · [checklist](FEAT-010-frontend-assets-mvc/checklist.md) · [报告](FEAT-010-frontend-assets-mvc/test-report.md) |
| FEAT-011 | 规约指针纯路标、细则校准、Grok 遵守 .agent、MCP/Skills 布局 | 已完成 | 2026-08-28 | Alex | [目录](FEAT-011-rules-pointers-mcp-skills/) · [spec](FEAT-011-rules-pointers-mcp-skills/spec.md) · [plan](FEAT-011-rules-pointers-mcp-skills/plan.md) · [checklist](FEAT-011-rules-pointers-mcp-skills/checklist.md) · [报告](FEAT-011-rules-pointers-mcp-skills/test-report.md) |
| FEAT-012 | Git 提交与分支必须对齐 FEAT/BUG 编号目录 | 已完成 | 2026-08-28 | Alex | [目录](FEAT-012-git-commit-branch-rules/) · [spec](FEAT-012-git-commit-branch-rules/spec.md) · [plan](FEAT-012-git-commit-branch-rules/plan.md) · [checklist](FEAT-012-git-commit-branch-rules/checklist.md) · [报告](FEAT-012-git-commit-branch-rules/test-report.md) |
| FEAT-013 | LexHubPro 四视角 code-review skill | 已完成 | 2026-08-28 | Alex | [目录](FEAT-013-code-review-skill/) · [spec](FEAT-013-code-review-skill/spec.md) · [plan](FEAT-013-code-review-skill/plan.md) · [checklist](FEAT-013-code-review-skill/checklist.md) · [报告](FEAT-013-code-review-skill/test-report.md) |

## 状态取值

`规划中` · `spec 待确认` · `plan 待确认` · `开发中` · `验证中` · `已完成` · `已废弃`

## 下一个可用编号

**FEAT-014**（建目录前请先执行 `ls docs/features` 复核，取现有最大号 +1）