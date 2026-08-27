# 实现方案：FEAT-005 可插拔认证与对象存储

> 本文档为规划产物。经用户确认后方可按阶段进入编码。

## 1. 总体技术方案

### 1.1 架构策略：端口-适配器（Ports & Adapters）

在认证与存储两处引入抽象端口，业务代码只依赖端口，具体实现由工厂按配置注入。

```
路由/服务层
    │  只依赖抽象
    ▼
AuthProvider (协议)            StoragePort (协议)
    ├── PlatformAuthProvider       ├── PlatformStorageProvider
    └── LocalAuthProvider          └── MinioStorageProvider
         ▲                              ▲
    工厂按 AUTH_MODE 选择          工厂按 STORAGE_MODE 选择
```

**为什么选这个方案**

| 方案 | 取舍 |
|------|------|
| 端口-适配器 + 配置工厂（采用） | 业务零感知；新增实现只加适配器；契约测试可复用；符合 06 分层与开闭原则 |
| 在业务代码里 `if mode == 'local'` 分支 | 分支散落各处，改一次要改多处，必然漂移，违反禁止堆砌与低耦合 |
| 拆成两套独立部署代码 | 维护成本翻倍，功能会逐渐不一致 |

### 1.2 关键收敛点：`dependencies/auth.py`

现有 `get_current_user` 已是「Bearer 令牌 → `UserResponse`」的单一入口，所有需要登录态的路由都经它。因此只需把它的内部实现改为委托 provider，**函数签名与返回类型保持不变**，即可让全部既有路由同时获得双模式能力，无需逐个改动。这是本设计成本最低、风险最小的切入点。

对应地，`AuthUser` 需与现有 `UserResponse` 字段兼容（`id` / `email` / `name` / `role` / `last_login`），新增 `tenant_id` / `status` 作为扩展字段，避免破坏既有响应契约。

### 1.3 存储抽象的落点选择

不直接改写 `services/storage.py`（它是与平台 OSS HTTP 服务对接的实现细节），而是新建 `storage_providers/platform_provider.py` 将其**包装**为端口实现。这样：

- 平台实现的既有行为不被破坏，回归风险最小。
- MinIO 实现是并列的新增文件，互不干扰。
- 业务侧只认 `StoragePort`，后续加 S3 / OSS 只需再加适配器。

### 1.4 local 模式表结构的落地方式（已实测确定，对应 spec R-1）

实测确认平台数据库允许应用建表与建约束，`core/database.py` 的建表机制为 `Base.metadata.create_all`（模型被导入即注册）。因此采用**独立目录 ORM 模型 + 启动自检幂等建表**：

- 模型定义在新增目录 `app/backend/local_auth/models.py`，**不写入** `app/backend/models/**`；`from core.database import Base` 属于引用而非修改。
- 建表由 `local_auth/bootstrap.py` 在启动自检阶段执行，使用 `checkfirst=True` 保证幂等，可重复启动。
- 模型模块由 `routers/local_auth.py` 导入，而 `main.py` 的 `include_routers_from_package` 会在应用启动时自动导入 `routers` 包全部模块，故模型注册**早于** lifespan 的建表时机，无需改动 `main.py`。
- **两种形态均可运行自建认证**，平台形态无需禁用，可在预览环境端到端验证。
- 禁改清单与 web-sdk 约束**均不放宽**：前端自建模式走 `client.apiCall.invoke`，不使用 fetch/axios 直连。

## 2. 分阶段实施计划

每阶段可独立验证、独立回滚。**未完成上一阶段验证不得进入下一阶段。**

### 阶段一：抽象层落地（不改变任何现有行为）

**内容**
- `auth_providers/base.py`：`AuthProvider` 协议、`AuthUser`、`AuthTokenError` / `AuthUserDisabledError`。
- `auth_providers/platform_provider.py`：包装 `core.auth.decode_access_token`，产出 `AuthUser`。
- `auth_providers/__init__.py`：工厂，读 `AUTH_MODE`，非法值抛错；返回单例。
- `storage_providers/base.py` + `platform_provider.py` + `__init__.py`：同构处理。
- `dependencies/auth.py`：改为委托工厂，签名不变。
- 调用现有存储的位置改为经 `StoragePort` 获取。
- 启动自检骨架：校验模式取值合法性。

