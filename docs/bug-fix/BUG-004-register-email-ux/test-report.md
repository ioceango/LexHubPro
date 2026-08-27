# 测试验证报告：BUG-004

## 1. 报告信息

| 项 | 内容 |
|----|------|
| 迭代号 | BUG-004-register-email-ux |
| 关联文档 | `./spec.md`、`./plan.md`、`./checklist.md` |
| 执行日期 | 2026-08-27 |
| 被测版本 | 本地 Docker Compose（backend/frontend/mailpit 已重建） |
| 结论 | ✅ 通过 |

## 2. 环境信息

| 项 | 值 |
|----|-----|
| 前端 | React 18 + TypeScript + Vite 5.4.21 |
| 后端 | FastAPI + SQLAlchemy Async + PostgreSQL |
| 运行环境 | Docker Compose + Mailpit（`SMTP_PROVIDER=mailpit`） |
| Node | v24.15.0 |
| Python | 3.11.14 |
| Playwright | 1.62.1 Chromium |

## 3. 自动化执行结果

| 顺序 | 步骤 | 命令 | 退出码 | 结果 |
|------|------|------|--------|------|
| ⓿ | 文档合规 | `bash scripts/verify.sh --docs-only` | 0 | 通过 |
| ① | 后端静态检查 | `cd app/backend && python -m py_compile ...` | 0 | 通过 |
| ② | 后端测试 | `cd app/backend && python -m pytest tests -q` | 0 | 48 passed, 5 warnings in 4.75s |
| ③ | 前端 Lint | `node_modules/.bin/eslint --quiet ./src` | 0 | 通过 |
| ⑤ | 前端构建 | `node_modules/.bin/vite build` | 0 | built in 7.84s |
| ⑥ | Playwright | `node_modules/.bin/playwright test` | 0 | 1 passed (6.1s) |

### 关键输出摘要

```text
48 passed, 5 warnings in 4.75s
✓ 1838 modules transformed
[chromium] › e2e/register-email.spec.ts › BUG-004 register sends code then succeeds after verify
1 passed (6.1s)
curl /api/v1/health → {"status":"healthy","database":"ok","service":"lexhubpro"}
grok mcp doctor playwright → handshake OK，24 tools
```

## 4. 编号截图

截图目录：[`./test-report/`](./test-report/)

| 编号 | 文件 | 覆盖 AC | 说明 |
|------|------|---------|------|
| S01 | [test-report/S01-register-page.png](./test-report/S01-register-page.png) | AC-01 / AC-08 | 注册页，提示使用 163 / Gmail |
| S02 | [test-report/S02-invalid-email.png](./test-report/S02-invalid-email.png) | AC-01 | `not-an-email` 拦截，红色错误文案 + toast |
| S03 | [test-report/S03-unsupported-mailbox.png](./test-report/S03-unsupported-mailbox.png) | AC-08 | `user@qq.com` 拒绝，提示仅 163 / Gmail |
| S04 | [test-report/S04-password-visible.png](./test-report/S04-password-visible.png) | AC-05 | 点击眼睛后密码明文 |
| S05 | [test-report/S05-code-step-after-register.png](./test-report/S05-code-step-after-register.png) | AC-06 | 点击注册后进入「输入验证码」，toast 为验证码已发送，未跳登录 |
| S06 | [test-report/S06-wrong-code.png](./test-report/S06-wrong-code.png) | AC-03 | `000000` 提示验证码无效 |
| S07 | [test-report/S07-register-success-login.png](./test-report/S07-register-success-login.png) | AC-07 | 正确验证码后跳转登录，toast「注册成功，请登录」 |

## 5. 验收标准逐条对照

| 编号 | 验收标准 | 验证方式 | 实际结果 | 结论 |
|------|----------|----------|----------|------|
| AC-01 | 非法邮箱不发请求 | Playwright S02 | 页面错误「请输入有效邮箱」 | ✅ |
| AC-02 | 发送 6 位码，未验证不可登录 | Playwright + Mailpit | S05 显示已发到 `*@163.com` | ✅ |
| AC-03 | 正确码成功、错误码失败 | Playwright S06/S07 | 错误码红字；正确码进登录 | ✅ |
| AC-04 | 成功/失败提示可区分 | Playwright | 发码 toast ≠ 注册成功 toast | ✅ |
| AC-05 | 密码可见切换 | Playwright S04 | 明文后 type=text | ✅ |
| AC-06 | 点注册不弹出注册成功、不跳登录 | Playwright S05 | 标题「输入验证码」 | ✅ |
| AC-07 | 验证码一致后才注册成功并跳登录 | Playwright S07 | 登录页 + 「注册成功，请登录」 | ✅ |
| AC-08 | 仅 163 / Gmail | Playwright S03 | qq.com 被拒 | ✅ |

## 6. 遗留风险

| 编号 | 遗留项 | 影响 | 建议 |
|------|--------|------|------|
| R-01 | 真实 163 / Gmail SMTP 账号密码未写入 `.env` | 当前发信走 Mailpit，不是用户真实收件箱 | 设置 `SMTP_PROVIDER=163` 或 `gmail`，并填写 `SMTP_USER` / `SMTP_PASSWORD`（163 授权码 / Gmail 应用密码）后重建 backend |
| R-02 | 本会话 Playwright MCP 工具未挂载 | 端到端改用 `pnpm`/本地 Playwright CLI，截图已归档 | 新开对话或 `/mcps` 刷新后可用 MCP |

## 7. 结论

通过。注册流程已改为「发码 → 校验通过 → 注册成功并跳转登录」。Playwright 7 张编号截图已写入 `test-report/` 并在本报告引用。163/Gmail 域名与 SMTP 预设已落地；真实运营商发信需补 SMTP 凭据。
