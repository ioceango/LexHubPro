# 测试验证报告：FEAT-008

## 1. 报告信息

| 项 | 内容 |
|----|------|
| 迭代号 | FEAT-008-user-llm-config |
| 执行日期 | 2026-08-27 |
| 执行人 | Alex |
| 对应 spec | `./spec.md` |
| 对应 checklist | `./checklist.md` |
| 结论 | ✅ 通过（自动化与 UI 门禁）。真实 DeepSeek/OpenRouter Key 拉取与审查未在本环境执行 |

## 2. 自动化

| 步骤 | 命令 | 退出码 | 结果摘要 |
|------|------|--------|----------|
| 文档 gate | `bash scripts/verify.sh --docs-only` | 0 | 8 个 FEAT / 5 个 BUG 目录通过 |
| ① py_compile | `cd app/backend && python -m py_compile api/user_llm.py services/user_llm.py ...` | 0 | 无语法错误 |
| ② pytest | `cd app/backend && python -m pytest tests -q` | 0 | **57 passed** |
| ③ eslint | `app/frontend/node_modules/.bin/eslint --quiet ./src` | 0 | 无问题。宿主 `pnpm run lint` 因 pnpm minimumReleaseAge 拦截 hono@4.13.5，改用本地二进制 |
| ⑤ vite build | `node_modules/.bin/vite build` | 0 | 1841 modules，约 6.8s |
| ⑥ Playwright | `playwright test e2e/user-llm-config.spec.ts`（`HTTP_PROXY=` `NO_PROXY='*'`，截图目录本迭代 `test-report/`） | 0 | **2 passed**（11.7s） |

未执行：`pnpm i`（宿主 lockfile 策略失败，与本迭代无关）；完整 `pnpm run e2e`（含 BUG-004/005 Mailpit 用例）。当前 SMTP 走 163，Mailpit 收不到验证码，故只跑本迭代 spec。

## 3. 编号截图

| 编号 | 文件 | 覆盖 AC | 说明 |
|------|------|---------|------|
| S01 | [test-report/S01-review-requires-login-or-model.png](./test-report/S01-review-requires-login-or-model.png) | AC-06 / E-02 | 未登录审查页：需登录后才能上传 |
| S02 | [test-report/S02-model-settings-login-required.png](./test-report/S02-model-settings-login-required.png) | AC-01 / E-02 | 未登录访问 `/settings/models` 被拦截 |
| S03 | [test-report/S03-login-before-model-config.png](./test-report/S03-login-before-model-config.png) | AC-01 | 引导登录页 |
| S04 | [test-report/S04-review-configure-model-banner.png](./test-report/S04-review-configure-model-banner.png) | AC-06 / F-08 | 已登录但无启用模型：横幅「请先配置审查模型」+「去配置模型」；主按钮禁用 |
| S05 | [test-report/S05-model-settings-two-providers.png](./test-report/S05-model-settings-two-providers.png) | AC-02 / F-01 | 配置页按后端列表渲染 DeepSeek 与 OpenRouter；含系统密钥轮换后请重填提示 |

S04/S05 通过拦截 `/api/v1/auth/me` 与 `/api/v1/llm/*` 模拟已登录、未配置状态，不消耗真实提供商额度。

## 4. 验收

| 编号 | 结论 | 证据 |
|------|------|------|
| AC-01 | ✅ | 未登录 `/api/v1/llm/providers` 依赖鉴权；S02 |
| AC-02 | ✅ | pytest `test_save_key_returns_suffix_not_plaintext`；S05 两张卡片 |
| AC-03 | ✅ | pytest `test_refresh_catalog_uses_adapter_and_invalid_key`（mock 成功路径） |
| AC-04 | ✅ | pytest `test_refresh_catalog_invalid_key`，文案含「密钥无效」，不含明文 Key |
| AC-05 | ✅ | pytest `test_enable_second_model_disables_first` |
| AC-06 | ✅ | S04 横幅 + 主按钮「请先配置审查模型」 |
| AC-07 | ✅ | `api/contract_review.py` 无启用模型 → 409「请先配置并启用一个审查模型」 |
| AC-08 | ✅ | `ContractReviewService(review_model=active.model_id)` + 注入用户 chat 客户端 |
| AC-09 | ✅ | pytest `test_user_isolation_hides_other_keys` |
| AC-10 | ✅ | S01–S05 |
| F-06 停用 | ✅ | pytest `test_disable_enabled_model_clears_active`；配置页「停用」按钮 |
| E-08 扫描件 | ✅ | pytest `test_extraction_rejects_scanned_pdf_without_platform_ocr` |

## 5. 遗留风险

- 未用真实 DeepSeek / OpenRouter Key 打外部 API。请在 `/settings/models` 保存自己的 Key → 拉取模型 → 加入 → 启用一个 → `/review` 做一次真实审查。
- 轮换 `JWT_SECRET_KEY` 后旧 Key 无法解密，配置页已提示重填；未做轮换演练。
- 审查 chat 超时已改为 600s，与前端 `timeout: 600_000` 对齐；长审查仍受提供商侧限流影响。

## 6. 最终结论

FEAT-008 代码、自动化与 Playwright 门禁通过。主路径可用：登录后到「模型配置」保存 Key 并启用一个模型，再进行合同审查。未启用则前端拦截、接口 409，无平台模型兜底。
