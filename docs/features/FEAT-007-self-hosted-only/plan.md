# 实现方案：FEAT-007 清除平台认证与硬约束，统一为自建登录与自托管架构

> 前置条件：同目录 `spec.md` 已获用户确认。未确认前不得编码。

## 基本信息

| 项 | 内容 |
|----|------|
| 迭代号 | FEAT-007-self-hosted-only |
| 对应 Spec | `./spec.md` |
| 预估工作量 | 1.5～2 人日 |
| 确认状态 | ✅ 已确认（用户 2026-08-27：确认，开始实施） |

## 1. 方案概述

产品形态从「平台 / 自托管双模式」收成**唯一自托管**：认证只留自建 JWT，**对象存储只留自建 MinIO**，数据只留一套四层 REST。平台 OIDC、web-sdk、entities、平台 OSS、模式开关、**`local_*` 过渡命名**一并删除。

关键取舍：不保留 mode 工厂；不把平台 OSS 管理台改接到 MinIO；**不保留 `/local-*` 别名**（删平台版 `api/auth.py` / `api/storage.py` / entities 后，自建文件改用这些正名）；审查改为「短事务 → 事务外从 MinIO 读文件并跑 AI → 短事务写报告」。视觉条款搬到 `.agent/design.md`。

### 备选方案对比

| 方案 | 优点 | 缺点 | 是否采用 |
|------|------|------|----------|
| A：删除平台实现，认证/存储/数据各留一条自建链路 | 与需求一致，后续不再双写 | 平台部署不可用（需求明确接受） | ✅ |
| B：保留 AUTH_MODE 开关但默认 local | 表面上「可回切」 | 平台代码与规约都会留下，与「全部清除」相反 | ❌ |
| C：只删 OIDC、保留 entities 与 web-sdk 数据面 | diff 小 | 数据面仍是平台架构，状态词与隔离规则无法统一 | ❌ |
| D：保留 `/api/v1/storage` 脚手架，内部改打 MinIO | 看似「OSS 统一」 | 把平台管理台做成半成品；本产品不需要通用建桶/列举台 | ❌ |
| E：删除平台 OSS 全部代码，业务文件只经 MinIO 端口 + 自建上传/预签名 API | 与「存储全部自建」一致 | 平台桶内旧对象不可再读（需求接受） | ✅ |

## 2. 架构与分层落点

目标调用链：

```
页面 → lib/http.ts + 领域封装（auth / contracts / storage）
     → api → services → repositories → models（tb_user / tb_contract / tb_review_report）
存储 → MinIO（`api/storage.py`，无 STORAGE_MODE，无平台 OSS）
认证 → JWT 密码认证（`api/auth.py` + `services/auth_*.py`，无 AUTH_MODE）
审查 → contract_review：从 MinIO 取对象 → 提取/AI（无 DB 事务）→ 仓储写报告与状态
```

### 2.1 后端改动

