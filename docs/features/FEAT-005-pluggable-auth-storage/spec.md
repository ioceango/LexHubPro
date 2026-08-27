# 需求规格说明：FEAT-005 可插拔认证与对象存储

> 2026-08-27 用户确认：继续本迭代，并明确要求修改规约，允许 `AUTH_MODE=local` 自建登录。禁改清单不放宽。

## 1. 背景与问题

现状（经代码核实）：

1. **认证单一绑定平台**：`app/backend/dependencies/auth.py` 通过 `core.auth.decode_access_token` 解析 Bearer JWT，令牌由 Atoms 平台 OIDC 签发；前端 `app/frontend/src/lib/api.ts` 仅 `createClient()`，登录态完全由 `client.auth` 提供。项目无自有用户表，`user_id` 由平台注入。
2. **存储单一绑定平台**：`app/backend/services/storage.py` 直接依赖 `settings.oss_service_url` / `settings.oss_api_key`，构造函数在未配置时直接 `raise ValueError`，无替代实现。
3. **自托管路径不完整**：`docker-compose.yml` 已含 `db` + `backend` + `frontend`，但没有对象存储组件；平台 OIDC 与 OSS 在自托管环境不可用，导致该编排无法真正独立跑通登录与文件上传。
4. **规约绑定单一平台**：`.agent/constraints.md` 中写入了大量 Atoms 平台专有条款（禁改文件清单、前端须经 web-sdk、禁止自建用户表等），与 FEAT-004 确立的「`.agent/` 技术中立」目标冲突，也使规约无法用于自托管形态。

结论：认证与存储缺少抽象层，两种部署形态（平台托管 / 自托管）无法共存。

## 2. 目标

1. 认证改为**可配置切换的双实现**：Atoms 平台 Auth / 自建 PostgreSQL 用户体系。
2. 存储改为**可配置切换的双实现**：Atoms 对象存储 / 自定义 MinIO（S3 兼容）。
3. `docker compose` 新增 MinIO 组件（初始化桶、健康检查、持久化卷），使自托管编排可独立跑通。
4. `.agent/` 规约**完全技术中立**，平台专有约束迁至 `.atoms/` 侧维护，并给出两种形态的约束差异矩阵。
5. 自建用户体系在**表结构与接口层面预留团队管理与多租户**，本期不实现团队功能但设计不堵死。

## 3. 非目标

- 不做数据迁移（自托管视为全新部署，用户已确认）。
- 本期不实现团队/组织管理功能界面与业务逻辑，只做预留设计。
- 不引入第三方社交登录（微信、GitHub 等），但身份表结构为其预留。
- 不引入具体邮件服务密钥（本轮仅明确依赖与选型待定项）。
- 不改变审查链路的 AI 逻辑、提示词、结构化输出策略。
- 不改变前端视觉设计规范。

## 4. 用户故事

1. 作为自托管部署者，我 `docker compose up` 后可直接注册账号、验证邮箱、登录，无需任何外部认证服务。
2. 作为自托管部署者，我上传的合同 PDF 存入本地 MinIO 私有桶，下载时通过预签名 URL 获取，文件不出内网。
3. 作为平台使用者，切换开关默认为平台模式，现有登录与上传行为完全不变。
4. 作为管理员，我可以禁用违规账号、查看登录日志，被禁用账号立即无法获取新令牌。
5. 作为忘记密码的用户，我可通过邮箱收到重置链接，链接一次性且限时有效。
6. 作为运维，配置错误（如 local 模式未设 `JWT_SECRET`）应在**启动期**就失败并给出明确原因，而不是等到用户登录时报 500。
7. 作为未来的团队功能开发者，我在现有表上扩展组织维度时不需要重建用户表。

## 5. 功能需求

### FR-1 认证抽象层

定义与实现分离，业务代码只依赖抽象。

**抽象接口（`AuthProvider` 协议）**

| 方法 | 签名语义 | 说明 |
|------|---------|------|
| `resolve_user(token)` | `str -> AuthUser` | 由访问令牌解析出统一用户对象；失败抛 `AuthTokenError` |
| `provider_name` | `str` | 用于日志与健康检查上报，取值 `platform` / `local` |

**统一用户模型 `AuthUser`**：`id`、`email`、`name`、`role`、`tenant_id`、`status`、`last_login_at`。两种实现必须产出相同字段语义，`id` 一律为字符串形式的稳定主键。

