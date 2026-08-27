# Checklist：FEAT-012

| 项 | 内容 |
|----|------|
| 迭代号 | FEAT-012-git-commit-branch-rules |
| 最后更新 | 2026-08-28 |

| 编号 | 验证项 | 状态 | 证据 |
|------|--------|------|------|
| AC-01 | 09 规则含提交必须带已存在编号 | ✅ | `docs/rules/09-git-commit-and-branch.md` |
| AC-02 | 分支命名与单编号约束 | ✅ | 09 §1、§3 |
| AC-03 | revert / 禁止 force main | ✅ | 09 §4 |
| AC-04 | `.agent/` 硬约束 | ✅ | workflow §7、rules §10 |
| AC-05 | README + 04 索引/引用 | ✅ | docs/README、04 ⑬ |
| AC-06 | 无 `.git` 的适用说明 | ✅ | 09 §7 |
| AC-07 | docs-only | ✅ | 退出码 0 |
| AC-08 | Playwright S01 起 | ✅ | S01–S02 |

## 规范符合性

- [x] 未改业务运行时代码与表
- [x] 未执行 `git init`
- [x] `.atoms/` 已同步
- [x] 编号截图已归档并在 `test-report.md` 引用
