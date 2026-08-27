# Plan：FEAT-009 后端分层清理与表目录

## 基本信息

| 项 | 内容 |
|----|------|
| 迭代号 | FEAT-009-backend-layer-cleanup-ddl |
| 对应 Spec | `./spec.md` |
| 确认状态 | ✅ 已确认（用户指定范围，2026-08-28） |

## 1. 方案概述

不改四层调用方向。补架构目录地图；删除 Atoms 残留；AI 文本类型从 `schemas/aihub.py` 收到 `schemas/chat.py`；`AIInvoker` 只接受已注入的 chat 客户端。新增 `docs/ddl/database-ddl-er.md` 作为表 DDL/ER 事实文档，verify 校验 ORM 表名均出现在该文件。建表运行时仍走 `create_all` + `COMMENT ON`，删除过时 Alembic 目录以免双事实源。

## 2. 文件清单

### 新增

- `docs/ddl/database-ddl-er.md`
- `app/backend/schemas/chat.py`
- `app/backend/tests/test_scaffold_removed.py`
- `app/frontend/e2e/layer-cleanup.spec.ts`

### 删除

- `app/backend/api/aihub.py`、`api/settings.py`
- `app/backend/services/aihub.py`、`payment.py`、`mock_data.py`
- `app/backend/schemas/aihub.py`
- `app/backend/lambda_handler.py`
- `app/backend/core/enums.py`、`core/mask_crypto.py`
- `app/backend/models/base.py`
- `app/backend/middlewares/`
- `app/backend/alembic/`、`alembic.ini`
- 前端 `LogoutCallback.tsx`、`LogoutCallbackPage.tsx` 及路由

### 修改

- `.agent/architecture.md` 目录地图；`.agent/rules.md`、`.agent/workflow.md`、`.agent/verification.md`、`.agent/constraints.md`
- `docs/rules/07-database-acid.md`、`docs/rules/04-iteration-workflow.md`、`docs/rules/06-backend-layering.md`（去掉过时 routers/AIHub 表述）
- `scripts/verify.sh` 增加表目录门禁
- `core/auth.py` 仅 JWT
- `services/ai_invoker.py` 去掉 Hub/PDF
- `main.py` 去掉 mock_data；title 改为 LexHubPro
- `requirements.txt` 去掉 stripe/alembic/mangum/sse-starlette（若无引用）
- 所有 `schemas.aihub` 的 gentxt 类型改为 `schemas.chat`

## 3. 数据

无 DDL 变更。文档补齐现行八张表：`tb_user`、`tb_refresh_token`、`tb_one_time_token`、`tb_auth_audit`、`tb_contract`、`tb_review_report`、`tb_user_llm_provider`、`tb_user_llm_model`。

## 4. 风险

误删仍被引用的模块会导致 import 失败。用 pytest 与「尝试 import 已删模块应失败」回归兜住。
