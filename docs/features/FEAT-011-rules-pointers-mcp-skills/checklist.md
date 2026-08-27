# Checklist：FEAT-011

| 项 | 内容 |
|----|------|
| 迭代号 | FEAT-011-rules-pointers-mcp-skills |
| 最后更新 | 2026-08-28 |

| 编号 | 验证项 | 状态 | 证据 |
|------|--------|------|------|
| AC-01 | 指针纯路标 | ✅ | 三份指针无红线列表；`verify.sh` 断言 `^## 关键红线摘要` |
| AC-02 | docs/rules 校准 | ✅ | 01 适配器 / 03 模型 / 05 `api/*.py` + mock AIInvoker / 06 去掉过渡期 `routers/` |
| AC-03 | 三层关系写明 | ✅ | `docs/README.md`、`.agent/README.md` |
| AC-04 | Grok 指针仍在 | ✅ | `.grok/rules/00-lexhubpro-rules.md` 说明官方扫描路径 |
| AC-05 | skills 目录约定 | ✅ | `.agent/skills/README.md` + `[skills] paths` |
| AC-06 | `.mcp.json` | ✅ | 已有且 command/args 与 TOML 对齐 |
| AC-07 | docs-only | ✅ | `bash scripts/verify.sh --docs-only` 退出码 0 |
| AC-08 | Playwright | ✅ | `e2e/rules-pointers.spec.ts` 1 passed；S01–S02 |

## 规范符合性

- [x] 未改业务运行时代码与表
- [x] 未删除 `.grok/`、未编写具体业务 skill 正文、未把 MCP 密钥写入仓库
- [x] 未新建 `.cursor/` 配置树
- [x] `.atoms/PROGRESS.md` 与 `.atoms/ATOMS.md` 已同步
- [x] 编号截图已归档并在 `test-report.md` 引用