**验证**
- 后端 `python -m py_compile` 通过。
- 新增契约测试：`AuthProvider` / `StoragePort` 的协议一致性用例（平台实现用 mock，不触真实 OSS）。
- 既有回归 `pytest tests` 全绿（含原 18 项）。
- 前端 `pnpm run lint` + `pnpm run build` 通过。
- 平台预览环境登录、上传、审查、历史四条链路人工确认行为无变化。

**回滚**：删除两个新目录，`dependencies/auth.py` 与存储调用点还原。

### 阶段二：自建认证实现（local 模式，含前端）

**内容**
- SQL 迁移脚本：`users` / `user_identities` / `refresh_tokens` / `auth_action_tokens` / `login_audits`，含全部约束与索引。
- `services/local_auth.py`：注册、登录、令牌签发与轮换、登出、邮箱验证、忘记/重置/修改密码、资料更新、锁定与解锁、审计写入。
- `auth_providers/local_provider.py`：自建 JWT 校验 + 用户状态与 `password_updated_at` 校验。
- `services/mailer.py`：邮件端口 + `console` 实现（打印脱敏链接）+ SMTP 实现骨架。
- `routers/local_auth.py`、`routers/admin_users.py`：按 spec §7 接口表实现，仅在 local 模式注册。
- 前端 `lib/auth-provider.ts`（双实现）、`lib/data-provider.ts`（双实现）、注册/登录/忘记密码/重置/个人资料页面；`hooks/use-auth.ts` 改为依赖统一封装且三态语义不变。
- 自托管所需的业务 REST CRUD 路由（对应 spec R-2）。

**验证**
- 单元测试（不依赖真实 PG，用事务回滚或临时库）：
  - 正向：注册成功、验证邮箱后可登录、刷新轮换成功、登出后旧刷新令牌失效、改密后旧访问令牌失效、重置密码闭环。
  - 反向：重复邮箱注册返回 409、弱密码 422、错误密码计数递增、达阈值锁定、锁定期内拒绝、禁用账号 403、过期令牌 401、一次性令牌二次使用被拒、刷新令牌重放触发整族吊销、非管理员访问管理接口 403。
  - 安全：账号不存在与密码错误返回体一致（防枚举）；日志断言无明文邮箱/IP/密码/令牌。
- 启动自检反向验证：`AUTH_MODE=local` 且 `JWT_SECRET` 缺失 → 启动失败并给出原因。
- 前端 lint + build 通过。

**回滚**：`AUTH_MODE` 回 `platform`，local 路由不注册；迁移脚本不执行即无表。

### 阶段三：MinIO 存储实现

**内容**
- `storage_providers/minio_provider.py`：S3 兼容客户端，私有桶，预签名下载 URL（按 `MINIO_PUBLIC_ENDPOINT` 签名），幂等 `ensure_bucket` 与 `delete`。
- `object_key` 生成规则收敛到共用工具，两实现共用。
- 依赖增量：S3 客户端库（在 `requirements` 上**增量编辑**，禁止整体覆盖）。

**验证**
- 契约测试：同一组用例分别跑平台实现（mock）与 MinIO 实现（可用本地 MinIO 或 mock 客户端）。
- 预签名 URL 断言：包含签名参数、有效期符合配置、host 取自 `MINIO_PUBLIC_ENDPOINT`。
- 反向：桶不存在时 `ensure_bucket` 自动创建；删除不存在对象不报错（幂等）；凭据错误时启动自检失败。

**回滚**：`STORAGE_MODE` 回 `platform`。

### 阶段四：编排与配置文档

**内容**
- `docker-compose.yml`：新增 `minio`（健康检查 + 持久化卷 + 控制台端口）与 `minio-init`（幂等建私有桶）；`backend` 增加 `depends_on: minio 健康` 与相关环境变量。
- `.env.example`：按 spec §8 全量补充，每项标注含义、默认值、是否必填、两模式取值。
- `docs/rules/03-configuration.md`：新增配置项登记。
- `docs/rules/08-deployment.md`：自托管步骤、MinIO 初始化、自托管仍缺 AI 网关的前置依赖说明（对应 spec R-3）。

