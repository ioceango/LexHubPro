# .agent/architecture.md — 系统架构与模块职责

> 本文件规定「改哪里」。架构变更必须同步更新本文件与 `.atoms/ARCHITECTURE.md`。
> 产品名：**LexHubPro**。

## 1. 系统概览

LexHubPro 是法律合同审查平台，前后端分离。认证为自建 JWT，对象存储为 MinIO，审查走后端 API 并落库。

核心链路：

```
① 用户邮箱密码登录 → JWT（/api/v1/auth）
② 上传 PDF → MinIO 私有桶 contracts → 写 tb_contract（pending）
③ 前端提交 contract_id 调用 /api/v1/review/analyze
④ 后端从 MinIO 取文件 → 仅 PyMuPDF 提取（不足 200 字符则 422，不再走平台 PDF 分析）
   → 用该用户当前启用的一个模型输出结构化审查 JSON（无启用模型则 409；无 DB 事务）
⑤ 短事务写入 tb_review_report，合同状态 completed
⑥ 报告页/历史页走 /api/v1/contracts、/api/v1/reports（仓储按 tenant_id+user_id 过滤）
```

## 2. 技术栈

- 前端：React 18 + TypeScript + Vite + shadcn/ui + Tailwind CSS + react-router-dom + sonner
- 后端：FastAPI + SQLAlchemy Async + PostgreSQL
- 认证：自建邮箱密码 + JWT
- 存储：MinIO（S3 兼容），私有桶 `contracts`
- AI：用户自备提供商 Key（DeepSeek / OpenRouter，注册表可扩展）；审查只用当前启用的一个模型
- 部署：Docker Compose 自托管为一等路径

技术栈变更属「先问再做」，不得自行迁移框架。

## 3. 后端四层铁律

```
api  →  services  →  repositories  →  models
```

| 层 | 规范目录 | 职责 | 硬禁止 |
|----|----------|------|--------|
| **api** | `app/backend/api/` | HTTP 边界：路由、Pydantic 入参、鉴权依赖、领域异常→状态码 | 业务规则、ORM、SQL、直接调对象存储/AI |
| **services** | `app/backend/services/` | 领域流程、事务边界、编排仓储与外部能力 | import fastapi、读 Request、裸 SQL |
| **repositories** | `app/backend/repositories/` | 只做持久化读写，方法语义化 | 业务判断、自行 commit（除非 plan 写明独立幂等写） |
| **models** | `app/backend/models/` | 表结构的唯一落点，**允许修改** | 业务方法、HTTP、外部 IO |

**目录地图（不是重复分层）**

| 目录 | 角色 | 说明 |
|------|------|------|
| `api/` | 四层·HTTP | 路由与状态码 |
| `services/` | 四层·领域 | 编排、事务边界 |
| `repositories/` | 四层·仓储 | 参数化读写 |
| `models/` | 四层·ORM | 表结构唯一落点，`tb_*` |
| `schemas/` | 契约 | Pydantic 入参出参，**不是**表模型；禁止与 `models` 合并 |
| `dependencies/` | HTTP 依赖 | `Depends`：鉴权、trace_id、session |
| `utils/` | 纯工具 | 无状态，禁止依赖业务模块 |
| `core/` | 进程基建 | 配置、引擎、`Base`、JWT 编解码；**不是**业务层，不含 OIDC |
| `auth_providers/` `storage_providers/` `llm_providers/` | 适配器 | 厂商端口 + 注册表，审查/登录不写 `if provider ==` |
| `docs/ddl/database-ddl-er.md` | 表目录 | 全部表的 DDL 与 ER；改表必须同步 |

**目录约束**
- HTTP 层只有 `app/backend/api/`。`main.py` 只扫描 `api`，不再扫描 `routers`。
- 禁止 api 直接 import repository。禁止 service import api。
- 禁止以 `local_` 命名业务文件；路径不用 `/local-`。
- `schemas/`、`dependencies/`、`utils/`、`core/` 不是第五业务层。
- 认证实现：`auth_providers/jwt_provider.py`（唯一）。存储实现：`storage_providers/minio_provider.py`（唯一）。
- 禁止再引入平台 OIDC、AI Hub 对外路由、Stripe、Lambda handler。