**目录落点**

```
app/backend/auth_providers/
  __init__.py              # 工厂：按配置返回单例 provider
  base.py                  # AuthProvider 协议 + AuthUser + 异常类型
  platform_provider.py     # 包装现有 core.auth.decode_access_token
  local_provider.py        # 自建 JWT 校验 + 用户状态检查
```

**依赖注入收敛点**：`app/backend/dependencies/auth.py` 的 `get_current_user` / `get_admin_user` 保持函数签名与返回类型不变，内部改为委托工厂返回的 provider。这样**所有既有路由零改动**即可获得双模式能力，是本设计的关键收敛点。

**登录态校验与 user_id 获取**：统一由 `get_current_user` 提供，业务层禁止自行解析令牌。

### FR-2 自建用户体系（local 模式）

| 能力 | 要求 |
|------|------|
| 注册 | 邮箱 + 密码；邮箱唯一（租户内）；密码强度校验（长度、字符类型组合）；创建后状态为 `pending_verification` |
| 密码存储 | Argon2id 加盐哈希（回退方案 bcrypt）；算法与参数入库以支持后续平滑升级；**禁止**明文或可逆加密 |
| 登录 | 校验密码 → 校验账号状态 → 签发访问令牌 + 刷新令牌；写登录日志 |
| 令牌 | 访问令牌短时效（默认 15 分钟）；刷新令牌长时效（默认 14 天）且**一次性轮换**（用后失效并记录 `replaced_by`） |
| 登出 | 吊销当前刷新令牌；支持吊销该用户全部令牌族（改密、禁用时触发） |
| 邮箱验证 | 注册后发一次性激活令牌；验证成功置 `email_verified_at` 并转 `active` |
| 忘记密码 | 一次性限时重置令牌；重置成功后吊销该用户所有刷新令牌 |
| 资料管理 | 昵称、头像、修改密码（改密需校验旧密码） |
| 角色权限 | `admin` / `user`；管理员可禁用/启用账号 |
| 防暴破 | 连续失败计数 + 达阈值锁定；锁定期内拒绝登录且不泄露账号是否存在 |
| 登录日志 | 记录结果分类、时间、脱敏后的 IP 与 UA |

**安全要求**：登录失败对外统一返回「邮箱或密码错误」，不区分「账号不存在」与「密码错误」，避免账号枚举；日志中 IP、UA、邮箱一律哈希或掩码后记录。

### FR-3 存储抽象层

**抽象接口（`StoragePort` 协议）**

| 方法 | 语义 |
|------|------|
| `ensure_bucket(bucket)` | 幂等确保桶存在（私有） |
| `upload(bucket, object_key, data, content_type)` | 上传并返回 `ObjectRef(bucket, object_key, size, etag)` |
| `get_download_url(bucket, object_key, expires_seconds)` | 返回限时预签名下载 URL |
| `delete(bucket, object_key)` | 幂等删除 |
| `exists(bucket, object_key)` | 存在性判断 |
| `provider_name` | `platform` / `minio` |

**`object_key` 语义保持一致**：两种实现共用同一命名规则 `{tenant_id}/{user_id}/{yyyymm}/{uuid}.pdf`。数据库仍只存 `bucket_name` + `object_key`，**禁止持久化预签名 URL**（与 07 规范一致）。

**目录落点**

```
app/backend/storage_providers/
  __init__.py              # 工厂
  base.py                  # StoragePort 协议 + ObjectRef + 异常
  platform_provider.py     # 包装现有 services/storage.py
  minio_provider.py        # S3 兼容实现（预签名 URL、私有桶）
```

### FR-4 前端统一封装（屏蔽双模式差异）

新增 `app/frontend/src/lib/auth-provider.ts`，导出统一接口：

```
signIn / signUp / signOut / me / getAccessToken / requestPasswordReset / resetPassword / updateProfile
```

- **platform 实现**：内部调用 `client.auth`（`me` / `toLogin` / `logout`），注册、改密、重置等自建专属方法在该模式下返回「不支持」语义，由 UI 隐藏对应入口。
- **local 实现**：通过统一 HTTP 客户端调用自建认证接口，访问令牌存内存 + 刷新令牌用 `HttpOnly` Cookie（优先方案），并实现 401 自动刷新重试一次。
- 切换开关：`VITE_AUTH_MODE`。`app/frontend/src/hooks/use-auth.ts` 只依赖该统一封装，**保持 loading / authenticated / anonymous 三态语义不变**。

