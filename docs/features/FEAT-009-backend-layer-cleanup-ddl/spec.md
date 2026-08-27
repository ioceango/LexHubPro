# Spec：后端分层清理与表结构目录

## 基本信息

| 项 | 内容 |
|----|------|
| 迭代号 | FEAT-009-backend-layer-cleanup-ddl |
| 类型 | 需求 |
| 优先级 | P1 |
| 提出人 | 用户 |
| 创建日期 | 2026-08-28 |
| 确认状态 | ✅ 已确认（用户指定 FEAT-009 范围，2026-08-28） |

## 1. 背景与问题

后端目录看起来重复，实际是四层规范叠了 Atoms 脚手架。对外还挂着文生图/管理改环境变量等与合同审查无关的接口；OIDC 代码仍留在认证基建里。缺少一份可长期维护的表 DDL 与 ER 图目录，后续改表容易只改 ORM 不改文档。

## 2. 范围

### 2.1 本次要做

- 在架构规约中写清目录地图：四层、schemas、core、适配器各做什么。
- 删除与 LexHubPro 无关的 Atoms 脚手架（支付、AI Hub 对外路由、Lambda、空中间件、mock 灌数、过时 Alembic、OIDC 回跳页等）。
- 对外不再提供 `/api/v1/aihub` 与管理端改 `.env` 的 settings。
- 认证基建只保留自建 JWT，去掉 OIDC/PKCE/JWKS。
- 审查调用不再回落到平台 AI Hub。
- 新增 `docs/ddl/database-ddl-er.md`：记录现行全部业务表的 DDL 与 ER 图。
- 新增规范：凡 FEAT/BUG 改动数据库表，必须同步该文档；文档门禁校验文件存在且覆盖 ORM 中的表名。

### 2.2 本次明确不做

- 不把 `schemas` 合并进 `models`，不把 `core` 合并进 `utils`。
- 不改审查算法、模型配置语义、登录注册流程。
- 不引入新的支付或平台 AI。
- 不强制重写 `core/database.py` 与 `schema_bootstrap.py` 的拆分（仅去掉无关调用）。
- 不删除 `.atoms/` 协作记录与 `.mgx/config.yaml`（非后端死代码主路径）。

## 3. 用户故事

- 作为维护者，我希望目录职责一眼能看懂，以免改错层。
- 作为维护者，我希望仓库里没有平台支付/OIDC/AI Hub 演示接口，以免误用或扩大攻击面。
- 作为维护者，我希望所有表的 DDL 和关系图画在一份文档里，改表时必须更新它。

## 4. 功能需求

| 编号 | 需求描述 | 输入 | 期望输出 |
|------|----------|------|----------|
| F-01 | 架构规约含目录地图 | 读 `.agent/architecture.md` | 四层 / schemas / core / 适配器职责可判定 |
| F-02 | 对外无 AI Hub 与 admin settings | 请求原路径 | 404，OpenAPI 无对应 tag |
| F-03 | 无 OIDC 登录/登出回跳依赖 | 前端路由与后端 auth 基建 | 仅邮箱密码 + JWT |
| F-04 | 删除支付、Lambda、mock 灌数、空 middleware、过时 alembic、无引用的 mask/enums | 代码库 | 无这些模块入口 |
| F-05 | 表目录文档 | `docs/ddl/database-ddl-er.md` | 含全部 `tb_*` DDL 与 ER 图 |
| F-06 | 改表必须同步表目录 | 新 FEAT/BUG 动表 | 规约 + verify 门禁要求文档覆盖表名 |

## 5. 异常与边界

| 编号 | 场景 | 期望 |
|------|------|------|
| E-01 | 误请求已删除的 aihub/settings | 404，无 500 |
| E-02 | 审查仍使用用户启用模型 | 行为与 FEAT-008/BUG-006 一致 |
| E-03 | 表目录缺失或漏表名 | `verify.sh --docs-only` 失败 |

## 6. 非功能

| 维度 | 要求 |
|------|------|
| 安全 | 去掉可改 `.env` 的管理接口；日志仍禁止密钥与合同正文 |
| 兼容 | 登录、审查、模型配置、历史报告保持可用 |
| 可维护 | 分层不合并；死代码不留 import 残留 |

## 7. 验收标准

- [ ] AC-01：架构文档有目录地图，说明 schemas≠models、core 不是业务层。
- [ ] AC-02：进程内无法 import 已删的 payment / aihub 路由 / mock_data / lambda_handler。
- [ ] AC-03：`/api/v1/aihub/*` 与 `/api/v1/admin/settings` 返回 404。
- [ ] AC-04：`core.auth` 不再出现 oidc/jwks/pkce。
- [ ] AC-05：审查 gentxt 不实例化平台 AI Hub。
- [ ] AC-06：`docs/ddl/database-ddl-er.md` 列出全部现行 `tb_*` 并含 ER 图。
- [ ] AC-07：`.agent/` 与 `docs/rules/07` 写明改表必须同步该文档；docs-only 校验文件存在且覆盖表名。
- [ ] AC-08：pytest 通过；Playwright 截图 S01 起归档。

## 8. 影响面

| 维度 | 影响 |
|------|------|
| 页面 | 去掉 OIDC 登出回跳页 |
| 接口 | 删除 aihub、admin settings |
| 数据结构 | 无表结构变更；只补文档 |
| 配置 | 去掉 stripe/alembic/mangum 依赖（若不再引用） |
