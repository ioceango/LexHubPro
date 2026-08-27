# Plan：BUG-004

## 方案

- 前端：`isValidEmail`；`PasswordInput`（Eye 切换）；注册成功 toast + 验证码步骤。
- 后端：6 位验证码（哈希入库，按邮箱+用户查找）；SMTP 实现（`SMTP_HOST` 存在则启用并强制验证）；`RegisterResponse.verification_required`。
- 防枚举：重复邮箱仍返回同一成功文案，不发信。
- 自托管：compose 增加 Mailpit，默认 `SMTP_HOST=mailpit`，可在 `http://localhost:8025` 查看验证码邮件。生产改真实 SMTP。
- 6 位码摘要绑定 `user_id`，避免撞 `tb_one_time_token.token_hash` 全局唯一约束。

## 文件

- 新增：`app/frontend/src/lib/email.ts`、`components/PasswordInput.tsx`
- 修改：`pages/Register.tsx`、`pages/Login.tsx`、`pages/ResetPassword.tsx`、`pages/Profile.tsx`、`lib/auth-provider.ts`
- 修改：`services/mailer.py`、`auth_accounts.py`、`api/auth.py`、`schemas/auth.py`、`repositories/user.py`、`utils/auth_crypto.py`
- 修改：`.env.example`、`docker-compose.yml`
- 测试：`tests/test_auth.py`、`tests/test_mailer.py`、`tests/test_auth_providers.py`（BUG-004 回归）

## 禁改

无。不改业务无关脚手架。

## 实施顺序

1. 邮箱校验与密码可见组件
2. 注册/登录提示与验证码步骤
3. SMTP 邮件与 6 位码签发/校验/重发
4. compose Mailpit 与配置
5. 回归测试与验证

## 数据与接口

- `POST /api/v1/auth/register` 响应增加 `verification_required`
- `POST /api/v1/auth/verify-email` 支持 `{email, code}`
- `POST /api/v1/auth/verify-email/resend`

## 风险与回滚

- 未配 SMTP 时不发信、不强制验证，行为与修前兼容。
- Mailpit 仅本地收信；生产必须改真实 SMTP，否则用户收不到邮件。
- 回滚：去掉 SMTP 环境变量即可关闭强制验证。

## 变更记录

- 相对初稿：增加 Mailpit 默认发信，验证码哈希绑定 user_id。
- 补充：注册成功仅在验证码校验后弹出并跳转登录；163/Gmail 白名单与 SMTP 预设；Playwright 截图门禁。