| 层 | 文件 | 改动类型 | 职责说明 |
|----|------|----------|----------|
| 规约 | `.agent/{README,constraints,architecture,rules,verification,workflow}.md`、指针三份 | 修改 | 废止平台硬约束；阅读清单加入 design.md |
| 规约 | `.agent/design.md` | 新增 | 原 constraints §6 视觉规范 |
| 规约 | `docs/rules/01～08.md`、`docs/README.md`、模板、`.atoms/*` | 修改 | 与 .agent 对齐；部署主路径改为 compose |
| api | `api/auth.py`、`api/admin_users.py` | 替换/修改 | **删除 OIDC `api/auth.py` 后**，自建登录注册从 `local_auth.py` 迁入 `api/auth.py`；prefix `/api/v1/auth`；admin 走 service |
| api | `api/contracts.py`、`api/reports.py` | 替换 | **删除 entities 版后**，由 `local_data.py` 迁入；prefix `/api/v1/contracts`、`/api/v1/reports`；经 service |
| api | `api/storage.py` | 替换 | **删除平台 OSS 版后**，由 `local_storage.py` 迁入；仅 upload + download-url |
| api | `api/contract_review.py` | 修改 | 入参改为已上传合同（contract_id）；异常映射不变 |
| api | `api/user.py`、`api/runtime_mode.py`、`api/local_*.py`（迁完后） | 删除 | OIDC profile、双模式探测、过渡文件名不得残留 |
| services | `services/auth_accounts.py`、`services/auth_sessions.py`、`services/contracts.py`（领域版） | 重命名/新增 | 由 `local_auth_*` 迁入；合同报告编排与事务边界 |
| services | `services/contract_review.py` | 修改 | AI 后调用仓储写报告；不在同一事务里调 AI |
| services | `services/auth.py`、`services/user.py`、脚手架 `services/contracts.py` / `review_reports.py`（entities 版） | 删除或替换 | OIDC 与通用实体 CRUD |
| services | `services/schema_bootstrap.py`、`startup_check.py` | 修改 | 不再建/迁 OIDC 表；不再按 AUTH_MODE 分支 |
| repositories | `repositories/user.py`、`repositories/contract.py` | 修改 | 唯一数据入口；合同 user_id 与 tb_user 对齐 |
| models | `models/user.py`、`models/contract.py`、`models/review_report.py` | 修改 | 去掉 LocalContract 等别名；状态 CHECK 一套；归属列必填；报告 FK |
| models | `models/auth.py`、`models/contracts.py`、`models/review_reports.py` | 删除 | OIDC 与垫片 |
| providers | `auth_providers/` | 修改 | 去掉 platform 实现与 AUTH_MODE 工厂 |
| storage | `storage_providers/minio_provider.py`、`base.py`、`__init__.py` | 修改 | **唯一存储实现**；`get_storage_provider()` 直接返回 MinIO，删除 mode 工厂 |
| storage | `storage_providers/platform_provider.py` | 删除 | 平台 OSS 适配器 |
| storage | `services/storage.py`、`api/storage.py`、`schemas/storage.py` | 删除 | 平台 OSS HTTP 客户端与脚手架 `/api/v1/storage/*`（建桶/列举/改名等管理台） |
| storage | `schemas/storage.py` | 替换 | 删除平台 OSS schema 后，放入上传/预签名契约（来自原 `schemas/local_storage.py`） |
| deps | `dependencies/auth.py` | 修改 | 只解析自建 JWT |
| core | `core/auth.py`（解禁后） | 修改 | JWT 只读一个密钥配置，消除双密钥 |
| main | `main.py` | 修改 | 只扫描 `api/`，不再扫描空 `routers/` |
| 测试 | `tests/test_auth.py`、`test_contracts.py`、`test_auth_providers.py`、`test_storage_providers.py`、`test_contract_review.py`、conftest | 重命名/修改 | 去掉 platform 用例与 `test_local_*` 文件名；MinIO 缺失则启动失败 |
| 配置 | `.env.example`、`docker-compose.yml` | 修改 | 去掉 mode 开关、OIDC、OSS_SERVICE_*；MinIO 无条件必填 |

### 2.2 前端改动

| 层 | 文件 | 改动类型 | 职责说明 |
|----|------|----------|----------|
| 依赖 | `package.json` / lock / `vite.config.ts` | 修改 | 移除 `@metagptx/web-sdk` 与 atoms 插件 |
| lib | `lib/http.ts`、`lib/auth-provider.ts`、`lib/data-access.ts`、`lib/storage-access.ts` | 修改 | 只保留自建实现；**storage-access 删除 `client.storage` 分支**，上传下载只打自建存储 API |
| lib | `lib/api.ts`、`lib/auth.ts`、`lib/runtime-mode.ts` | 删除 | web-sdk 单例、axios OIDC、模式开关 |
| hook | `hooks/use-auth.ts` | 修改 | 只依赖自建 auth-provider |
| 页面 | `pages/Login.tsx` 等自建页 | 保留 | 行为不变 |
| 页面 | `pages/AuthCallback.tsx`、`AuthError.tsx`、OIDC 向 `LogoutCallback` | 删除或改成自建登出提示 | 去掉 `client.auth.login()` |
| 页面 | `Review.tsx`、`History.tsx`、`ReportDetail.tsx` | 修改 | 审查不再本地 POST 报告实体；上传走 MinIO 封装 |
| 组件 | `ProtectedAdminRoute.tsx`、去掉 `contexts/AuthContext.tsx` | 修改/删除 | 管理路由改用 `hooks/use-auth` |
| 路由 | `App.tsx` | 修改 | 删除 `/auth/callback` 等 OIDC 路由 |

