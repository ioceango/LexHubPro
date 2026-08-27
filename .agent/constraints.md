# .agent/constraints.md — 能力边界与红线

> 本文件规定「不能做什么」。违反本文件任一条即为不合格交付。
> 产品名：**LexHubPro**。认证只有自建邮箱密码 + JWT；对象存储只有 MinIO。

## 1. 不再作为禁改的平台脚手架

下列文件**可以修改或删除**（不再因「平台托管」而冻结）。本迭代只改任务需要的部分，禁止借机重写无关脚手架：

```
app/backend/core/**
app/backend/main.py
app/frontend/index.html
```

- 业务表结构只在 `app/backend/models/`；表目录文档在 `docs/ddl/database-ddl-er.md`。
- 横切能力（如 `trace_id`）优先用路由级依赖 + contextvars。
- 禁止再引入 Lambda handler、平台 OIDC、对外 AI Hub、Stripe。

## 2. 认证、存储与前端访问边界

**必须（always）**
- 认证唯一实现：自建邮箱 + 密码 + JWT。用户与业务表在 `models/`，表名 `tb_<业务>`，经 `repositories/` 访问。隔离按令牌中的 `tenant_id + user_id` 强制过滤，禁止信任请求体里的身份字段。
- 对象存储唯一实现：自建 MinIO。合同文件存私有桶，数据库只持久化 `bucket_name` + `object_key`；下载时换取限时预签名链接。禁止持久化签名 URL。
- 前端访问后端必须走 `lib/http.ts` 及认证/数据/存储封装，禁止页面内散落 `fetch` / `axios`。禁止再引入 web-sdk。
- HTTP 路径用正式资源名：`/api/v1/auth`、`/api/v1/contracts`、`/api/v1/reports`、`/api/v1/storage`。禁止 `local-` 前缀与 `local_` 业务文件名。

**禁止（never）**
- 平台 OIDC、web-sdk `client.auth` / `client.entities` / `client.storage`、平台 OSS、`AUTH_MODE` / `STORAGE_MODE` 双模式。
- 在四层之外再开平行分层。
- 数据库事务跨越 AI 调用、网络请求或对象存储操作。

**先问再做（ask first）**
- 引入新依赖、新第三方服务或新密钥。
- 破坏性 DDL（删列、改名、无默认值的 NOT NULL）。新增 `tb_*` 且含注释、约束与仓储的，按分层落地并在 `plan.md` 记录。
- 变更既有 API 契约或技术选型。
- 需求存在两种以上合理解释时。

## 3. 配置读取要求

- 禁止把可变参数（URL、超时、模型名、限额、路径）硬编码进业务代码。
- 读取动态配置必须使用 `getattr(settings, name, default)`，并校验值是否仍为 `$$占位符$$` 形式。
- 新增或变更配置项必须同步写入 `.env.example`，标注含义、默认值、是否必填。
- JWT 只认 `JWT_SECRET_KEY`；MinIO 项为启动必填。

## 4. 日志与脱敏红线

- 日志**禁止**记录：合同正文、PDF base64、prompt 全文、密钥、签名 URL、完整个人身份信息。
- 需要观测长文本时只记录长度与摘要特征，使用统一脱敏工具。
- 关键路径必须带 `trace_id`，错误响应体与日志共享同一 `trace_id`。
- AI 调用与数据库关键操作必须有埋点（阶段、模型、耗时、结果）。

## 5. 业务硬约束

- 合同上传限制：PDF 格式，15MB / 80 页以内。
- `/api/v1/review/analyze` 前端调用必须设置 `timeout: 600_000`。
- AI 报告展示页必须标注「仅供参考，不构成正式法律意见」免责声明。
- AI 失败对外语义：额度耗尽 → 402（不可重试）；限流/超时/上游 5xx → 503（可重试）；无有效文本 → 422；未知 → 500。

## 6. 视觉

见 `.agent/design.md`。本文件不重复设计 token。

## 7. 交付诚实性红线

- 禁止用占位内容、假成功态、无响应按钮、假支付完成来冒充功能完成。
- 禁止在未真实执行命令的情况下填写测试报告结论。
- 禁止在无法完成时静默降级而不告知；应明确说明阻塞点与已尝试方案。
- 每个 FEAT / BUG 禁止跳过 Playwright 端到端；禁止截图不归档到该迭代 `test-report/` 或不按 `S01` 起编号引用。零 UI 迭代须在 checklist 写豁免并获确认。
