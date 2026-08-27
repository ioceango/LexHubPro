# Checklist：BUG-004

| 项 | 内容 |
|----|------|
| 迭代号 | BUG-004-register-email-ux |
| 关联文档 | `./spec.md`、`./plan.md` |
| 最后更新 | 2026-08-27 |

## 1. 功能验收

| 编号 | 验证项 | 状态 | 实际结果 / 证据 |
|------|--------|------|-----------------|
| AC-01 | 非法邮箱不发注册请求 | ✅ | 前端 `isValidEmail`；后端 `EmailStr` 对 `not-an-email` 返回 422 |
| AC-02 | SMTP 下发送 6 位验证码，未验证不可登录 | ✅ | Mailpit 收到 `【LexHubPro】邮箱验证码：284275`；未验证登录 403 |
| AC-03 | 正确验证码可登录，错误码失败 | ✅ | verify-email 200「邮箱验证成功」；`000000` 返回 400 |
| AC-04 | 注册成功/失败有明确提示 | ✅ | 成功 toast + `RegisterResponse.message`；失败 `toast.error` |
| AC-05 | 登录注册密码可切换明文/密文 | ✅ | Playwright S04 |
| AC-06 | 点注册只发码，不跳登录 | ✅ | Playwright S05 |
| AC-07 | 验证码一致后才注册成功并跳登录 | ✅ | Playwright S07 |
| AC-08 | 仅 163 / Gmail | ✅ | Playwright S03；pytest `test_register_rejects_unsupported_mailbox` |

## 2. 异常场景

| 编号 | 场景 | 期望行为 | 状态 | 实际结果 |
|------|------|----------|------|----------|
| E-01 | 非法邮箱 | 不发成功注册 | ✅ | HTTP 422 |
| E-02 | 未验证登录 | 403 明确提示 | ✅ | 「邮箱尚未验证，请先完成邮箱验证」 |
| E-03 | SMTP 故障 | 注册成功但提示重发 | ✅ | `MailerError` 映射为可重发文案 |
| E-04 | 重复注册 | 同一成功文案，不发信 | ✅ | 200 同一 message |
| E-05 | 错误验证码 | 400 | ✅ | 「验证码无效或已过期」 |

## 3. 分层与设计规范

- [x] 改动落在 api / services / repositories / 前端 pages+components+lib
- [x] api 不写业务规则，service 不 import fastapi
- [x] 邮件在事务外发送
- [x] 未改无关脚手架
- [x] 验证码哈希绑定 user_id
- [x] 配置写入 `.env.example`

## 4. 自动化验证

| 顺序 | 命令 | 状态 | 结果摘要 |
|------|------|------|----------|
| ⓿ | `bash scripts/verify.sh --docs-only` | ✅ | 退出码 0 |
| ① | `cd app/backend && python -m py_compile ...` | ✅ | 退出码 0 |
| ② | `cd app/backend && python -m pytest tests -q` | ✅ | 48 passed |
| ③ | `cd app/frontend && node_modules/.bin/eslint --quiet ./src` | ✅ | 退出码 0 |
| ④ | 前端单测 | ⚠️ | 无 `pnpm test` 脚本，跳过 |
| ⑤ | `cd app/frontend && node_modules/.bin/vite build` | ✅ | 退出码 0 |
| ⑥ | `node_modules/.bin/playwright test` | ✅ | 1 passed，S01–S07 |

## 5. 文档同步

- [x] spec/plan 已按用户「请修复优化」确认
- [x] `.atoms/PROGRESS.md`、`.atoms/ATOMS.md`、`.atoms/ARCHITECTURE.md` 已更新
- [x] 索引表状态改为已修复

## 9. 豁免项记录

| 编号 | 豁免内容 | 理由 | 确认人 |
|------|----------|------|--------|
| X-01 | 真实 163 / Gmail SMTP 凭据未配置 | 代码已支持预设；本机无授权码，e2e 用 Mailpit | 本迭代 |