**验证**
- `docker compose config` 语法校验通过（若环境不允许执行 Docker，则只做 YAML 解析校验并在报告中如实标注未实际启动）。
- `.env.example` 与代码 `getattr` 默认值逐项对齐核对。

### 阶段五：`.agent/` 规约中立化

**内容**
- `.agent/constraints.md`：移除全部平台专有条款，保留通用工程约束。
- `.agent/architecture.md`：平台绑定表述改为「按配置选择的实现」。
- `.agent/README.md`：声明平台专有约束由 `.atoms/` 维护且平台形态下同时强制生效。
- `.atoms/ATOMS.md`：接收平台专有约束 + 新增平台/自托管差异矩阵。

**验证**
- 全文检索 `.agent/` 确认无平台专有关键词残留（Atoms、web-sdk、OIDC、`.mgx`、entities、AIHub 等）。
- `bash scripts/verify.sh --docs-only` 通过。
- 反向：临时在 `.agent/` 注入一条平台条款，确认检索能命中（人工核验，不依赖门禁自动判定）。

### 阶段六：整体验证与文档收尾

- 按 `.agent/verification.md` 固定顺序全量执行。
- 补齐 `checklist.md` 勾选与 `test-report.md` 真实结果。
- 更新 `.atoms/PROGRESS.md`、`.atoms/ARCHITECTURE.md`、`.agent/architecture.md`。

## 3. 改动文件清单

### 3.1 后端新增

| 文件 | 职责 |
|------|------|
| `auth_providers/base.py` | 认证端口协议、`AuthUser`、异常 |
| `auth_providers/platform_provider.py` | 平台认证适配器 |
| `auth_providers/local_provider.py` | 自建认证适配器 |
| `auth_providers/__init__.py` | 工厂与单例 |
| `storage_providers/base.py` | 存储端口协议、`ObjectRef`、异常 |
| `storage_providers/platform_provider.py` | 平台存储适配器 |
| `storage_providers/minio_provider.py` | MinIO/S3 适配器 |
| `storage_providers/__init__.py` | 工厂与单例 |
| `services/local_auth.py` | 自建认证业务编排 |
| `services/mailer.py` | 邮件端口 + console/SMTP 实现 |
| `routers/local_auth.py` | 自建认证路由 |
| `routers/admin_users.py` | 管理端用户与审计路由 |
| `utils/object_key.py` | `object_key` 生成规则（两实现共用） |
| `utils/startup_check.py` | 启动期配置自检 |
| `local_auth/models.py` | 自建认证 ORM 模型（独立目录，不进 `models/**`） |
| `local_auth/bootstrap.py` | 幂等建表与首个管理员引导 |
| `tests/test_auth_providers.py` | 认证契约与 local 逻辑用例 |
| `tests/test_storage_providers.py` | 存储契约用例 |

> 注意 01 规范的文件数与行数阈值：`services/local_auth.py` 若超 400 行必须按职责拆分（如 `local_auth_password.py` / `local_auth_tokens.py`）。

### 3.2 后端修改

| 文件 | 改动 |
|------|------|
| `dependencies/auth.py` | 内部改为委托 provider，签名不变 |
| `services/contract_review.py` 及其调用方 | 文件读写改用 `StoragePort` |
| `requirements.txt` / `requirements.default` | **增量**添加 argon2、S3 客户端、JWT 库；先读后改，禁止覆盖 |

### 3.3 前端

| 文件 | 改动 |
|------|------|
| `lib/auth-provider.ts` | 新增，双实现统一封装 |
| `lib/data-provider.ts` | 新增，业务数据访问双实现 |
| `lib/api.ts` | 扩展为按模式导出客户端 |
| `hooks/use-auth.ts` | 改为依赖统一封装，三态语义不变 |
| `pages/`（Login / Register / ForgotPassword / ResetPassword / Profile） | local 模式新增页面 |
| `pages/Review.tsx`、`pages/History.tsx`、`pages/ReportDetail.tsx` | 数据访问改经 data-provider |

**注意路由原子性**：新增页面文件必须与 `App.tsx` 的 import + `<Route>` **同批次**提交，禁止先挂路由后补文件。