**表设计（与 07 同步，架构级强制）**
- 表名：`tb_<业务英文短名>`。
- 每张表必须有**表用途注释**；每个字段必须有**字段用途注释**。
- **三条路径必须同时带注释**：ORM `comment=`；建表 DDL 的 `COMMENT ON TABLE` / `COMMENT ON COLUMN`；存量表库内 `pg_description` 缺失则幂等补齐。
- `create_all` 不会给已存在表补注释，不能当作存量注释已落地。
- **表 DDL/ER 目录**：`docs/ddl/database-ddl-er.md`。新增/删改表或列必须同迭代更新该文件。

## 4. 模块职责

| 模块 | 职责 | 关键文件 |
|------|------|---------|
| 审查服务 | 本机 PyMuPDF 提取（扫描件 422）+ 用户启用模型结构化审查、从 MinIO 取文件、写报告 | `services/contract_review.py` |
| 审查 API | 入参 `contract_id`、无启用模型 409、异常映射 402/422/503/500 | `api/contract_review.py` |
| 合同/报告 | CRUD，令牌过滤 | `models/contract.py`、`models/review_report.py`、`repositories/contract.py`、`services/contracts.py`、`api/contracts.py`、`api/reports.py` |
| 认证 | 注册登录、6 位邮箱验证码、令牌轮换、锁定、审计 | `models/user.py`、`repositories/user.py`、`services/auth_accounts.py`、`services/auth_sessions.py`、`services/mailer.py`、`api/auth.py` |
| 用户 LLM | 用户自备提供商 Key 与互斥启用模型；审查只用当前启用的一个 | `llm_providers/`、`models/user_llm.py`、`services/user_llm.py`、`api/user_llm.py` |
| 存储 | MinIO 上传与预签名 | `storage_providers/minio_provider.py`、`api/storage.py` |
| 认证状态（前端） | loading / authenticated / anonymous | `hooks/use-auth.ts`、`lib/auth-provider.ts` |
| 页面 | 首页 / 上传审查 / 报告 / 历史 / 登录注册 / 模型配置 | `pages/` |

## 4.1 前端分层（对应 MVC，不另开目录）

| MVC | 目录 | 职责 |
|-----|------|------|
| View | `app/frontend/src/pages/`、`components/` | 页面编排与可复用 UI；`components/ui` 仅保留实际引用 |
| Controller | `app/frontend/src/hooks/` | 认证状态、交互编排，页面不直接散落 fetch |
| Model | `app/frontend/src/lib/` | 类型、API 封装、领域规则 |
| Assets | `app/frontend/src/assets/` | 品牌图等静态资源，由 Vite 打包；禁止运行时拉平台 CDN |

## 5. 关键技术决策（不得擅自推翻）

| 决策 | 选择 | 原因 |
|------|------|------|
| 产品名 | LexHubPro | 统一表示，不再用 LegalGuard / 法盾审约 |
| 认证 | 仅自建 JWT | 去掉平台 OIDC |
| 存储 | 仅 MinIO | 去掉平台 OSS |
| 数据面 | `/api/v1/contracts` 与 `/api/v1/reports` | 去掉 entities 双轨 |
| 审查是否落库 | 后端短事务写报告 | 避免前端经 entities 落库；事务不跨 AI |
| 分层 | `api → services → repositories → models` | 单向、可改 ORM |
| 表命名与注释 | `tb_*` + COMMENT ON | 库内可读 |
| 部署 | Docker Compose 自托管 | 一等路径 |
| 审查模型 | 用户自备 Key，同时只能启用一个；无平台模型兜底 | FEAT-008；提供商走 `llm_providers/` 注册表 |

## 6. 扩展指引

- 新增业务表：`models/`（`tb_*` + 表/字段 comment）→ `repositories/` → `services/` → `api/`。DDL 必须带 `COMMENT ON`。
- 新增 LLM 提供商：`llm_providers/<slug>.py` 实现端口并在 `registry` 注册。禁止改审查主流程里的厂商分支。
- 新增审查维度：prompt schema、归一化、api 响应、前端 `lib/review.ts`、报告页同步。
- 认证状态必须区分 loading 与 anonymous。
- 业务请求失败不得跳转登录，只展示错误与重试入口。
