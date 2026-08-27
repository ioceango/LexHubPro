# 06 后端分层规范（FastAPI + PostgreSQL）

> 调用方向严格单向：**api → service → repository → model**。任何反向或跨层调用都必须在 `plan.md` 中说明并获确认。
> HTTP 层规范目录是 `app/backend/api/`。禁止再使用 `routers/` 与 `local_*` 文件名。

## 1. API 层（HTTP 边界）

**位置**：`app/backend/api/*.py`

**必须做**：
1. 定义 `APIRouter(prefix="/api/v1/<资源>", tags=[...], dependencies=[Depends(bind_trace_id)])`。
2. 通过 Pydantic `schemas` 校验入参、声明 `response_model`。
3. 通过 `Depends(get_current_user)` 完成鉴权，`Depends(get_db)` 获取会话。
4. 廉价前置校验（格式、大小、枚举）在此完成，**避免把明显非法请求送进昂贵的 AI 调用**。参见 `api/contract_review.py`。
5. 把领域异常映射为 HTTP 状态码：`ContractReviewError → 422`、`ValueError → 400`、未知异常 → `500` + `logger.error(..., exc_info=True)`。

**禁止做**：
- ❌ 写业务规则（评分、条款判断、prompt 组装）
- ❌ 直接使用 SQLAlchemy `session.execute` / ORM 查询（应走 repository）
- ❌ 直接调用提供商 SDK（应走 service / `llm_providers`）
- ❌ 向客户端返回堆栈、SQL、环境变量、第三方原始报错
- ❌ 单文件超过 8 个端点

## 2. Service 层（业务编排）

**位置**：`app/backend/services/*.py`

**必须做**：
1. 表达领域流程与规则，方法名使用业务语言（`extract_contract_text`、`review_contract_text`）。
2. 编排外部能力（AI、对象存储）与仓储调用；对不可信外部返回做归一化与校验（`_normalize_payload`、必需字段检查、一次修复重试）。
3. 抛出领域异常（`ContractReviewError`），**不抛 `HTTPException`**。
4. 通过构造函数接收依赖（`self.ai = AIInvoker()`，或由外部注入），便于测试替换。
5. 保持无状态：不缓存请求级数据到实例属性。

**禁止做**：
- ❌ import `fastapi`（除类型无关的极少数工具）或返回 `Response`
- ❌ 感知 HTTP 状态码、请求头、Cookie
- ❌ 裸写 SQL / 直接操作 `AsyncSession`
- ❌ 单个 service 覆盖 3 个以上聚合（上帝服务）
- ❌ 在 service 内 `commit()` 之后再执行可能失败的长耗时调用（见 §5）

## 3. Repository 层（数据访问）

**位置**：`app/backend/repositories/*.py`（按需创建，一个聚合一个仓储类）

**必须做**：
1. 构造函数接收 `AsyncSession`：`def __init__(self, session: AsyncSession)`。
2. 只提供语义化方法：`get_by_id`、`list_by_user`、`create`、`update_status`、`delete_with_reports`。
3. 所有查询显式限定归属条件（如 `user_id`），并显式指定排序与分页上限。
4. 使用参数化查询；如必须写原生 SQL，使用 `text()` + 绑定参数，标识符需白名单校验。
5. 只 `flush()`，**由调用方（service）决定 `commit()`**，以保证事务边界由业务语义控制。

**禁止做**：
- ❌ 包含业务判断（风险等级计算、是否允许审查）
- ❌ 返回 ORM 对象给 api 层（应返回领域对象或由 service 转 schema）
- ❌ 自行 `commit()` / `rollback()`（除明确的独立幂等写入场景，需在 plan 说明）
- ❌ 无 `limit` 的全表查询

## 4. Model 层（ORM，允许修改）

**位置**：`app/backend/models/*.py`。这是表结构的**唯一长期落点**。

