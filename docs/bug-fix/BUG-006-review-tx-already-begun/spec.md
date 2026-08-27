# BUG-006 已配置自定义模型后合同审查仍 500

## 1. 基本信息

| 项 | 内容 |
|----|------|
| 编号 | BUG-006 |
| 类型 | Bug |
| 严重级别 | 阻塞（审查主路径失败） |
| 提出人 | 用户 |
| 日期 | 2026-08-27 |
| 状态 | 已修复 |
| 确认 | ✅ 已确认（用户要求确认实施，2026-08-27） |

## 2. 复现步骤

1. 登录后在 `/settings/models` 保存 DeepSeek 或 OpenRouter Key，拉取模型并启用其中一个。
2. 打开 `/review`，确认出现「当前审查模型」。
3. 上传文字版 PDF，点击开始审查。

## 3. 实际表现

- 页面审查失败（通用错误）。
- Docker 后端日志（`trace_id=285f9cca532d43db`，合同 id=3）：
  - `POST /api/v1/review/analyze` 已通过鉴权，写了 `analyze request`。
  - 随即 `Database session error: A transaction is already begun on this Session.`
  - 栈：`api/contract_review.py` `analyze_contract` → `services/contracts.py` `update_contract_status` 的 `async with session.begin()`。
  - 请求未进入 MinIO 下载之后的提取/模型调用。
- 前端随后 `PATCH /api/v1/contracts/3/status` 把合同标为失败（该接口本身成功）。
- 事务修复后再次审查（合同 id=4，`trace_id=1f5774da0bd34047`）：OpenRouter `z-ai/glm-5.3-flash` HTTP 200，耗时 171s，`output_chars=0`，页面「AI 审查返回为空」。

## 4. 期望表现

- 已启用模型时，审查应进入提取与模型调用，不再因 Session 事务冲突 500。
- 数据库短事务不得跨越对象存储下载或 AI 调用。
- 失败时仍按既有 402/422/409/503 语义提示，而不是 SQLAlchemy 内部错误。

## 5. 根因

SQLAlchemy 2 在第一次查询时会 **autobegin**。`analyze_contract` 的顺序是：

1. `get_contract`：SELECT，会话进入事务。
2. FEAT-008 新增 `get_active`：再 SELECT，仍在同一事务中。
3. `update_contract_status` 再执行 `session.begin()` → `InvalidRequestError`。

因此用户一旦配好模型跨过 409，审查在调用自定义模型之前就 500。事务也尚未按规范在外部 IO 前结束。

**第二根因（事务修复后暴露）**：`OpenAICompatChat` 只读 `message.content`。GLM-5 / Kimi 等推理模型把正文放在 `reasoning_content`（或 `reasoning`），`content` 为 null。调用成功但 `output_chars=0`，被当成空审查。openai SDK 在 DEBUG 下还会把 prompt 打进日志。

## 6. 影响范围

- 所有已配置并启用模型后发起的 `/api/v1/review/analyze`。
- 不影响模型配置 CRUD、未登录拦截、无模型 409。
- 不影响 `PATCH /contracts/{id}/status`（该接口一开始就 `begin()`，前面没有 SELECT）。

## 7. 验收标准

- [ ] AC-01：同一 Session 上先读合同与启用模型，再更新状态为 `reviewing`，不得抛出 `InvalidRequestError`。
- [ ] AC-02：已启用模型时 `analyze` 能越过状态更新，进入文件下载/提取（下载或模型错误不得再伪装成事务冲突）。
- [ ] AC-03：对象存储与 AI 调用期间会话不处于未提交事务。
- [ ] AC-04：无启用模型仍返回 409。
- [ ] AC-05：回归用例注释 `# BUG-006 回归`，且不打真实模型网关。
- [ ] AC-06：Playwright 端到端截图从 S01 起归档。
- [ ] AC-07：`content` 为空但 `reasoning_content` 有正文时，审查能取到该正文（不打真实网关）。
- [ ] AC-08：日志不得因 openai SDK DEBUG 记录 prompt / 合同正文。

## 8. 不做事项

- 不改提供商适配器、加密与「只能启用一个模型」规则。
- 不恢复平台 `APP_AI_*` 兜底。
- 本迭代不以真实 DeepSeek/OpenRouter 额度作为门禁（mock / 不触网）。
