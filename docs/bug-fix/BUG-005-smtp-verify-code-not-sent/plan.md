# Plan：BUG-005

## 方案

`EmailAlreadyExistsError` 后查询该邮箱：非 `disabled` 则重新签发 6 位码并交给事务外的 `deliver_verification_email`。对外仍用同一句防枚举文案。邮件补 Date/Message-ID，失败原因记异常类型（不记授权码）。

## 文件

- 修改：`services/auth_accounts.py`、`services/mailer.py`
- 测试：`tests/test_auth.py`（BUG-005 回归）
- 文档：本目录四份 + 索引

## 禁改

不改 `core/**`。不把 SMTP 授权码写入报告。

## 风险

重复点击注册会向该邮箱再发一封验证码；163 侧可能限流。禁用账号仍不发信。