**数据访问路径差异（重要影响面）**：平台模式下前端通过 `client.entities` 读写 `contracts` / `review_reports`，该能力由平台提供且自带 `user_id` 隔离。自托管模式无 `client.entities`，必须由后端补一组等价 REST CRUD 路由，并在服务端强制按 `tenant_id + user_id` 过滤。因此需再新增 `app/frontend/src/lib/data-provider.ts` 做同样的双实现封装，页面只依赖它。

### FR-5 MinIO 编排

`docker-compose.yml` 新增：

- `minio` 服务：`minio/minio` 镜像，`server /data --console-address :9001`，端口 9000/9001，`healthcheck` 探活，持久化卷 `legalguard_miniodata`。
- `minio-init` 一次性任务：等 MinIO 健康后创建私有桶、设置桶策略为非公开；幂等可重复执行。
- `backend` 增加 `depends_on: minio (service_healthy)` 与 MinIO 相关环境变量注入。

### FR-6 `.agent/` 规约技术中立化

- 从 `.agent/constraints.md` 移除全部平台专有条款：禁改文件清单、前端须经 web-sdk、禁止自建用户表、平台 OIDC 唯一、`/api/v1/review/analyze` 平台超时约定、AI 网关内建能力说明等。
- `.agent/architecture.md` 中的平台绑定描述改为「按配置选择的实现」中立表述。
- 通用工程约束（分层、量化阈值、事务不跨外部调用、日志脱敏、配置读取、交付诚实性）保留。
- 平台专有约束迁入 `.atoms/ATOMS.md` 的 Constraints 段，并新增「平台模式 / 自托管模式约束差异矩阵」（见 §9），写明各条生效条件。
- `.agent/README.md` 增补：平台专有运行时约束由 `.atoms/` 维护，在平台形态下与 `.agent/` 同时生效。

## 6. 数据库表设计（local 模式，遵循 `docs/rules/07-database-acid.md`）

> 命名沿用 `snake_case` 复数；时间列统一 `TIMESTAMPTZ`；金额无关。所有表含 `created_at` / `updated_at`。

### 6.1 `users`

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | UUID | PK, default `gen_random_uuid()` | 主键 |
| `tenant_id` | UUID | NOT NULL, default 默认租户常量 | **多租户预留** |
| `email` | TEXT | NOT NULL | 原始邮箱（保留大小写用于展示） |
| `email_normalized` | TEXT | NOT NULL | 小写去空格，用于唯一与查询 |
| `password_hash` | TEXT | NOT NULL | Argon2id 编码串（含盐与参数） |
| `password_algo` | TEXT | NOT NULL, CHECK IN (`argon2id`,`bcrypt`) | 支持后续平滑升级 |
| `password_updated_at` | TIMESTAMPTZ | NOT NULL | 用于「改密后令牌失效」判定 |
| `nickname` | TEXT | NULL | 可选 |
| `avatar_object_key` | TEXT | NULL | 只存 key，不存 URL |
| `role` | TEXT | NOT NULL default `user`, CHECK IN (`admin`,`user`) | 角色 |
| `status` | TEXT | NOT NULL default `pending_verification`, CHECK IN (`pending_verification`,`active`,`disabled`) | 账号状态 |
| `email_verified_at` | TIMESTAMPTZ | NULL | 非空即已验证 |
| `failed_login_count` | INTEGER | NOT NULL default 0, CHECK `>= 0` | 防暴破计数 |
| `locked_until` | TIMESTAMPTZ | NULL | 锁定截止 |
| `last_login_at` | TIMESTAMPTZ | NULL | 最后登录 |

**唯一与索引**
- `UNIQUE (tenant_id, email_normalized)` —— 租户内邮箱唯一，天然支持后续多租户。
- `INDEX (tenant_id, status)` —— 管理端列表。
- `INDEX (tenant_id, created_at DESC)` —— 注册时间倒序分页。

**并发与幂等**：注册并发靠上述唯一约束兜底，捕获唯一冲突返回业务错误，**不用「先查后插」**。失败计数递增使用 `UPDATE ... SET failed_login_count = failed_login_count + 1` 原子自增，禁止读改写。

