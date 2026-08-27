# Checklist：FEAT-009

| 项 | 内容 |
|----|------|
| 迭代号 | FEAT-009-backend-layer-cleanup-ddl |
| 最后更新 | 2026-08-28 |

## 1. 功能验收

| 编号 | 验证项 | 状态 | 证据 |
|------|--------|------|------|
| AC-01 | 架构目录地图 | ✅ | `.agent/architecture.md` 目录地图 |
| AC-02 | 死代码模块不可 import | ✅ | `test_scaffold_removed.py` |
| AC-03 | aihub/settings 404 | ✅ | Playwright request 404 |
| AC-04 | core.auth 无 oidc | ✅ | `test_core_auth_has_no_oidc` |
| AC-05 | 审查不走 AI Hub | ✅ | `AIInvoker` 无 Hub；无 chat 抛 `AIConfigurationError` |
| AC-06 | DDL/ER 文档覆盖全部 tb_* | ✅ | `docs/ddl/database-ddl-er.md` |
| AC-07 | 改表同步规约 + docs-only 门禁 | ✅ | `.agent/rules.md`、`07-database-acid.md`、verify `check_ddl_catalog` |
| AC-08 | pytest + Playwright | ✅ | 75 passed；e2e 1 passed S01–S03 |

## 2. 规范

- [x] 未合并 schemas 与 models
- [x] 四层调用方向未改
- [x] 表无结构变更，仅建目录文档
