# 测试验证报告：BUG-005

## 1. 报告信息

| 项 | 内容 |
|----|------|
| 迭代号 | BUG-005-smtp-verify-code-not-sent |
| 执行日期 | 2026-08-27 |
| 结论 | ✅ 通过 |

## 2. 现场排查

| 检查 | 结果 |
|------|------|
| 容器 SMTP 解析 | `provider=163 host=smtp.163.com port=465 ssl=True` |
| TCP/TLS | `smtp.163.com:465` TLSv1.3 成功 |
| 探测发信到发件人 163 | `SEND_OK` |
| 探测发信到已有 Gmail | `GMAIL_SEND_OK` |
| 用户再点注册 | 日志 `register attempt on existing email`，**未发信** |

结论：163 SMTP 可用。收不到信是因为该 Gmail 已在库中（切 163 之前就注册过），再次注册被当成重复账号，验证码为 `None`。

## 3. 自动化

| 步骤 | 结果 |
|------|------|
| pytest | 49 passed |
| 修复后再次注册已有 Gmail | `reissue=True`；`mail dispatched(smtp) to=w***@gmail.com` |
| Playwright | 1 passed；S01–S03 在 `./test-report/` |

Playwright 用了不存在的 `*@163.com`，163 返回 `550 User not found`（预期：只能发给真实存在的邮箱）。页面文案「验证码发送失败，请点击重新发送。」见 S02。

## 4. 编号截图

| 编号 | 文件 | 覆盖 AC | 说明 |
|------|------|---------|------|
| S01 | [test-report/S01-register-page.png](./test-report/S01-register-page.png) | AC-01 | 注册页 |
| S02 | [test-report/S02-code-step-after-send.png](./test-report/S02-code-step-after-send.png) | AC-04 | 进入验证码页；不存在的 163 地址被拒信 |
| S03 | [test-report/S03-resend-still-code-step.png](./test-report/S03-resend-still-code-step.png) | AC-02 | 重新发送仍留在验证码页 |

## 5. 验收

| 编号 | 结果 |
|------|------|
| AC-01 | ✅ 新真实邮箱走 SMTP（Gmail 探测与再注册均 dispatched） |
| AC-02 | ✅ pytest 再注册签发新码；现场 Gmail `reissue=True` 并 dispatched |
| AC-03 | ✅ pytest 禁用账号 `code is None` |
| AC-04 | ✅ 失败提示「验证码发送失败」；日志只含脱敏邮箱与异常类型 |

## 6. 结论

通过。请到 **Gmail 收件箱和垃圾箱** 查刚才补发的「【LexHubPro】邮箱验证码」。已注册过的邮箱再点注册现在会重新发码。163 不会把验证码投递到不存在的 163 地址（550）。