### 6.2 `user_identities`（多身份源预留，本期只写 `local` 一种）

| 字段 | 类型 | 约束 |
|------|------|------|
| `id` | UUID | PK |
| `user_id` | UUID | NOT NULL, FK → `users(id)` ON DELETE CASCADE |
| `provider` | TEXT | NOT NULL, CHECK IN (`local`,`platform`,`oidc`) |
| `provider_uid` | TEXT | NOT NULL |

- `UNIQUE (provider, provider_uid)`；`INDEX (user_id)`。
- 作用：未来接入社交登录或把平台账号与本地账号关联时无需改 `users`。

### 6.3 `refresh_tokens`

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | UUID | PK | |
| `user_id` | UUID | NOT NULL, FK → `users(id)` ON DELETE CASCADE | |
| `token_hash` | TEXT | NOT NULL, UNIQUE | 只存哈希，**禁止存明文令牌** |
| `family_id` | UUID | NOT NULL | 令牌族，用于整族吊销 |
| `expires_at` | TIMESTAMPTZ | NOT NULL | |
| `revoked_at` | TIMESTAMPTZ | NULL | 非空即失效 |
| `replaced_by` | UUID | NULL, FK → `refresh_tokens(id)` | 轮换链，可检测重放 |
| `ip_hash` | TEXT | NULL | 脱敏 |
| `user_agent_hash` | TEXT | NULL | 脱敏 |

- `INDEX (user_id, revoked_at)`；`INDEX (expires_at)` 供清理任务。
- **重放检测**：若使用了已 `revoked_at` 且有 `replaced_by` 的令牌，视为泄露，吊销整个 `family_id` 并记 WARNING。
- 轮换必须在**单事务**内完成「旧令牌置吊销 + 新令牌插入」，保证原子性。

### 6.4 `auth_action_tokens`（邮箱验证 / 密码重置共用）

| 字段 | 类型 | 约束 |
|------|------|------|
| `id` | UUID | PK |
| `user_id` | UUID | NOT NULL, FK → `users(id)` ON DELETE CASCADE |
| `purpose` | TEXT | NOT NULL, CHECK IN (`email_verify`,`password_reset`) |
| `token_hash` | TEXT | NOT NULL, UNIQUE |
| `expires_at` | TIMESTAMPTZ | NOT NULL |
| `consumed_at` | TIMESTAMPTZ | NULL |

- `INDEX (user_id, purpose, consumed_at)`。
- **一次性语义靠条件更新保证幂等**：`UPDATE ... SET consumed_at = now() WHERE id = :id AND consumed_at IS NULL`，受影响行数 0 表示已被使用，按幂等处理。

### 6.5 `login_audits`

| 字段 | 类型 | 约束 |
|------|------|------|
| `id` | BIGSERIAL | PK |
| `user_id` | UUID | NULL, FK → `users(id)` ON DELETE SET NULL |
| `tenant_id` | UUID | NOT NULL |
| `email_hash` | TEXT | NOT NULL |
| `result` | TEXT | NOT NULL, CHECK IN (`success`,`bad_credentials`,`locked`,`disabled`,`unverified`) |
| `ip_hash` | TEXT | NULL |
| `user_agent_hash` | TEXT | NULL |

- `INDEX (tenant_id, created_at DESC)`；`INDEX (user_id, created_at DESC)`。
- 账号不存在时 `user_id` 为空，仅记 `email_hash`，避免泄露明文。

### 6.6 团队与多租户预留（本期**不建表**，仅锁定目标形态）

后续团队功能的目标设计：`organizations(id, tenant_id, name, owner_user_id)` + `organization_members(org_id, user_id, org_role)` 且 `UNIQUE (org_id, user_id)`；业务表增加 `organization_id` 可空列，空值表示个人空间。

本期为其预留的落点：`users.tenant_id` 已就位；业务查询一律显式带 `tenant_id` 条件；`AuthUser` 已含 `tenant_id` 字段。因此后续扩展只需增表加列，不需重建用户体系。

### 6.7 与现有业务表的关系

`contracts` / `review_reports` 现有 `user_id` 语义保持不变，local 模式下写入 `users.id`。建议后续为其补 `tenant_id` 列以贯通租户隔离，本期在文档中记录为演进项而非本期改动。

