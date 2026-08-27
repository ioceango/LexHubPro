# Checklist：BUG-005

| 项 | 内容 |
|----|------|
| 迭代号 | BUG-005-smtp-verify-code-not-sent |
| 最后更新 | 2026-08-27 |

## 1. 功能验收

| 编号 | 验证项 | 状态 | 实际结果 / 证据 |
|------|--------|------|-----------------|
| AC-01 | 新邮箱注册走 SMTP | ✅ | GMAIL_SEND_OK；再注册 dispatched |
| AC-02 | 已存在账号再次注册补发验证码 | ✅ | pytest + 日志 reissue=True |
| AC-03 | 禁用账号不发信 | ✅ | pytest blocked is None |
| AC-04 | 失败提示与日志脱敏 | ✅ | 550 时页面「发送失败」 |

## 7. 自动化验证

| 顺序 | 命令 | 状态 | 结果摘要 |
|------|------|------|----------|
| ⓿ | docs-only | ✅ | 退出码 0 |
| ② | pytest | ✅ | 49 passed |
| ⑥ | Playwright | ✅ | 1 passed，S01–S03 |
