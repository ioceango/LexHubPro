# 测试验证报告：FEAT-009

## 1. 报告信息

| 项 | 内容 |
|----|------|
| 迭代号 | FEAT-009-backend-layer-cleanup-ddl |
| 执行日期 | 2026-08-28 |
| 结论 | ✅ 通过 |

## 2. 自动化

| 步骤 | 命令 | 退出码 | 摘要 |
|------|------|--------|------|
| 文档 gate | `bash scripts/verify.sh --docs-only` | 0 | 含表 DDL/ER 目录检查；9 个 FEAT |
| pytest | `cd app/backend && python -m pytest tests -q` | 0 | **75 passed** |
| eslint | `node_modules/.bin/eslint --quiet ./src` | 0 | |
| vite build | `node_modules/.bin/vite build` | 0 | |
| Playwright | `playwright test e2e/layer-cleanup.spec.ts` | 0 | 1 passed |
| Docker | `docker compose up -d --build backend frontend` | 0 | healthy |

## 3. 编号截图

| 编号 | 文件 | 覆盖 AC | 说明 |
|------|------|---------|------|
| S01 | [test-report/S01-home.png](./test-report/S01-home.png) | AC-08 | 首页仍为 LexHubPro |
| S02 | [test-report/S02-login-jwt-only.png](./test-report/S02-login-jwt-only.png) | AC-04 / AC-08 | 仅邮箱密码登录 |
| S03 | [test-report/S03-oidc-callback-removed.png](./test-report/S03-oidc-callback-removed.png) | AC-04 | `/logout-callback` 已无 OIDC 退出页 |

Playwright 同时断言 `POST /api/v1/aihub/gentxt` 与 `GET /api/v1/admin/settings` 为 404。

## 4. 验收

| 编号 | 结论 | 证据 |
|------|------|------|
| AC-01 | ✅ | architecture 目录地图 |
| AC-02 | ✅ | pytest 对 payment/aihub/mock_data/lambda_handler 等 `ModuleNotFoundError` |
| AC-03 | ✅ | e2e 404 |
| AC-06 | ✅ | 八张 `tb_*` 均在 `docs/ddl/database-ddl-er.md` |
| AC-07 | ✅ | docs-only 打印「表 DDL/ER 目录：已检查」 |

## 5. 遗留

`.mgx/config.yaml` 与 `.atoms/` 协作记录未删。前端 blog 预渲染仍在构建产物中，未纳入本迭代删除范围。

## 6. 结论

脚手架已从运行路径移除；四层保持清晰；表目录与门禁已生效。
