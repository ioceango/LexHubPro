# 缺陷迭代索引（BUG）

> 每个 Bug 一个编号目录，命名 `BUG-<3位序号>-<英文短slug>/`，序号全局单调递增、不复用、不回填。
> 每个目录固定四份文档：`spec.md`、`plan.md`、`checklist.md`、`test-report.md`。
> **每个 Bug 修复必须补一条回归用例**，用例注释注明本迭代编号。流程见 [`../rules/04-iteration-workflow.md`](../rules/04-iteration-workflow.md)。

## 索引表

| 编号 | 标题 | 严重级别 | 状态 | 日期 | 负责人 | 文档 |
|------|------|----------|------|------|--------|------|
| BUG-001 | 登出返回 500 且 OIDC 登出回跳页缺失 | 阻塞 | 已修复 | 2026-08-26 | Alex | [目录](BUG-001-logout-500/) · [spec](BUG-001-logout-500/spec.md) · [plan](BUG-001-logout-500/plan.md) · [checklist](BUG-001-logout-500/checklist.md) · [报告](BUG-001-logout-500/test-report.md) |
| BUG-002 | AI 审查合同失败（额度不足 403 被吞成 500） | 阻塞 | 已修复 | 2026-08-26 | Alex | [目录](BUG-002-ai-review-failure/) · [spec](BUG-002-ai-review-failure/spec.md) · [plan](BUG-002-ai-review-failure/plan.md) · [checklist](BUG-002-ai-review-failure/checklist.md) · [报告](BUG-002-ai-review-failure/test-report.md) |
| BUG-003 | 启动 COMMENT ON 使用绑定参数导致 backend 崩溃、frontend 无法健康拉起 | 阻塞 | 已修复 | 2026-08-27 | Alex | [目录](BUG-003-startup-comment-sql/) · [spec](BUG-003-startup-comment-sql/spec.md) · [plan](BUG-003-startup-comment-sql/plan.md) · [checklist](BUG-003-startup-comment-sql/checklist.md) · [报告](BUG-003-startup-comment-sql/test-report.md) |
| BUG-004 | 注册缺邮箱约束与验证码邮件，成功提示不清，登录注册无密码可见开关 | 严重 | 已修复 | 2026-08-27 | Alex | [目录](BUG-004-register-email-ux/) · [spec](BUG-004-register-email-ux/spec.md) · [plan](BUG-004-register-email-ux/plan.md) · [checklist](BUG-004-register-email-ux/checklist.md) · [报告](BUG-004-register-email-ux/test-report.md) |
| BUG-005 | SMTP 已配置但已存在邮箱再次注册不发验证码 | 严重 | 已修复 | 2026-08-27 | Alex | [目录](BUG-005-smtp-verify-code-not-sent/) · [spec](BUG-005-smtp-verify-code-not-sent/spec.md) · [plan](BUG-005-smtp-verify-code-not-sent/plan.md) · [checklist](BUG-005-smtp-verify-code-not-sent/checklist.md) · [报告](BUG-005-smtp-verify-code-not-sent/test-report.md) |
| BUG-006 | 已配置自定义模型后合同审查因 Session 重复 begin 返回 500 | 阻塞 | 已修复 | 2026-08-27 | Alex | [目录](BUG-006-review-tx-already-begun/) · [spec](BUG-006-review-tx-already-begun/spec.md) · [plan](BUG-006-review-tx-already-begun/plan.md) · [checklist](BUG-006-review-tx-already-begun/checklist.md) · [报告](BUG-006-review-tx-already-begun/test-report.md) |
| BUG-007 | 合同与审查报告 user_id 类型与用户表不一致且无外键 | 严重 | 已修复 | 2026-08-28 | Alex | [目录](BUG-007-contract-report-user-id-fk/) · [spec](BUG-007-contract-report-user-id-fk/spec.md) · [plan](BUG-007-contract-report-user-id-fk/plan.md) · [checklist](BUG-007-contract-report-user-id-fk/checklist.md) · [报告](BUG-007-contract-report-user-id-fk/test-report.md) |

## 严重级别取值

`阻塞`（功能完全不可用） · `严重`（主流程受损） · `一般`（局部异常） · `轻微`（体验问题）

## 状态取值

`已报告` · `定位中` · `spec 待确认` · `plan 待确认` · `修复中` · `验证中` · `已修复` · `不予修复`

## 下一个可用编号

**BUG-008**（建目录前请先执行 `ls docs/bug-fix` 复核，取现有最大号 +1）