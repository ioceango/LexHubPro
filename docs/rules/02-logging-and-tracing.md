# 02 日志与链路追踪规范

> 目标：任何一次审查失败，都能仅凭一个 `trace_id` 在日志中还原「请求进入 → 鉴权 → PDF 解析 → AI 审查 → 结果校验 → 响应」的完整链路，且不泄露合同内容与用户隐私。

## 1. 基础设施现状

- 后端统一使用 Python 标准库 `logging`，每个模块固定写法：
  ```python
  import logging
  logger = logging.getLogger(__name__)
  ```
  **禁止 `print()`**，禁止自建 logger 层级或重复 `basicConfig`。
- 日志文件轮转与清理由 `utils/logging_utils.py` 负责（`app_YYYYMMDD.log`），受环境变量控制：
  `FUNCSEA_BACKEND_LOG_CLEANUP_ENABLED`、`FUNCSEA_BACKEND_LOG_BACKUP_COUNT`、`FUNCSEA_BACKEND_LOG_MAX_TOTAL_MB`。**业务代码不得自行删除或改写日志文件。**
- 已有埋点前缀约定：数据库层使用 `[DB_OP]`（见 `core/database.py`）。本规范在此基础上补充 `[AI_OP]`、`[BIZ]`、`[TRACE]`。

## 2. 日志分级标准

| 级别 | 使用场景 | 本项目示例 | 是否允许出现在生产 |
|------|----------|------------|--------------------|
| `DEBUG` | 开发排查细节、耗时统计、入参摘要 | `[DB_OP] session created in 0.01s`、PDF 文本长度 | 仅 `DEBUG=true` 时 |
| `INFO` | 关键业务里程碑（成功路径） | 审查完成 `score=/level=`、文件上传成功、登出跳转生成 | 是 |
| `WARNING` | 可自愈的异常/降级/重试 | JSON 解析失败进入一次修复重试、`frontend_url` 为占位符回退请求 host、命中限额 | 是 |
| `ERROR` | 请求失败且用户可感知，需人工关注 | PDF 解析异常、AI 调用异常、数据库写入失败 | 是 |
| `CRITICAL` | 服务级不可用 | 数据库初始化失败、配置缺失导致启动失败 | 是 |

规则：
1. 用户输入不合法（400/422）用 `WARNING`，**不得用 `ERROR`**，避免噪声掩盖真实故障。
2. `ERROR` 必须带 `exc_info=True`，保留堆栈。
3. 同一次失败**只记录一次** `ERROR`（在捕获并转换为 HTTP 响应的那一层），下层用 `WARNING`/`DEBUG`，禁止逐层重复打印同一异常。
4. 日志消息使用英文短句 + 结构化字段，便于检索；面向用户的中文提示只放在 HTTP `detail`。

## 3. `trace_id` 贯穿链路

### 3.1 生成与传递

因平台约束**不得修改 `main.py`**（无法注册全局中间件），本项目采用「路由级依赖 + `contextvars`」方案：

```python
# app/backend/dependencies/tracing.py
import contextvars, logging, uuid
from fastapi import Request

trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="-")
logger = logging.getLogger(__name__)

async def bind_trace_id(request: Request) -> str:
    """为当前请求绑定 trace_id：优先复用上游 X-Trace-Id，否则新生成。"""
    incoming = (request.headers.get("X-Trace-Id") or "").strip()
    trace_id = incoming[:64] or uuid.uuid4().hex[:16]
    trace_id_var.set(trace_id)
    logger.info("[TRACE] enter %s %s trace_id=%s", request.method, request.url.path, trace_id)
    return trace_id
```

新增自定义 router 必须在创建时挂载该依赖：

```python
router = APIRouter(prefix="/api/v1/review", tags=["review"], dependencies=[Depends(bind_trace_id)])
```

Service / Repository 层通过 `trace_id_var.get()` 读取，**不得把 `trace_id` 作为业务参数一路透传**（避免污染领域签名）。

### 3.2 日志格式约定

每条业务日志必须可关联 `trace_id`，统一采用：

```
logger.info("[BIZ] contract reviewed trace_id=%s user_id=%s score=%s level=%s cost_ms=%s",
            trace_id_var.get(), user_id, score, level, cost_ms)
```

### 3.3 前端协同

