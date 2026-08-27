# 01 开发规范总纲

> 适用范围：`app/frontend`（React + TS + Vite + shadcn/ui）与 `app/backend`（FastAPI + SQLAlchemy Async + PostgreSQL）全部业务代码。

## 1. 分层架构

### 1.1 前端分层

```
app/frontend/src/
├── pages/          # 路由级页面：只做「编排」，不放可复用逻辑
├── components/     # 可复用展示组件（components/ui/** 为 shadcn 原语，禁止改动其 API）
├── hooks/          # 有状态逻辑复用：use-auth.ts、use-mobile.tsx …
├── lib/            # 无状态领域逻辑与外部适配：http.ts、auth-provider.ts、data-access.ts、storage-access.ts、user-llm.ts、review.ts、assets.ts
└── index.css       # 设计系统 tokens（色彩、字体、风险语义色）
```

各层职责与禁止事项：

| 层 | 必须做 | 禁止做 |
|----|--------|--------|
| `pages/` | 组合组件、调用 hooks、处理路由参数与页面级加载/错误态 | 禁止写正则解析、评分算法、文本导出等领域逻辑；禁止页面内散落 `fetch` / `axios` |
| `components/` | 纯展示 + 受控交互，输入靠 props，输出靠回调 | 禁止直接调后端（数据获取属于 pages/hooks + `lib/http.ts` 封装） |
| `hooks/` | 封装状态机（如认证三态 loading/authenticated/anonymous）、数据获取与缓存 | 禁止渲染 JSX；禁止在 hook 里 `toast` 业务级文案以外的副作用堆叠 |
| `lib/` | 类型定义、纯函数、HTTP/认证/存储/用户模型适配（`lib/http.ts` 是唯一请求出口） | 禁止依赖 React；禁止读取组件状态 |

**真实约束举例**：报告页的 `risk_clauses` / `missing_clauses` / `compliance_checks` / `key_terms` / `suggestions` 在数据库中是 JSON 字符串，解析必须统一走 `lib/review.ts` 的 `parseJsonField`，**不允许任何页面内联 `JSON.parse`**。新增报告维度时必须同步四处：后端 prompt schema → 后端 `_normalize_payload` → 后端响应模型 → 前端 `lib/review.ts` 类型 → 报告页展示区块。

### 1.2 后端分层

```
app/backend/
├── api/            # HTTP 边界（规范目录）：入参校验、鉴权依赖、错误码映射

├── services/       # 业务编排：领域规则、AI 调用编排、跨资源协调
├── repositories/   # 数据访问：SQLAlchemy 查询与写入，一个聚合一个仓储
├── models/         # ORM 表模型（可改；表名 tb_*，表与字段必须有用途 comment，且 DDL 写入 COMMENT ON）
├── schemas/        # Pydantic 请求/响应模型
├── dependencies/   # FastAPI 依赖：auth、database、tracing
├── core/           # 基础设施（config/database/auth）
└── utils/          # 通用工具（日志清理等）
```

调用方向**严格单向**：`api → services → repositories → models`。
禁止反向依赖（service 不得 import api/router）、禁止跨层跳跃（api 不得直接 import repository，除纯读取且无业务规则的场景需在 plan.md 中说明理由）。
禁止把长期业务 ORM 放在四层之外的旁路包。

> FEAT-006 已将自建认证与自托管业务表收回四层。禁止再新建旁路包放 ORM。

详细的每层禁止事项与事务边界见 [06 后端分层规范](06-backend-layering.md)。

## 2. 设计模式使用场景（结合本项目）

只在下列场景使用模式，**不为炫技引入抽象**（一个实现只有一个分支时不要抽策略接口）。

| 模式 | 本项目适用场景 | 落地位置 |
|------|----------------|----------|
| 策略（Strategy） | 不同合同类型/不同审查深度使用不同 prompt 与校验规则；未来接入多模型对比 | `services/review_strategies/*.py`，由 `ContractReviewService` 按 `contract_type` 选择 |
| 模板方法（Template Method） | 审查流程固定为「提取文本 → 结构化审查 → 规范化校验」，只允许子步骤变化 | `ContractReviewService.extract_contract_text` / `review_contract_text` / `_normalize_payload` |
| 仓储（Repository） | 隔离 SQLAlchemy 细节，让 service 只面对领域对象 | `repositories/contract_repository.py`（按需新增） |
| 依赖注入（DI） | 鉴权、数据库会话、trace 上下文 | `Depends(get_current_user)`、`Depends(get_db)`、`Depends(bind_trace_id)` |
| 适配器（Adapter） | 把 HTTP、JWT 认证、MinIO、用户 LLM 提供商包装成项目语义 | 前端 `lib/http.ts` / `lib/auth-provider.ts` / `lib/data-access.ts` / `lib/storage-access.ts` / `lib/user-llm.ts`；后端 `llm_providers/` + `services/ai_invoker.py` |
| 外观（Facade） | 前端页面只面对一组语义化领域函数，不感知存储/解析细节 | `lib/review.ts`（报告解析、文本生成、导出、下载链接） |
| 防腐层 / 容错包装 | 外部配置或第三方返回不可信时做归一化与兜底 | `_normalize_payload`、`_resolve_frontend_base_url`、`parseJsonField` |