- **必须可改**：新增/调整列、约束、索引、注释都在本层完成，并在 `plan.md` 记录。禁止再以「平台生成」为由把 ORM 藏到旁路目录。
- 表名必须 `tb_<业务英文短名>`（见 07）。表必须有用途 `comment`，每个字段必须有意义 `comment`。
- 时间列用 `DateTime(timezone=True)`；业务代码对 `created_at` / `updated_at` 以数据库默认值或 ORM `onupdate` 为准，禁止在 service 里随便改时间语义。
- 模型中不写业务方法（保持持久化职责单一）。

## 5. 事务边界规则（强制）

### 5.1 铁律：数据库事务不得跨越 AI 调用

AI 调用耗时在数十秒级（本项目审查接口前端超时设为 600s）。若事务跨越 AI 调用，会长时间占用连接、持有行锁、放大死锁与连接池耗尽风险。

```python
# ❌ 严禁
async with session.begin():
    contract = await repo.create(...)
    report = await ai_service.review(...)   # 数十秒，事务持续持有连接与锁
    await repo.save_report(report)

# ✅ 正确：短事务 → AI 调用（无事务）→ 短事务
contract_id = await contract_service.create_pending(...)   # 事务①：提交，status=reviewing
report = await review_service.review_contract_text(...)    # 无事务，纯计算/外部调用
await contract_service.complete(contract_id, report)       # 事务②：提交结果与状态
```

**本项目现状**：审查接口从 MinIO 取文件并在 AI 完成后由 service 短事务写报告。事务不得跨越 AI 调用。

### 5.2 其他事务规则

1. **一个业务操作一个事务**：事务由 service 用 `async with session.begin()` 显式界定，禁止隐式依赖 autocommit。
2. **事务内只做数据库操作**：禁止在事务内发 HTTP 请求、读写对象存储、发送邮件、调用 AI。
3. **事务尽量短**：先在事务外完成所有校验与计算，进入事务只做读写。
4. **失败即回滚**：不捕获异常后继续复用同一会话；不手动 `rollback()` 后继续使用（会话上下文管理器已负责回滚，重复回滚会触发 asyncpg 状态错误）。
5. **副作用外推**：需要在写入成功后触发的副作用（通知、清理文件），放在事务提交之后，并保证可重试/幂等。
6. **跨表一致性**：删除合同与其关联报告必须在同一事务内完成，禁止分两次请求造成孤儿数据。

## 6. 错误处理分层

| 层 | 抛出 | 捕获 | 日志 |
|----|------|------|------|
| repository | 数据库原生异常（`IntegrityError` 等） | 仅转换为领域语义异常 | `DEBUG`/`WARNING` |
| service | 领域异常（`XxxError`） | 捕获底层异常并转领域异常 | `WARNING`（可自愈）|
| api | `HTTPException` | 捕获领域异常 + 兜底 `Exception` | `ERROR` + `exc_info=True`（仅此层记 ERROR）|

同一异常只在 api 层记一次 `ERROR`，避免重复堆栈污染日志（见 02 §2）。

## 7. 新增后端能力检查清单

- [ ] 端点落在 `api/`，prefix 符合 `/api/v1/<资源>` 且挂载 `bind_trace_id`
- [ ] 入参有 Pydantic schema、出参有 `response_model`
- [ ] 鉴权依赖已声明，数据访问已限定归属
- [ ] 表在 `models/`、访问在 `repositories/`、编排在 `services/`，三者均可单测
- [ ] 事务不跨 AI / 网络 / 存储调用
- [ ] 领域异常→HTTP 映射完整，含 400 / 401 / 422 / 500
- [ ] 关键埋点（`[AI_OP]` / `[DB_OP]` / `[BIZ]`）已补，含 `trace_id`
- [ ] 无硬编码（模型名、限额、桶名、超时均为常量或配置）
- [ ] `python -m py_compile` 通过，单元/集成测试已补