# 测试验证报告：FEAT-011

## 1. 报告信息

| 项 | 内容 |
|----|------|
| 迭代号 | FEAT-011-rules-pointers-mcp-skills |
| 执行日期 | 2026-08-28 |
| 结论 | ✅ 通过 |

## 2. 自动化

| 步骤 | 命令 | 退出码 | 摘要 |
|------|------|--------|------|
| 文档 gate | `bash scripts/verify.sh --docs-only` | 0 | `.agent` 7/7；指针 3/3（已断言不含 `## 关键红线摘要`）；11 个 FEAT、6 个 BUG |
| Playwright | `cd app/frontend && E2E_BASE_URL=http://127.0.0.1:5173 E2E_SCREENSHOT_DIR=.../FEAT-011-.../test-report ./node_modules/.bin/playwright test e2e/rules-pointers.spec.ts` | 0 | 1 passed（5.9s）；对已运行的 `lexhubpro-frontend`（5173→80）截图 |

未跑全量 pytest / eslint / vite build（本迭代无业务行为变更；仅新增文档 e2e 规格 `e2e/rules-pointers.spec.ts`）。

## 3. 编号截图

| 编号 | 文件 | 覆盖 AC | 说明 |
|------|------|---------|------|
| S01 | [test-report/S01-home-entry.png](./test-report/S01-home-entry.png) | AC-08 | 首页产品入口仍可打开（LexHubPro 标识、主视觉、能力区） |
| S02 | [test-report/S02-login-entry.png](./test-report/S02-login-entry.png) | AC-08 | 登录页仍可打开（邮箱密码登录表单） |

## 4. 验收

| 编号 | 结论 | 证据 |
|------|------|------|
| AC-01 | ✅ | `AGENTS.md` / `CLAUDE.md` / `.grok/rules/00-lexhubpro-rules.md` 无 `## 关键红线摘要`，仅路标 + 必读清单 + 验证命令；`verify.sh` 已加该项断言 |
| AC-02 | ✅ | `docs/rules/01` 适配器改为 `lib/http.ts` + `llm_providers` / `AIInvoker`；`03` 将 claude-opus-5 标为禁止硬编码的反例，现行方案为用户启用模型 |
| AC-03 | ✅ | `docs/README.md`「规范三层关系」；`.agent/README.md` §2 / §6 / §7 |
| AC-04 | ✅ | `.grok/rules/00-lexhubpro-rules.md` 仍在，并写明 Grok 官方扫描本目录 + `AGENTS.md` 后执行 `.agent/` |
| AC-05 | ✅ | `.agent/skills/README.md` 存在；`.grok/config.toml` `[skills] paths = [".agent/skills"]` |
| AC-06 | ✅ | 根 `.mcp.json` Playwright command/args 与 TOML 一致（`node` + 仓库内 `cli.js` + headless/isolated/ignore-https-errors/vision） |
| AC-07 | ✅ | `bash scripts/verify.sh --docs-only` 退出码 0 |
| AC-08 | ✅ | S01–S02 |

## 5. 结论

指针已收成纯路标；细则与现行 JWT + MinIO + 用户自备模型对齐；Grok 仍通过 `AGENTS.md` 与 `.grok/rules` 遵守 `.agent/`；skills 权威目录与 MCP 通用清单已接线。产品入口页面在文档改动后仍可访问。
