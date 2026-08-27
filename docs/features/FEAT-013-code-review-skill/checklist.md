# Checklist：FEAT-013

| 项 | 内容 |
|----|------|
| 迭代号 | FEAT-013-code-review-skill |
| 最后更新 | 2026-08-28 |

| 编号 | 验证项 | 状态 | 证据 |
|------|--------|------|------|
| AC-01 | SKILL.md 存在且可触发 | ✅ | `.agent/skills/code-review/SKILL.md` |
| AC-02 | 四视角且指向 SSOT | ✅ | §1–4 |
| AC-03 | 输出格式与只读默认 | ✅ | 文首 + §6 |
| AC-04 | README 登记、无 grok 拷贝 | ✅ | skills README；无 `.grok/skills` |
| AC-05 | docs-only | ✅ | 退出码 0 |
| AC-06 | Playwright | ✅ | S01–S02 |
| AC-07 | 审查产物写入 `review-report/Rnn-日期.md` | ✅ | [R01-2026-08-28.md](./review-report/R01-2026-08-28.md) |

- [x] 未改业务代码与表
- [x] `.atoms/` 已同步