## 7. 接口设计（local 模式新增；platform 模式不注册这些路由）

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/v1/auth/local/register` | 注册并发送验证邮件 | 否 |
| POST | `/api/v1/auth/local/login` | 登录，返回访问令牌 + 刷新令牌 | 否 |
| POST | `/api/v1/auth/local/refresh` | 刷新令牌轮换 | 刷新令牌 |
| POST | `/api/v1/auth/local/logout` | 吊销当前刷新令牌 | 是 |
| POST | `/api/v1/auth/local/verify-email` | 消费一次性激活令牌 | 否 |
| POST | `/api/v1/auth/local/password/forgot` | 申请重置（**无论邮箱是否存在都返回成功**，防枚举） | 否 |
| POST | `/api/v1/auth/local/password/reset` | 消费重置令牌并改密 | 否 |
| POST | `/api/v1/auth/local/password/change` | 校验旧密码后改密 | 是 |
| GET / PATCH | `/api/v1/auth/local/profile` | 读取 / 更新昵称头像 | 是 |
| GET | `/api/v1/admin/users` | 用户列表（分页、按状态筛选） | 管理员 |
| PATCH | `/api/v1/admin/users/{id}/status` | 启用 / 禁用账号 | 管理员 |
| GET | `/api/v1/admin/login-audits` | 登录日志查询 | 管理员 |
| GET | `/api/v1/auth/mode` | 返回当前认证模式，供前端自检 | 否 |

**统一错误语义**：`401` 未认证或令牌无效；`403` 角色不足或账号被禁用；`409` 邮箱已注册；`422` 入参或密码强度不合规；`429` 触发频率限制或账号锁定；错误体统一带 `trace_id`。

## 8. 配置项清单

> 均遵循 03 规范：`getattr(settings, name, default)` 读取 + 占位符校验；同步写入 `.env.example`。

### 8.1 模式开关

| 变量 | 含义 | 默认值 | 必填 | platform 模式 | 自托管模式 |
|------|------|--------|------|--------------|-----------|
| `AUTH_MODE` | 认证实现 | `platform` | 否 | `platform` | `local` |
| `STORAGE_MODE` | 存储实现 | `platform` | 否 | `platform` | `minio` |
| `VITE_AUTH_MODE` | 前端认证实现 | `platform` | 否 | `platform` | `local` |
| `VITE_API_BASE_URL` | 前端后端基址 | 空（同源） | local 模式必填 | 不使用 | 必填 |
| `DEFAULT_TENANT_ID` | 默认租户 UUID | 固定常量 | 否 | 不使用 | 建议显式设置 |

### 8.2 自建认证（`AUTH_MODE=local` 时生效）

| 变量 | 含义 | 默认值 | 必填 |
|------|------|--------|------|
| `JWT_SECRET` | 访问令牌签名密钥 | 无 | **是**（缺失即启动失败） |
| `JWT_ALGORITHM` | 签名算法 | `HS256` | 否 |
| `JWT_ISSUER` | 令牌签发者标识 | `legalguard` | 否 |
| `ACCESS_TOKEN_TTL_SECONDS` | 访问令牌有效期 | `900` | 否 |
| `REFRESH_TOKEN_TTL_SECONDS` | 刷新令牌有效期 | `1209600` | 否 |
| `PASSWORD_HASH_SCHEME` | 密码哈希算法 | `argon2id` | 否 |
| `PASSWORD_MIN_LENGTH` | 密码最小长度 | `10` | 否 |
| `PASSWORD_REQUIRE_MIXED` | 是否要求字符类型混合 | `true` | 否 |
| `LOGIN_MAX_FAILED_ATTEMPTS` | 锁定阈值 | `5` | 否 |
| `LOGIN_LOCK_DURATION_SECONDS` | 锁定时长 | `900` | 否 |
| `EMAIL_VERIFICATION_REQUIRED` | 是否强制验证邮箱后才能登录 | `true` | 否 |
| `EMAIL_VERIFY_TOKEN_TTL_SECONDS` | 激活令牌有效期 | `86400` | 否 |
| `PASSWORD_RESET_TOKEN_TTL_SECONDS` | 重置令牌有效期 | `3600` | 否 |
| `AUTH_BOOTSTRAP_ADMIN_EMAIL` | 首个管理员邮箱 | 空 | 否 |

### 8.3 MinIO（`STORAGE_MODE=minio` 时生效）

| 变量 | 含义 | 默认值 | 必填 |
|------|------|--------|------|
| `MINIO_ENDPOINT` | 服务端内部地址 | `http://minio:9000` | **是** |
| `MINIO_PUBLIC_ENDPOINT` | 预签名 URL 对外地址 | 同 `MINIO_ENDPOINT` | 否（内外网不同时必填） |
| `MINIO_ACCESS_KEY` | 访问密钥 | 无 | **是** |
| `MINIO_SECRET_KEY` | 密钥 | 无 | **是** |
| `MINIO_REGION` | 区域 | `us-east-1` | 否 |
| `MINIO_USE_SSL` | 是否 HTTPS | `false` | 否 |
| `MINIO_PRESIGN_EXPIRES_SECONDS` | 预签名有效期 | `900` | 否 |
| `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` | compose 内 MinIO 初始凭据 | 无 | 自托管必填 |
| `CONTRACT_BUCKET` | 合同桶名（复用现有变量） | `contracts` | 否 |