- 前端在调用 `client.apiCall.invoke` 失败时，将后端 5xx 响应中的 `trace_id` 展示在错误提示的次要行（如「错误编号：a1b2c3d4」），便于用户反馈定位。
- 后端 5xx 响应体的 `detail` 允许附带 `（错误编号：<trace_id>）`，**但不得附带任何堆栈或 SQL**。

## 4. 关键埋点清单（必须实现）

### 4.1 AI 调用埋点（`[AI_OP]`）

每次 AI 调用前后各一条，成对出现：

| 时机 | 级别 | 必含字段 |
|------|------|----------|
| 调用前 | `INFO` | `stage`（`pdf_extract` / `review` / `json_repair`）、`model`、`input_chars`、`trace_id` |
| 成功后 | `INFO` | `stage`、`model`、`output_chars`、`cost_ms`、`trace_id` |
| 解析失败进入修复重试 | `WARNING` | `stage=json_repair`、`reason`、`trace_id` |
| 调用异常 | `ERROR` | `stage`、`model`、`error_type`、`cost_ms`、`trace_id` + `exc_info=True` |

**禁止记录**：合同全文、PDF base64、prompt 完整内容、AI 返回完整 JSON。只允许记录长度、字段名、条目数量等元信息。

### 4.2 数据库埋点（`[DB_OP]`）

| 时机 | 级别 | 必含字段 |
|------|------|----------|
| 事务开始/提交 | `DEBUG` | `op`、`table`、`cost_ms` |
| 写操作成功 | `INFO` | `op`（insert/update/delete）、`table`、`affected`、`trace_id` |
| 唯一键冲突 / 幂等命中 | `WARNING` | `table`、`conflict_key`（仅字段名） |
| 事务回滚 | `ERROR` | `op`、`table`、`error_type` + `exc_info=True` |
| 慢查询（> 500ms） | `WARNING` | `op`、`table`、`cost_ms` |

**禁止记录**：完整 SQL 参数值、合同标题以外的业务明文、任何凭据。

### 4.3 认证与存储埋点

- 登录/登出：`INFO`，记录 `user_id`、动作、跳转目标 host（**不记录完整含 token 的 URL**）。
- 配置降级：`WARNING`，例如 `frontend_url` 缺失或仍为 `$$FRONTEND_DOMAIN$$` 占位符时的回退（这是真实发生过的登出 500 根因，必须留痕）。
- 对象存储：`INFO` 记录 `bucket`、`object_key`、`size`；**禁止记录临时下载 URL**（含签名）。

## 5. 错误上报与脱敏

### 5.1 错误分层映射

| 异常来源 | HTTP 状态 | 日志级别 | 用户提示 |
|----------|-----------|----------|----------|
| 入参不合法（非 PDF、超限） | 400 | `WARNING` | 明确可操作的中文提示 |
| 领域可重试失败（`ContractReviewError`） | 422 | `WARNING` | 原因 + 「请重试」 |
| 未认证 | 401 | `INFO` | 引导登录 |
| 越权访问他人数据 | 403/404 | `WARNING` | 通用提示，不透露资源是否存在 |
| 依赖故障（AI/DB/存储） | 500 | `ERROR` + `exc_info` | 通用提示 + 错误编号 |

**红线**：`HTTPException.detail` 中禁止出现堆栈、SQL、内部文件路径、环境变量名与值、第三方原始报错原文。

### 5.2 脱敏清单（禁止入日志）

1. 合同正文、条款原文、`raw_text_excerpt`、PDF base64；
2. 用户邮箱/手机号/姓名全文（如需定位只记录 `user_id`）；
3. `Authorization` 头、Cookie、OIDC token、`client_secret`、任意 `*_KEY` / `*_SECRET` / `DATABASE_URL`；
4. 对象存储签名 URL、`upload_url`、`download_url`；
5. 完整请求体。必要时只记录字段名与长度：`fields=[pdf(len=1234567), contract_type, party_role]`。

### 5.3 实施要求

- 提供统一脱敏工具（建议 `utils/log_sanitize.py`）：`mask_secret(value)` 保留首尾 2 位、`truncate(text, n=200)`、`omit_keys(payload, SENSITIVE_KEYS)`。凡记录来自外部的结构体，必须先过工具函数。
- 前端 `console` 输出仅允许 `console.error` 且不得打印合同内容；生产构建不保留调试 `console.log`（`pnpm run lint` 需通过）。