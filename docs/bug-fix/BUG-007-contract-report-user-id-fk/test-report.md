# 测试验证报告：BUG-007

## 1. 报告信息

| 项 | 内容 |
|----|------|
| 迭代号 | BUG-007-contract-report-user-id-fk |
| 执行日期 | 2026-08-28 |
| 结论 | ✅ 通过 |

## 2. 自动化

| 步骤 | 命令 | 退出码 | 摘要 |
|------|------|--------|------|
| 文档 gate | `bash scripts/verify.sh --docs-only` | 0 | 11 个 FEAT、7 个 BUG；DDL 覆盖 ORM 表名 |
| py_compile | `python -m py_compile api/*.py services/*.py repositories/*.py models/*.py auth_providers/*.py` | 0 | |
| pytest | `python -m pytest tests -q` | 0 | 78 passed, 5 warnings |
| eslint | `eslint --quiet src/lib/auth-provider.ts src/pages/AdminUsers.tsx e2e/user-id-fk.spec.ts` | 0 | 仅改动文件 |
| Playwright | `playwright test e2e/user-id-fk.spec.ts` | 0 | 1 passed（6.2s） |
| 现场库 | backend 重建后 `schema_bootstrap` | 0 | `tb_contract.user_id:varchar->integer` + 两表 user_id_fkey |

未跑全量 `pnpm run lint` / `pnpm run build`（页面无布局变更，仅 `AuthProfile.id` 类型）。

## 3. 编号截图

| 编号 | 文件 | 覆盖 AC | 说明 |
|------|------|---------|------|
| S01 | [test-report/S01-home-entry.png](./test-report/S01-home-entry.png) | AC-07 | 首页仍可打开 |
| S02 | [test-report/S02-login-entry.png](./test-report/S02-login-entry.png) | AC-07 | 登录页仍可打开 |
| S03 | [test-report/S03-review-entry.png](./test-report/S03-review-entry.png) | AC-07 | 审查入口仍可打开 |
| S04 | [test-report/S04-history-entry.png](./test-report/S04-history-entry.png) | AC-07 | 历史页「我的合同与报告」仍可打开 |

## 4. 验收

| 编号 | 结论 | 证据 |
|------|------|------|
| AC-01 | ✅ | ORM Integer + FK；现场 `data_type=integer`；`tb_contract_user_id_fkey` / `tb_review_report_user_id_fkey` |
| AC-02 | ✅ | `test_one_user_many_contracts_and_reports`；报告仍 FK 到合同 |
| AC-03 | ✅ | 启动日志 `varchar->integer`；存量 `"1"` 转为 integer |
| AC-04 | ✅ | 仓储仍忽略请求体身份，Owner 由令牌组装 |
| AC-05 | ✅ | `tests/test_user_id_fk.py` 注释 `# BUG-007 回归` |
| AC-06 | ✅ | `docs/ddl/database-ddl-er.md` ER/DDL 已改 |
| AC-07 | ✅ | S01–S04 |
| AC-08 | ✅ | `AuthUser.id: int`、`Owner.user_id: int`；`auth_tokens.py` 仍 `sub: str(user.id)`；对象键出口保留 `str(auth_user.id)` |
| AC-09 | ✅ | `UserResponse` / `UserProfile` / 前端 `AuthProfile.id` 为 number/int |

## 5. 结论

合同与审查报告的 `user_id` 已与 `tb_user.id` 统一为整数外键。进程内身份类型对齐模型层；JWT `sub` 只在序列化边界为字符串。