**反模式清单（禁止）**：单例式全局可变状态、上帝服务（一个 service 覆盖 3 个以上聚合）、贫血 + 逻辑散落在页面、为「以后可能扩展」预留空接口、继承层级超过 2 层。

## 3. 高内聚低耦合原则

1. **一个模块一个变更理由**：合同解析、风险审查、报告存取、页面展示必须能独立修改。
2. **依赖倒置**：service 依赖抽象（仓储接口、AI 客户端接口），不依赖具体驱动细节。
3. **数据契约集中**：跨层结构体必须在 `schemas/`（后端）或 `lib/review.ts`（前端）声明，禁止用裸 `dict` / `any` 在层间传递。
4. **副作用外推**：纯计算函数（评分归一化、文本生成）不得内嵌 IO；IO 由调用方注入。
5. **禁止循环依赖**：任何两个模块互相 import 视为设计缺陷，必须抽公共模块。

## 4. 禁止堆砌代码：量化判定标准

以下为**硬性阈值**，超限即需重构或在 `plan.md` 中给出明确豁免理由：

| 维度 | 阈值 | 处理方式 |
|------|------|----------|
| 函数/方法长度 | ≤ 50 行（不含 docstring 与常量声明） | 拆子函数，按语义命名 |
| React 组件长度 | ≤ 250 行；含 3 个以上独立区块须拆子组件 | 抽 `components/` 子组件 |
| 单文件长度 | ≤ 400 行（`components/ui/**` 与 prompt 常量文件除外） | 按职责拆文件 |
| 函数参数个数 | ≤ 5；再多必须用 Pydantic model / TS interface | 参数对象化 |
| 嵌套层数 | ≤ 3 层（if/for/try） | 早返回、卫语句、提取函数 |
| 圈复杂度 | ≤ 10 | 表驱动或策略模式替换 if-else 链 |
| 重复代码 | 连续 ≥ 8 行且出现 ≥ 2 次 | 必须抽公共函数/hook |
| 单个 `useEffect` | 只做一件事，依赖数组 ≤ 4 项 | 拆多个 effect |
| 魔法值 | 0 容忍 | 提为具名常量或配置项（见 03） |
| 单个 api 文件端点数 | ≤ 8 | 按子域拆 `api/` 模块 |

**「堆砌」的典型识别信号**（出现即视为不合格）：复制粘贴的三段近似 `try/except`、页面里逐个字段手写重复的 `JSON.parse`、同一段风险等级颜色映射在多个文件重写、把校验逻辑分散在 router 与 service 两处、用注释分隔而不是用函数分隔的超长函数。

## 5. 注释规范

1. **注释解释「为什么」，不复述「做什么」**。
   - 反例：`# 遍历列表` ；正例：`# 平台动态属性缺失时会抛 AttributeError，此处回退到请求 host，避免登出接口 500`。
2. 后端每个模块（`.py`）顶部必须有中文模块 docstring，说明职责、上下游、关键约束（参见 `services/contract_review.py`）。
3. 后端每个公开类与公开方法必须有 docstring；私有函数在逻辑非显然时补一行说明。
4. 前端每个非 UI 原语文件顶部写一句用途注释；复杂领域函数写 JSDoc 说明入参含义与失败行为。
5. 所有「反直觉决策」「兜底逻辑」「外部契约不可信处」必须留注释并注明背景，例如：JSON 修复重试、审查 API 600s 超时、私有桶只存 `object_key`。
6. 禁止：注释掉的死代码、`TODO` 无责任人无迭代号、与代码不一致的过期注释（改代码必须同步改注释）。

## 6. 命名规范

| 对象 | 规则 | 示例 |
|------|------|------|
| Python 模块/包 | `snake_case` | `contract_review.py` |
| Python 类 | `PascalCase`，服务以 `Service` 结尾，仓储以 `Repository` 结尾，异常以 `Error` 结尾 | `ContractReviewService`、`ContractReviewError` |
| Python 函数/变量 | `snake_case`；私有前缀 `_` | `_normalize_payload` |
| 常量 | `UPPER_SNAKE_CASE` | `MAX_PDF_DATA_URI_LENGTH`、`REVIEW_API_TIMEOUT_MS` |
| React 组件文件 | `PascalCase.tsx` | `ReportDetail.tsx`、`SiteHeader.tsx` |
| hook 文件 | `use-xxx.ts` | `use-auth.ts` |
| TS 类型/接口 | `PascalCase`，不加 `I` 前缀 | `ReviewReport`、`RiskClause` |
| 布尔变量 | `is/has/can/should` 前缀 | `isReviewing`、`hasReport` |
| 事件回调 | `handleXxx`（内部） / `onXxx`（props） | `handleUpload` / `onDelete` |
| API 路径 | `/api/v1/<资源复数>/<动作>`，全小写短横线 | `/api/v1/review/analyze` |
| 数据库表 | `tb_<业务英文短名>` | `tb_contract`、`tb_review_report`、`tb_user_llm_model` |

命名禁止：拼音、无意义缩写（`tmp2`、`data1`、`mgr`）、与内置/库同名（`list`、`type`、`Zap` 与已 import 图标重名）。