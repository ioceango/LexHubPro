# 测试验证报告：BUG-006

## 1. 报告信息

| 项 | 内容 |
|----|------|
| 迭代号 | BUG-006-review-tx-already-begun |
| 执行日期 | 2026-08-27 |
| 执行人 | Alex |
| 结论 | ✅ 通过 |

## 2. 自动化

| 步骤 | 命令 | 退出码 | 结果摘要 |
|------|------|--------|----------|
| 文档 gate | `bash scripts/verify.sh --docs-only` | 0 | 6 个 BUG 目录通过 |
| ① py_compile | `python -m py_compile api/contract_review.py services/contracts.py` | 0 | |
| ② pytest | `cd app/backend && python -m pytest tests -q` | 0 | **64 passed**（含 `test_review_tx.py`、`test_openai_compat.py`） |
| ③ eslint | `node_modules/.bin/eslint --quiet ./src` | 0 | 宿主 `pnpm i` 仍受 minimumReleaseAge 限制，用本地二进制 |
| ⑤ vite build | `node_modules/.bin/vite build` | 0 | 1841 modules |
| ⑥ Playwright | `playwright test e2e/review-tx.spec.ts`（`NO_PROXY='*'`，截图目录本迭代 `test-report/`） | 0 | **2 passed**（9.1s） |
| Docker | `docker compose up -d --build backend` | 0 | backend healthy；frontend 5173 与 `/docs` 200 |

未执行：完整 `pnpm run e2e`（含 Mailpit 注册用例）。当前 SMTP 走 163，只跑本迭代 spec。未用真实 DeepSeek/OpenRouter Key 做整段审查（按规范 mock）。

## 3. 编号截图

| 编号 | 文件 | 覆盖 AC | 说明 |
|------|------|---------|------|
| S01 | [test-report/S01-review-page.png](./test-report/S01-review-page.png) | AC-06 | 审查页可打开 |
| S02 | [test-report/S02-model-settings-login-required.png](./test-report/S02-model-settings-login-required.png) | AC-06 | 未登录访问模型配置被拦截 |
| S03 | [test-report/S03-review-ready-with-enabled-model.png](./test-report/S03-review-ready-with-enabled-model.png) | AC-02 / AC-06 | 已启用模型时显示「当前审查模型」与「开始 AI 审查」 |

## 4. 验收

| 编号 | 结论 | 证据 |
|------|------|------|
| AC-01 | ✅ | 未 close 时 `InvalidRequestError: already begun`；close 后状态可改为 reviewing |
| AC-03 | ✅ | close 后 `not session.in_transaction()` |
| AC-05 | ✅ | `tests/test_review_tx.py` |
| AC-07 | ✅ | `test_extract_glm_reasoning_content_when_content_empty` |
| AC-08 | ✅ | `main.py` / `openai_compat.py` 将 openai、httpx 设为 WARNING |
| AC-06 | ✅ | S01–S03 |

## 5. 遗留风险

请用已启用的 OpenRouter `z-ai/glm-5.3-flash`（或其它推理模型）再提交一次文字版 PDF。本次修复会读取 `reasoning_content`。若思考过程写满 token、正文仍空，请换普通对话模型。

## 6. 最终结论

两处根因已修：① 重复 begin 500；② 推理模型空 `content`。Docker 后端已重建。
