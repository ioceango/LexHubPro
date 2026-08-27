# Checklist：BUG-006

| 项 | 内容 |
|----|------|
| 迭代号 | BUG-006-review-tx-already-begun |
| 关联文档 | `./spec.md`、`./plan.md` |
| 最后更新 | 2026-08-27 |

## 1. 功能验收

| 编号 | 验证项 | 状态 | 实际结果 / 证据 |
|------|--------|------|-----------------|
| AC-01 | 先读后写状态不抛 begin 冲突 | ✅ | `test_close_read_transaction_allows_status_update`；对照 `test_select_then_begin_raises_without_closing_read_tx` |
| AC-02 | 已启用模型能越过状态更新 | ✅ | 关闭只读事务后 `reviewing` 写成功 |
| AC-03 | 下载/AI 不在未提交事务中 | ✅ | `close_read_transaction` 后 `not session.in_transaction()` |
| AC-04 | 无启用模型仍 409 | ✅ | `get_active` 空仍在 commit 前返回 409，未改语义 |
| AC-05 | 回归用例 `# BUG-006 回归` | ✅ | `tests/test_review_tx.py` 两条 docstring 均注明 BUG-006 回归 |
| AC-06 | Playwright 截图 S01 起 | ✅ | S01–S03 |
| AC-07 | content 空时读取 reasoning_content | ✅ | `test_extract_glm_reasoning_content_when_content_empty` |
| AC-08 | openai DEBUG 不记 prompt | ✅ | `openai`/`httpx` logger 降为 WARNING |

## 2. 规范

- [x] 事务不跨 MinIO / AI（读完即 commit，再短写状态）
- [x] 日志不记录合同正文、Key、prompt
- [x] 分层未破坏

## 3. 自动化

| 步骤 | 状态 | 结果 |
|------|------|------|
| docs-only | ✅ | 退出码 0 |
| pytest | ✅ | 64 passed |
| eslint / vite | ✅ | 退出码 0 |
| Playwright `review-tx.spec.ts` | ✅ | 2 passed |
