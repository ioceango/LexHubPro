# Checklist：FEAT-008

| 项 | 内容 |
|----|------|
| 迭代号 | FEAT-008-user-llm-config |
| 关联文档 | `./spec.md`、`./plan.md` |
| 最后更新 | 2026-08-27 |

## 1. 功能验收

| 编号 | 验证项 | 状态 | 实际结果 / 证据 |
|------|--------|------|-----------------|
| AC-01 | 未登录不能保存 Key | ✅ | LLM API 走 `get_current_auth_user`；S02 |
| AC-02 | 两提供商保存 Key 仅回显掩码 | ✅ | pytest suffix；S05 |
| AC-03 | 有效 Key 可拉取并勾选模型 | ✅ | mock `refresh_catalog` |
| AC-04 | 无效 Key 拉取失败无明文 | ✅ | `test_refresh_catalog_invalid_key` |
| AC-05 | 同一用户只能启用一个模型（跨提供商互斥） | ✅ | pytest 启用第二条关掉第一条 |
| AC-06 | 审查页无模型拦截 | ✅ | S04 横幅 + 禁用提交 |
| AC-07 | 审查 API 无模型 409 | ✅ | `get_active` 空 → 409 |
| AC-08 | 审查使用启用模型 | ✅ | `review_model=active.model_id` |
| AC-09 | 用户隔离 | ✅ | `test_user_isolation_hides_other_keys` |
| AC-10 | Playwright 截图 S01 起 | ✅ | S01–S05 |

## 2. 异常场景验证

| 编号 | 场景 | 期望行为 | 状态 | 实际结果 |
|------|------|----------|------|----------|
| E-01 | Key 为空/占位符 | 400，不保存 | ✅ | `test_placeholder_key_rejected` |
| E-02 | 未登录 | 引导登录 | ✅ | S01–S03 |
| E-03 | Key 无效拉模型 | 「密钥无效」无原始报文 | ✅ | mock 401/400 映射 |
| E-06 | 无启用模型仍审查 | 前端拦截 + 409 | ✅ | S04；API 409 |
| E-07 | 启用第二个 | 前一个自动停用 | ✅ | pytest |
| E-08 | 扫描件 | 422，不走平台 PDF 分析 | ✅ | pytest scan 用例 |
| E-09 | 停用当前启用 | 变为无启用 | ✅ | pytest + 「停用」按钮 |

## 3. 分层与设计规范

- [x] 改动落在 plan 声明的分层；审查/配置服务不按厂商名分支
- [x] 新表 `tb_user_llm_provider` / `tb_user_llm_model`，`comment=` + 无写死两家的 CHECK
- [x] 前端页面通过 `lib/user-llm.ts` + `localRequest`，无页面内 `fetch` 打提供商
- [x] `LlmProviderCard` 221 行、`ModelSettings` 71 行、`Review` 383 行，均未超组件/文件上限
- [x] 未改 `index.html`、`AuthCallback.tsx`；本迭代未新增 `.env` 项（加密派生自已有 `JWT_SECRET_KEY`）

## 4. 日志与追踪

- [x] `/api/v1/llm` 与 `/api/v1/review` 挂 `bind_trace_id`
- [x] 保存/删除 Key 只记 provider 与 user_id，不记明文
- [x] AI 调用仍走 `[AI_OP]` 埋点（长度/模型/耗时）
- [x] 提供商错误映射为中文，不回传原始报文

## 5. 配置管理

- [x] 无新增环境变量。厂商 URL 在适配器常量中（plan 确认）
- [x] 配置页提示：更换系统登录密钥后请重填 API Key

## 6. 数据库与事务

- [x] 拉模型 HTTP 在事务外（`refresh_catalog` 不包 `session.begin()`）
- [x] 审查 AI 调用不在写事务内；报告短事务落库
- [x] 启用互斥在同一事务 `disable_all` + `set_enabled`

## 7. 自动化验证

| 顺序 | 命令 | 状态 | 结果摘要 |
|------|------|------|----------|
| ⓿ | `bash scripts/verify.sh --docs-only` | ✅ | 退出码 0 |
| ① | `python -m py_compile ...` | ✅ | 退出码 0 |
| ② | `python -m pytest tests -q` | ✅ | 57 passed |
| ③ | `eslint --quiet ./src` | ✅ | 退出码 0 |
| ⑤ | `vite build` | ✅ | 退出码 0 |
| ⑥ | Playwright `user-llm-config.spec.ts` | ✅ | 2 passed，S01–S05 |

## 8. 豁免

无 UI 豁免。真实提供商 Key 出网按 plan 禁止在测试中执行，留待用户用自己的 Key 验收。