**`MINIO_PUBLIC_ENDPOINT` 是最易踩坑项**：预签名 URL 的签名与 host 绑定，若用内部 host 签名再给浏览器访问会直接失败，必须按对外可达地址签名。

### 8.4 邮件发送（选型待定）

| 变量 | 含义 | 状态 |
|------|------|------|
| `MAIL_PROVIDER` | `smtp` / `console` / 第三方 | 待定，开发期默认 `console`（只打印链接不发信） |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USERNAME` / `SMTP_PASSWORD` / `SMTP_USE_TLS` | SMTP 连接参数 | 待定 |
| `MAIL_FROM_ADDRESS` / `MAIL_FROM_NAME` | 发件人 | 待定 |

**本轮不收集任何邮件密钥**。开发与验证阶段用 `console` 驱动（令牌链接写入日志，且日志中链接需截断脱敏），进入真实发信前需用户确认服务商并单独走密钥收集流程。

### 8.5 启动期配置校验

新增启动自检（不修改 `core/config.py`，在应用初始化路径的可改文件中实现）：

1. 读取 `AUTH_MODE` / `STORAGE_MODE`，非法取值直接 `CRITICAL` 并终止。
2. `AUTH_MODE=local` 时校验 `JWT_SECRET` 非空、非 `$$占位符$$`、长度达标；不满足则终止启动。
3. `STORAGE_MODE=minio` 时校验 endpoint 与密钥齐备，并做一次 `ensure_bucket` 连通性探测，失败记 `CRITICAL` 并终止。
4. 自检结果输出一行汇总日志（模式 + 各项 ok/fail），**不打印任何密钥值**。
5. 校验结果暴露到健康检查响应，便于编排探活时快速定位。

原则：**配置错误必须在启动期暴露**，不允许把错误推迟到用户请求时变成 500。

## 9. 平台模式 / 自托管模式约束差异矩阵

| 约束 | 平台模式 | 自托管模式 | 生效条件 | 维护位置 |
|------|---------|-----------|---------|---------|
| 禁改 `app/backend/core/**`、`models/**`、`main.py`、`lambda_handler.py`、`AuthCallback.tsx`、`index.html`、`.mgx/config.yaml` | 强制 | 不适用（自有部署可自管） | 运行于 Atoms 平台 | `.atoms/` |
| 前端仅经 web-sdk 访问后端，禁止 fetch/axios 直连 | 强制 | 不适用（local 模式必须走 HTTP） | `AUTH_MODE=platform` | `.atoms/` |
| 禁止自建用户表，`user_id` 由平台注入 | 强制 | 反转：必须自建用户表 | 由 `AUTH_MODE` 决定 | `.atoms/` |
| 认证只用平台 OIDC | 强制 | 使用自建 JWT | 由 `AUTH_MODE` 决定 | `.atoms/` |
| 对象存储走平台 OSS | 强制 | 使用 MinIO | 由 `STORAGE_MODE` 决定 | `.atoms/` |
| AI 能力走平台网关，不作为项目密钥 | 强制 | 需自备 AI 网关或凭据 | 运行环境 | `.atoms/` |
| 分层架构与职责边界 | 强制 | 强制 | 始终 | `.agent/` |
| 代码量化阈值 | 强制 | 强制 | 始终 | `.agent/` |
| 事务不跨 AI/网络/存储调用 | 强制 | 强制 | 始终 | `.agent/` |
| 日志脱敏红线 | 强制 | 强制 | 始终 | `.agent/` |
| 配置读取用 `getattr` + 占位符校验 | 强制 | 强制 | 始终 | `.agent/` |
| 迭代流程与双确认门 | 强制 | 强制 | 始终 | `.agent/` |
| 交付诚实性红线 | 强制 | 强制 | 始终 | `.agent/` |

## 10. 风险与阻塞点（必须在确认前知悉）

### R-1 平台模式下自建用户表 —— 已实测解除（原判定为高风险，现降级为已解决）

**原判定**：平台约束禁改 `app/backend/models/**`，故自建用户体系无处安放，自建认证只能在自托管形态运行。

**实测推翻了这一判定**。2026-08-26 在平台形态实测「独立目录定义 ORM 模型 + 由应用建表」，全部步骤通过：

| 步骤 | 实测结果 |
|------|---------|
| 在独立模块作用域内定义模型并注册进 `Base.metadata` | 成功 |
| 获取平台注入的数据库引擎 | 成功 |
| 由应用侧执行建表（`checkfirst=True`） | 成功 |
| 校验实际列结构与模型定义一致 | 成功（7 列全部匹配） |
| 插入数据 | 成功 |
| 复合唯一约束是否真实生效 | 生效（重复插入被拒） |
| CHECK 约束是否真实生效 | 生效（非法枚举值被拒） |
| 清理测试表 | 成功 |

**结论**：平台数据库授予应用建表与建约束权限，且 `core/database.py` 的建表机制为 `Base.metadata.create_all`——模型模块只要被导入即会注册。因此：

- 自建用户体系的 ORM 模型定义在**新增独立目录** `app/backend/local_auth/models.py`，**不写入** `app/backend/models/**`。`from core.database import Base` 属于引用而非修改，不违反禁改约束。
- 建表由启动自检幂等执行，平台形态与自托管形态共用同一套逻辑。
- 前端在自建模式下走 `client.apiCall.invoke` 调用自建认证路由，**不使用 fetch/axios 直连**，故 web-sdk 约束同样无需放宽。
- **自建认证在平台形态与自托管形态均可运行**，可在平台预览环境端到端验证。
- **禁改清单保持不变，不放宽任何平台约束。**

残留注意点：两种形态共用表结构定义，建表逻辑必须严格幂等（`checkfirst=True`），避免重复启动报错。

### R-2 自托管缺少 `client.entities` 等价能力（高，本期一并实现）

平台模式下前端直接用 `client.entities` 读写业务表。自托管无此能力，需后端补一组 REST CRUD，并在服务端强制按 `tenant_id + user_id` 过滤，**禁止依赖前端传入身份**。用户已确认本期一并完成，对应实施计划阶段三。

### R-3 自托管缺少 AI 网关（中）

`services/ai_invoker.py` 依赖平台 AI 能力。自托管下 PDF 分析与审查模型调用需自备凭据。本迭代**不解决**该问题，仅在部署文档中标注为自托管前置依赖，否则自托管形态可跑通登录与上传但审查会失败。这是自托管完整可用性的剩余缺口，需单独迭代。

### R-4 规约中立化可能丢失平台必需约束（中）

`.agent/` 移除平台条款后，若 AI 工具只读 `.agent/` 就在平台形态下工作，可能误改禁改文件或用 axios 直连。缓解：`.agent/README.md` 显式声明「平台形态下 `.atoms/` 的平台约束同时强制生效」，并把差异矩阵放在双方都能索引到的位置；后续可考虑把「平台约束文件存在时必须一并读取」纳入文档门禁。

### R-5 令牌存储方式的安全取舍（中）

刷新令牌放 `localStorage` 有 XSS 风险，放 `HttpOnly` Cookie 需处理跨站与 CSRF。倾向方案：访问令牌只存内存、刷新令牌用 `HttpOnly` + `SameSite=Lax` Cookie + 双提交 CSRF 令牌。若部署为前后端跨域，需改 `SameSite=None` 且强制 HTTPS，此为部署约束。

### R-6 邮件能力缺失导致注册流程不闭环（中）

`EMAIL_VERIFICATION_REQUIRED=true` 且无邮件服务时用户无法激活。缓解：开发期 `MAIL_PROVIDER=console`；自托管首次部署可用 `AUTH_BOOTSTRAP_ADMIN_EMAIL` 直接置为已验证管理员，避免无法登录的死锁。

### R-7 MinIO 预签名 URL 与内外网地址不一致（中）

见 §8.3 说明。缓解：`MINIO_PUBLIC_ENDPOINT` 独立配置，并在启动自检中校验其可解析。

### R-8 双实现导致测试矩阵翻倍（低）

缓解：抽象层协议用统一契约测试（同一组用例跑两套实现），避免为每套实现各写一份。

## 11. 验收标准（AC）

| 编号 | 标准 |
|------|------|
| AC-01 | 认证抽象接口与统一用户模型定义完整，两套实现字段语义一致 |
| AC-02 | `dependencies/auth.py` 的 `get_current_user` / `get_admin_user` 签名与返回类型不变，既有路由零改动 |
| AC-03 | 存储抽象接口覆盖 ensure_bucket / upload / 预签名下载 / delete / exists，`object_key` 规则两实现一致 |
| AC-04 | 库内只存 `bucket_name` + `object_key`，无任何持久化签名 URL |
| AC-05 | 自建用户体系覆盖 FR-2 全部 11 项能力 |
| AC-06 | 表设计含唯一约束、CHECK、外键级联、必要索引，并说明并发与幂等策略 |
| AC-07 | `users` 含 `tenant_id`，团队与多租户扩展路径明确且不需重建用户表 |
| AC-08 | 密码 Argon2id 加盐哈希，算法参数入库；无明文或可逆存储 |
| AC-09 | 刷新令牌一次性轮换 + 整族吊销 + 重放检测，轮换在单事务内完成 |
| AC-10 | 登录失败不区分账号是否存在；日志中邮箱/IP/UA 全部脱敏 |
| AC-11 | 前端统一封装屏蔽双模式差异，`use-auth` 三态语义不变 |
| AC-12 | compose 新增 MinIO 含健康检查、持久化卷、私有桶幂等初始化 |
| AC-13 | 配置项清单完整（含默认值、必填、两模式取值），并同步 `.env.example` |
| AC-14 | 启动自检覆盖模式合法性、local 密钥、MinIO 连通性，失败即终止且不打印密钥 |
| AC-15 | `.agent/` 无任何平台专有条款；平台约束迁至 `.atoms/` 且差异矩阵完整 |
| AC-16 | 风险章节明确指出平台模式无法自建用户表，并给出方案供决策 |
| AC-17 | 本轮文档四份齐全、已登记索引、文档门禁通过 |
| AC-18 | 本轮未改动任何业务代码 |

## 12. 边界与约束

- 本轮**仅产出文档**，不改业务代码、不改 `.agent/`、不改 compose、不改 `.env.example`。
- 遵循既有 01/02/03/05/06/07 规范，不新造与其冲突的规则。
- 测试报告只记录本轮真实执行的文档校验结果，禁止编造功能测试数据。

## 13. 影响面预估（供 `plan.md` 展开）

| 类型 | 路径 |
|------|------|
| 新增（后端） | `auth_providers/`（4 文件）、`storage_providers/`（4 文件）、`services/local_auth.py`、`services/mailer.py`、`routers/local_auth.py`、`routers/admin_users.py`、`core_startup_check`（落在可改文件）、SQL 迁移脚本 |
| 修改（后端） | `dependencies/auth.py`（改为委托）、`services/contract_review.py` 或其调用方（改用存储抽象）、`requirements` 增量（argon2、S3 客户端、JWT 库按需） |
| 新增（前端） | `lib/auth-provider.ts`、`lib/data-provider.ts`、注册/登录/重置/资料页面（local 模式） |
| 修改（前端） | `hooks/use-auth.ts`、`lib/api.ts`、上传与历史相关页面改用 data-provider |
| 修改（编排与文档） | `docker-compose.yml`、`.env.example`、`docs/rules/03`、`docs/rules/08`、`.agent/*`、`.atoms/ATOMS.md` |
| 禁改（平台形态） | `core/**`、`models/**`、`main.py`、`lambda_handler.py`、`AuthCallback.tsx`、`index.html`、`.mgx/config.yaml` |