### 3.4 编排与文档

`docker-compose.yml`、`.env.example`、`docs/rules/03-configuration.md`、`docs/rules/08-deployment.md`、`.agent/constraints.md`、`.agent/architecture.md`、`.agent/README.md`、`.atoms/ATOMS.md`、`.atoms/ARCHITECTURE.md`、`.atoms/PROGRESS.md`

### 3.5 禁改（平台形态）

`app/backend/core/**`、`app/backend/models/**`、`main.py`、`lambda_handler.py`、`app/frontend/src/pages/AuthCallback.tsx`、`app/frontend/index.html`、`.mgx/config.yaml`

## 4. 依赖顺序

```
阶段一（抽象层）
   ├─▶ 阶段二（自建认证）──┐
   └─▶ 阶段三（MinIO）─────┤
                           ├─▶ 阶段四（编排与配置）
                           └─▶ 阶段五（规约中立化，可与二/三并行）
                                     └─▶ 阶段六（整体验证收尾）
```

- 阶段二与阶段三都依赖阶段一，彼此独立可并行。
- 阶段四依赖二、三产出的配置项才能定稿。
- 阶段五只依赖 spec 的差异矩阵，可提前进行。

## 5. 对现有审查链路的影响评估

| 环节 | 影响 | 处置 |
|------|------|------|
| 登录态获取 | `get_current_user` 内部实现变化 | 签名与返回不变，既有路由零改动；以回归测试兜底 |
| PDF 上传 | 改经存储抽象 | 平台实现包装原逻辑，行为等价 |
| 文件下载 | 改为端口的预签名接口 | 平台实现内部仍走原 `getDownloadUrl`，语义一致 |
| `object_key` | 规则收敛到共用工具 | 新上传按新规则；平台既有数据的 key 语义不变，读取路径不受影响 |
| AI 审查与提示词 | 不改动 | 无影响 |
| `contracts` / `review_reports` 表结构 | 本期不改 | `tenant_id` 列列为后续演进项 |
| 前端数据访问 | 引入 data-provider 间接层 | platform 实现直接委托 `client.entities`，行为等价 |

## 6. 风险与缓解（实施视角）

| 风险 | 缓解 |
|------|------|
| 平台形态无法验证 local 全链路（spec R-1） | 用不依赖真实 PG 的单元测试覆盖逻辑；平台形态由启动自检拒绝 local；测试报告如实标注未在平台端到端验证 |
| 改 `dependencies/auth.py` 影响全部受保护路由 | 保持签名不变 + 回归测试全绿 + 平台预览四条链路人工确认 |
| 自托管 REST CRUD 遗漏租户过滤导致越权 | 过滤条件下沉到统一数据访问封装，禁止各路由自行拼条件；补越权反向用例 |
| 密码与令牌泄露进日志 | 复用现有 `utils/log_sanitize.py`；测试中加日志断言 |
| 依赖文件被整体覆盖丢包 | 先 `Editor.read` 再 `edit_file_by_replace` 增量添加 |
| 文件行数超阈值 | 按职责拆分，不靠压行规避 |
| 规约中立化后平台约束被忽视 | `.agent/README.md` 显式声明 + 差异矩阵；后续考虑纳入文档门禁 |
| 自托管审查功能不可用（缺 AI 网关，spec R-3） | 在部署文档明确标注为前置依赖，不宣称自托管已完整可用 |

## 7. 回滚策略

- 阶段一至三：均为「新增文件 + 少量委托改造」，回滚只需还原委托点并移除新增目录。
- 阶段二、三的启用完全由 `AUTH_MODE` / `STORAGE_MODE` 控制，出问题**先切回 platform 止损**，再排查。
- 阶段四：compose 与 `.env.example` 为独立文件，可单独还原。
- 阶段五：文档类改动，可逐文件还原。

## 8. 本轮（规划阶段）交付与验证

**交付**：本目录四份文档 + `docs/features/README.md` 登记 + `.atoms/PROGRESS.md` 更新。

**验证**：`bash scripts/verify.sh --docs-only` 通过。本轮**不执行**任何功能测试，`test-report.md` 只记录文档校验的真实结果。