### 2.3 禁改文件自查（本迭代变更禁改政策）

原平台禁改清单在本迭代**废止**。允许改动，但范围仍按任务清单，禁止借机重写无关脚手架。

- [ ] 本迭代允许修改：`core/auth.py`（单一 JWT 密钥）、`main.py`（只扫 api）、删除 `AuthCallback.tsx`
- [ ] 本迭代不强制删除：`lambda_handler.py`、`.mgx/config.yaml`（解除禁改即可，避免无关大 diff）
- [ ] `index.html` 仅在仍引用平台 SDK 时修改
- [ ] `models/` 按四层正常修改

## 3. 接口契约

### 唯一认证面：`/api/v1/auth/*`

注册、登录、刷新、登出、`/me`、找回密码、邮箱验证。语义与现自建实现一致，**路径不再带 `local-`**。登录成功返回 access + refresh；登出作废刷新令牌，回跳本站 `/login` 或首页，**不**跳外部 IdP。

实施顺序：先删除 OIDC 的 `api/auth.py`，再把原 `api/local_auth.py` 迁入该正名并改 prefix。

### 删除（无兼容别名）

| 方法 | 路径 | 原因 |
|------|------|------|
| * | OIDC authorize/callback/token/logout（原平台 `/api/v1/auth`） | 平台登录；正名让给自建认证 |
| GET | `/api/v1/auth/mode` | 双模式探测 |
| * | `/api/v1/entities/contracts`、`/api/v1/entities/review_reports` | 平台 entities |
| * | `/api/v1/users/profile` | 与 `/api/v1/auth/me` 重复且绑 OIDC 表 |
| * | 平台 OSS 管理台（create-bucket / list / rename 等） | 删除不迁 |
| * | **`/api/v1/local-auth/*`、`/api/v1/local-data/*`、`/api/v1/local-storage/*`** | 过渡前缀，统一后 404 |

### 合同/报告：`/api/v1/contracts`、`/api/v1/reports`

唯一 CRUD。归属只取 JWT。越权 404。

状态词（唯一）：`pending` / `reviewing` / `completed` / `failed`。

### 唯一存储 HTTP：`/api/v1/storage/upload`、`/api/v1/storage/download-url`

