# Checklist：BUG-007

| 项 | 内容 |
|----|------|
| 迭代号 | BUG-007-contract-report-user-id-fk |
| 最后更新 | 2026-08-28 |

| 编号 | 验证项 | 状态 | 证据 |
|------|--------|------|------|
| AC-01 | 两表 user_id 为整数且 FK 到 tb_user | ✅ | ORM + 现场 `\d` |
| AC-02 | 合同 1:N 报告仍成立 | ✅ | `test_user_id_fk.py` |
| AC-03 | 存量 varchar 迁成 integer，库内外键存在 | ✅ | bootstrap 日志 + information_schema |
| AC-04 | 归属只来自令牌 | ✅ | Owner 由 auth_user.id 组装 |
| AC-05 | `# BUG-007 回归` 用例 | ✅ | `tests/test_user_id_fk.py`、`test_schema_bootstrap.py` |
| AC-06 | DDL/ER 已同步 | ✅ | `docs/ddl/database-ddl-er.md` |
| AC-07 | Playwright S01 起 | ✅ | S01–S04 |
| AC-08 | 进程内身份类型为 int；JWT 仅序列化边界为 str | ✅ | AuthUser/Owner/schemas；`auth_tokens.sub` |
| AC-09 | `/me` 与前端 AuthProfile.id 为数字 | ✅ | schemas + `auth-provider.ts` |

## 规范符合性

- [x] 表变更已同步 `docs/ddl/database-ddl-er.md`
- [x] 未合并 schemas 与 models
- [x] 仓储 commit 仍由 service 控制
- [x] `.atoms/` 已同步
- [x] 编号截图已归档并在 `test-report.md` 引用
