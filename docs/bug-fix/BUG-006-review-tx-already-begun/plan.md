# Plan：BUG-006 审查会话重复 begin

## 基本信息

| 项 | 内容 |
|----|------|
| 迭代号 | BUG-006-review-tx-already-begun |
| 对应 Spec | `./spec.md` |
| 预估工作量 | 0.5 人时 |
| 确认状态 | ✅ 已确认（用户要求确认实施，2026-08-27） |

## 1. 方案概述

在 `analyze_contract` 读完合同与当前启用模型后，把后续要用的标量字段拷贝出来，再提交/结束自动开启的只读事务，然后才用现有 `session.begin()` 短事务改状态。下载 PDF 与模型调用在事务外。禁止在已有事务上再 `begin()`，也禁止把事务带到 MinIO/AI。

### 备选方案对比

| 方案 | 优点 | 缺点 | 是否采用 |
|------|------|------|----------|
| A：读完后结束隐式事务，再短写；访问对象前拷贝字段 | 符合「事务不跨 IO」；根因清除 | 审查 API 多几行 | ✅ |
| B：`update_contract_status` 改为 `begin_nested` | 少改 API | 仍把事务带到下载/AI | ❌ |
| C：读写全部包在一个 begin 里 | 实现少 | 事务跨越存储与 AI，违规 | ❌ |

## 2. 架构与分层落点

| 层 | 文件 | 改动 | 职责 |
|----|------|------|------|
| services | `app/backend/services/contracts.py` | 修改 | 增加结束隐式只读事务的方法 |
| api | `app/backend/api/contract_review.py` | 修改 | 读完即结束事务；下载/AI 只用标量；短事务写状态与报告 |
| tests | `app/backend/tests/test_contract_review.py` | 修改 | `# BUG-006 回归`：先读再改状态不抛 begin 冲突 |
| e2e | `app/frontend/e2e/review-tx.spec.ts` | 新增 | 审查页与配置入口截图 |

### 禁改自查

- 不改 `lambda_handler.py`、`AuthCallback.tsx`、`index.html`、`.mgx/config.yaml`
- 不改 `llm_providers` 适配器 URL

## 3. 接口契约

`POST /api/v1/review/analyze` 对外字段不变。

| 状态码 | 触发 | 说明 |
|--------|------|------|
| 409 | 无启用模型 | 保持「请先配置并启用一个审查模型」 |
| 500 因 Session begin | 不应再出现 | 本 Bug 消除 |

## 4. 数据库变更

无。

## 5. 实施顺序

1. `close_read_transaction(session)`：若 `session.in_transaction()` 则 `commit()`。
2. `analyze_contract`：`get_contract` + `get_active` → 拷贝 id/title/bucket/key/type → 结束只读事务 → `update_contract_status('reviewing')` → 下载 → 提取/审查 → 短事务写报告与 `completed`。
3. 回归测试：内存库走与生产相同的「先 SELECT 再 begin 写状态」顺序。
4. Playwright 截图归档。
5. **续作**：`extract_completion_text` 兼容 `content` / 分段列表 / `reasoning_content` / `reasoning`；审查 `max_tokens` 提到 16384；把 `openai`/`httpx` 日志降到 WARNING。

## 6. 风险与回滚

| 风险 | 缓解 |
|------|------|
| `expire_on_commit` 后访问 ORM 触发懒加载再次 autobegin | 下载与写报告只用拷贝的标量 |
| 结束后还有别的模型错误 | 日志继续按 402/422/503 分类；本 Bug 只保证能进到调用链 |

回滚：还原 `analyze_contract` 与 `contracts.py` 两处。