删除平台 OSS `api/storage.py` 后，自建上传/预签名占用该正名。**不得**恢复建桶/列举管理台。

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/storage/upload` | multipart PDF → MinIO 私有桶；object_key 由服务端按 tenant/user 生成；返回 bucket + object_key + size |
| POST | `/api/v1/storage/download-url` | 校验当前用户对该 object 有权后，用 `MINIO_PUBLIC_ENDPOINT` 签发短时 GET URL；**不**把 URL 写入数据库 |

无模式门闩。MinIO 是唯一实现，接口始终需登录。

### `POST /api/v1/review/analyze`

**请求**：`contract_id`（及已有的合同类型、立场等），**不再**要求前端把 PDF 当 data URI 再传一遍（文件已在 MinIO）。若抽取实现仍暂需字节，由 service 从存储读取，不作为前端契约。

**响应（200）**：结构化审查 JSON（字段与现有一致），且服务端已写入 `tb_review_report`、合同状态 `completed`。

**错误码**：400 合同不存在或非本人（对外 404）；402/422/503/500 保持现语义；失败时合同可 `failed`。

## 4. 数据库变更

| 表 | 变更类型 | 字段/约束/索引 | 向后兼容 | 回滚方案 |
|----|----------|----------------|----------|----------|
| `tb_user` 及令牌/审计表 | 保持 | 仍为唯一账号 | 是 | 无结构破坏 |
| `tb_oidc_user`、`tb_oidc_state` | 停止使用 | 应用不再 create_all 这两张表 | 旧库可留空表，不强制 DROP | 不回滚平台账号 |
| `tb_contract` | 修改约束 + **补注释** | `tenant_id`/`user_id` NOT NULL；status CHECK 仅四态；去掉别名模型；表/列 `COMMENT ON` | 已有自托管行已有归属则可改 | 备份后 ALTER |
| `tb_review_report` | 修改约束 + **补注释** | 同上 + `contract_id` FK；表/列 `COMMENT ON` | 已有自托管数据可加 FK | 备份后 ALTER |
| `tb_user`、`tb_refresh_token`、`tb_one_time_token`、`tb_auth_audit` | **补库内注释** | 与 ORM `comment` 对齐的 `COMMENT ON TABLE/COLUMN`，不改列类型 | 是 | 仅注释，可再执行覆盖 |

- 事务边界：创建/更新合同短事务；**从 MinIO 读文件与 AI 均在事务外**；写报告+更新合同状态同一短事务。上传对象在写库之前完成，失败则不写合同行（或写 failed，不持有 DB 事务等 MinIO）。
- 隔离级别：默认 READ COMMITTED。
- 并发：状态用 `WHERE status = :from` 条件更新；0 行按幂等处理。
- 启动 DDL：停止 RENAME 平台旧表；禁止再在启动路径 DROP 业务数据。缺表可用 create_all 只建自建表。OIDC 空表可列入一次性空表清理，有数据则留下不删。

## 5. 配置项变更

| 变量名 | 类型 | 默认值 | 必填 | 读取位置 | 缺失时降级行为 |
|--------|------|--------|------|----------|----------------|
| `JWT_SECRET_KEY` | str | 无 | 是 | JWT 签发校验（`core.auth` 与认证服务只认这一项） | 启动失败，指出变量名。**删除 `LOCAL_AUTH_SECRET_KEY`** |
| `AUTH_PUBLIC_BASE_URL` | URL | 无 | 否 | 邮件链接 | 可回退 `FRONTEND_URL` |
| `AUTH_REQUIRE_EMAIL_VERIFICATION` | bool | false | 否 | 注册流程 | |
| `AUTH_MAX_LOGIN_FAILURES` / `AUTH_LOCK_MINUTES` | int | 既有默认 | 否 | 锁定策略 | |
| `AUTH_MODE` / `VITE_AUTH_MODE` / `VITE_DATA_MODE` / `STORAGE_MODE` / **`LOCAL_AUTH_*`** | — | 删除 | — | — | 不得再被读取 |
| OIDC issuer/client/secret 等 | — | 删除 | — | — | |
| `OSS_SERVICE_URL` / `OSS_API_KEY` | — | 删除 | — | 原 `services/storage.py` | 删除后无读取方 |
| `MINIO_ENDPOINT` | URL | 无 | 是 | MinIO 实现 | 缺失或不可达 → 启动失败 |
| `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` | str | 无 | 是 | MinIO 实现 | 缺失 → 启动失败 |
| `MINIO_PUBLIC_ENDPOINT` | URL | 默认同 ENDPOINT | 内外网不一致时必填 | 预签名 | 签出浏览器不可达 URL 视为配置错误 |
| `MINIO_REGION` / `MINIO_ADDRESSING_STYLE` / `MINIO_VERIFY_TLS` | 既有 | path / 默认 | 否 | MinIO 实现 | 沿用现默认（MinIO 须 path-style） |
| `AUTH_BOOTSTRAP_ADMIN_EMAIL` | 既有 | 可选 | 否 | schema_bootstrap | 不创建则需手动注册 |
| `VITE_APP_NAME` | str | LexHubPro | 否 | 前端标题 | 缺省即 LexHubPro，不得再默认「法盾审约」 |
| `JWT_ISSUER` | str | lexhubpro | 否 | 令牌 iss | 从 legalguard 改名后旧 token 失效 |
| `POSTGRES_USER` / `POSTGRES_DB` / `MINIO_ROOT_USER` 默认 | str | lexhubpro | 否 | compose | 与容器网络名一并改；旧卷按 T-17 迁移 |

- [ ] 不再有「不得覆盖平台注入变量」条款
- [ ] 同步 `.env.example` 与 compose（默认就是自建 + MinIO，无 mode）
- [ ] 读取仍走 `getattr` + `$$` 占位符校验

## 6. 设计模式与复杂度自查

| 模式 | 使用位置 | 选择理由 |
|------|----------|----------|
| 端口（仅 MinIO） | `storage_providers/minio_provider.py` | 删除 platform 策略与 STORAGE_MODE 工厂；一个实现不保留空开关 |
| 端口（仅 JWT 密码认证） | `auth_providers/jwt_provider.py` | 删除 platform 与 `local_provider` 文件名 |
| 仓储 | repositories/contract.py、user.py | 隔离 SQL 与归属过滤 |
| 统一 HTTP 封装 | lib/http.ts | 页面禁止散落 fetch/axios |

- [ ] 本迭代新改文件尽量不超过 400 行；`components/ui/**`、未改动的历史超标文件书面豁免
- [ ] 删除死代码（空 routers 业务扫描、别名模型、AuthContext、lib/auth.ts）
- [ ] 豁免：`lambda_handler.py`、未拆的 `services/aihub.py`（本迭代非目标）

## 7. 日志与追踪计划

| 位置 | 级别 | 前缀 | 关键字段 |
|------|------|------|----------|
| 登录成功/锁定 | INFO/WARNING | `[BIZ]` | user id、tenant、trace_id，无密码 |
| 合同写/删 | INFO | `[DB_OP]` | id、status，无 object 正文 |
| MinIO 上传/预签名/删除 | INFO | `[BIZ]` | bucket、key 长度/前缀、size；**禁止**完整签名 URL 与密钥 |
| 审查 AI | INFO | `[AI_OP]` | stage、model、耗时、文本长度 |
| 越权访问 | WARNING | `[BIZ]` | 资源 id，不暴露是否存在于他人名下（对外仍 404） |

- [ ] 不记录合同正文、base64、密钥、签名 URL、完整请求体

## 8. 任务拆分

| 编号 | 任务 | 产出文件 | 依赖 |
|------|------|----------|------|
| T-01 | 规约：废止平台硬约束、STORAGE_MODE、以及把自建叫作 local 模式的条款；写明唯一 MinIO 与正式模块名；产品名 **LexHubPro**；**保留并强化 DDL 表/字段用途注释条款**；新增 `.agent/design.md` | `.agent/*`、`docs/rules/*`、`AGENTS.md` 等 | spec/plan 确认 |
| T-02 | 文档门禁纳入 `design.md`；`verify.sh` 编译 `api/` `repositories/` `models/` `auth_providers/` `storage_providers/`，停止以 `routers/*.py` 为主 | `scripts/verify.sh`、`.agent/verification.md` | T-01 |
| T-03 | 后端删除 OIDC：模型、路由、服务、测试 | `models/auth.py` 等删除；`api/auth.py` 删除 | T-01 |
| T-04 | 认证收口为唯一 JWT 密码实现；去掉 AUTH_MODE；密钥只留 `JWT_SECRET_KEY`；**`local_auth.py` / `local_provider.py` / `LOCAL_AUTH_*` 迁到正式名后删除旧文件** | `api/auth.py`、`services/auth_*.py`、`auth_providers/jwt_provider.py`、`core/auth.py`、compose/env | T-03 |
| T-05 | **删除全部平台 OSS**：`platform_provider.py`、旧 `services/storage.py`、旧 `api/storage.py`、旧 OSS schema、`STORAGE_MODE` 工厂、`OSS_*` | 上列文件、`.env.example` | T-01 |
| T-06 | 删除 entities CRUD 与垫片模型；合同/报告经 service+repository 落到 **`api/contracts.py` + `api/reports.py`**；状态词一套；归属 NOT NULL + 报告 FK | `api/contracts.py`、`api/reports.py`、`models/contract.py`、`repositories/`、`services/` | T-04 |
| T-07 | 审查：service **从 MinIO 读对象**、AI、短事务写报告 | `services/contract_review.py`、`api/contract_review.py`、测试 | T-06、T-12 |
| T-08 | 前端删除 web-sdk/atoms、AuthCallback、AuthContext、runtime-mode；封装只打 `/api/v1/auth`、`/contracts`、`/reports`、`/storage` | `package.json`、`vite.config.ts`、`lib/*`、`App.tsx` | T-04～T-07 |
| T-09 | 管理路由改用 `use-auth`；审查/历史页去掉 entities 与双状态映射；**页面上传下载只走自建 storage-access** | 页面与 `ProtectedAdminRoute.tsx` | T-08、T-13 |
| T-10 | 清理空 `routers/` 扫描、data_models json、双密钥文档 | `main.py` 等 | T-03 |
| T-11 | 回归：pytest、lint、build、docs-only；管理员登录；**compose 上传命中 MinIO 桶**；旧 `/local-*` 返回 404；**保留表库内注释非空**；UI 显示 LexHubPro | `test-report.md` | T-02～T-17 |
| T-12 | **MinIO 收口**：`get_storage_provider()` 直接构造 MinIO；自建上传迁入 **`api/storage.py`**（`/api/v1/storage/upload|download-url`）；启动自检必连 MinIO；删 `local_storage.py` | `storage_providers/`、`api/storage.py`、`startup_check.py`、compose | T-05 |
| T-13 | **前端存储去平台**：删除 `isLocalDataMode` 与 `client.storage`；只请求 `/api/v1/storage/upload` 与 `/download-url` | `lib/storage-access.ts`、Review/ReportDetail | T-12、T-08 |
| T-14 | **存储配置与规约**：删除 `STORAGE_MODE`；MinIO 无条件必填；architecture 写「唯一 MinIO」 | 配置、规约、存储测试、conftest | T-05、T-12 |
| T-15 | **去 `local` 扫尾**：全库文件名/符号/路由/配置不得再以 `local_`、`local-`、`LOCAL_AUTH_`、`LocalUser` 等表示自建形态；`rg` 业务目录无命中（`localhost` 与 PDF 本机抽取除外） | 全量重命名后的残留、测试、规约用语 | T-04、T-06、T-12、T-13 |
| T-16 | **存量与 DDL 注释**：保留表 ORM 无缺 comment 列；用幂等 `COMMENT ON TABLE/COLUMN`（迁移或引导，不改已发布旧 Alembic 文件）写入库内；新 DDL/Alembic 必须带 `comment=`；用 `obj_description`/`col_description` 核对六张保留表 | `models/`、schema 引导或新 alembic revision、`docs/rules/07`（已含条款） | T-01、T-06 |
| T-17 | **品牌收口为 LexHubPro**：UI/邮件/`VITE_APP_NAME`/`index.html`；compose 容器、网络、卷、默认账号；`.env.example`；`JWT_ISSUER`；指针 `.grok/rules/00-lexhubpro-rules.md` 并改 `verify.sh`；Dockerfile/nginx 注释；`.wiki.md` 现行段落。已有 compose 卷 `legalguard_*` 写明 `docker volume` 迁移，避免丢库。归档 FEAT 文档不改。 | 见 spec §4.2 | T-01 |

## 9. 测试策略

| 层级 | 覆盖内容 | 用例要点 |
|------|----------|----------|
| 单元 | JWT 解析、状态词、归属过滤 | 伪造 user_id 无效；未知状态被拒 |
| 集成 | 注册登录刷新；合同 CRUD 越权 404；审查 mock AI 后库中有报告；**存储 mock MinIO 上传/预签名** | 无 OIDC；无 entities；无平台 OSS |
| 构建 | lint + build | 不得再解析 `@metagptx/web-sdk`、`client.storage` |
| 端到端 | compose：登录 → **上传进 MinIO** → 审查（无模型凭据则标明未执行）→ 历史下载预签名 | 不出现 /auth/callback；不出现 `/local-*`；不出现建桶管理台 |

删除 `test_auth_providers` / `test_storage_providers` 中的 platform 分支，改为「未配置 JWT 密钥 / MinIO 则启动失败」。`feat005_runtime_probe` 中 `STORAGE_MODE=platform` 用例删除或改为「不再识别该变量」。

## 10. 风险与回滚

| 风险 | 影响 | 概率 | 应对措施 |
|------|------|------|----------|
| 平台环境无法再部署 | 产品形态切换 | 高（预期） | 需求接受；不留开关 |
| 审查改后端落库回归不足 | 成功无报告或重复报告 | 中 | mock AI 集成测试 + 条件更新 |
| NOT NULL / CHECK 收紧导致旧脏数据升不了约束 | 启动或写入失败 | 低（自托管行本就有归属） | 迁移前检查空归属行 |
| 去掉 web-sdk 后构建缺插件 | 前端 build 失败 | 中 | 同步改 vite.config，CI 以 build 为准 |
| 改 core.auth 影响签发 | 登录 500 | 中 | 单一密钥 + 启动自检；compose 只注入一项 |
| 删除平台 OSS 后旧平台桶对象不可读 | 仅影响曾用平台存储的部署 | 高（预期） | 需求接受；自托管 MinIO 卷保留 |
| compose 卷从 `legalguard_*` 改名 | 未迁移则看起来像空库 | 中 | T-17 写明 `docker volume` 改名或外部覆盖卷名；默认新名 `lexhubpro_*` |
| `JWT_ISSUER` 改为 lexhubpro | 已签发 access/refresh 失效 | 中 | 用户重新登录即可 |
| 预签名仍用容器内 `minio:9000` | 浏览器无法下载 | 中 | 强制 `MINIO_PUBLIC_ENDPOINT` 参与签名（现实现已有，回归保住） |

- 回滚方案：git 还原本迭代提交。数据：OIDC 表本就不迁；合同状态 CHECK 收紧前备份；MinIO 卷不在本迭代删除。
- 不可回滚项：产品不再支持平台 OIDC 登录与平台 OSS。须在确认记录中明示。

## 11. 变更记录

| 日期 | 变更内容 | 原因 | 是否重新确认 |
|------|----------|------|--------------|
| 2026-08-27 | 初稿 | 评估后建档 | 待确认 |
| 2026-08-27 | 存储范围升级：全部 OSS 走自建 MinIO；删除平台 OSS 全链路；拆出 T-12～T-14 | 用户补充「存储全部自建」 | 待确认 |
| 2026-08-27 | 去除 `local` 过渡命名：文件/路由/配置/类型改正式名；增加 spec §4.1 与 T-15；无 `/local-*` 别名 | 用户确认 local 仅为区分前缀 | 待确认 |
| 2026-08-27 | DDL 与存量表强制表/字段用途注释；07 与 `.agent` 已写入条款；本迭代 T-16 补齐保留表库内注释 | 用户补充规约 | 待确认 |
| 2026-08-27 | 产品名统一 LexHubPro，替换 LegalGuard / legalguard / 法盾审约 / 契审云；T-17 | 用户补充 | 待确认 |

---

## 确认记录

| 日期 | 确认人 | 结论 | 备注 |
|------|--------|------|------|
| 2026-08-27 | 用户 | 确认 | 开始实施 |
