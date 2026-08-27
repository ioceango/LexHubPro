# 需求规格说明：FEAT-007 清除平台认证与硬约束，统一为自建登录与自托管架构

> 2026-08-27 提出。编码前须确认本文与 `plan.md`。

## 基本信息

| 项 | 内容 |
|----|------|
| 迭代号 | FEAT-007-self-hosted-only |
| 类型 | 需求 |
| 优先级 | P0（阻塞后续自托管演进） |
| 提出人 | 用户 |
| 创建日期 | 2026-08-27 |
| 确认状态 | ✅ 已确认（用户 2026-08-27：确认，开始实施） |

## 1. 背景与问题

上一轮评估已经说明：规约改成了「平台 / 自托管双模式」，代码却仍按「平台 entities 为主、自托管打补丁」运行。认证有 OIDC 与自建 JWT 两套；合同有 `/api/v1/entities/*` 与 `/api/v1/local-data` 两套；前端还靠 web-sdk 和模式开关翻译状态词。

本次要求更进一步，不再保留双模式：

1. **去掉平台登录**：不再提供 OIDC、`/auth/callback`、平台用户表、web-sdk `client.auth`。
2. **只保留自建认证**：邮箱 + 密码 + JWT，用户只存在 `tb_user`。
3. **视觉规范从硬约束中拆出**：色彩、字体、组件风格写入单独的 `design.md`，不再与安全红线混在同一份「违反即不合格」文件里。
4. **代码与架构统一到自建**：同一套四层、同一套 REST、同一套状态词、**同一套对象存储（本地自建 MinIO）**。
5. **平台硬约束与平台代码逻辑全部清除**：禁改脚手架、web-sdk、OIDC、entities、平台 OSS、`AUTH_MODE`/`STORAGE_MODE` 等一律废止并从实现中删除。
6. **存储全部自建**：平台 OSS 全部去掉；合同上传、下载、审查取文件、删除等一切对象读写只走自建 MinIO。
7. **去掉 `local` 命名（本次补充）**：`local` 只是相对平台的过渡前缀。统一后文件、模块、路由、配置、类型一律用正式自建名（`auth` / `contracts` / `storage` 等），**禁止再以 `local` 命名任何文件**，也不保留 `/api/v1/local-*` 路径。
8. **产品名统一为 LexHubPro（本次补充）**：所有现行项目表示（UI、邮件、compose、配置默认值、规约、容器/网络/数据卷默认名）用 **LexHubPro** 替换 LegalGuard / legalguard / 法盾审约 / 契审云，不再并用旧名。

不完成这一步，后续每个功能都还要写两套分支，自托管也无法成为唯一产品形态。

## 2. 范围

### 2.1 本次要做

- 规约：产品形态固定为自托管；认证只有自建 JWT；**对象存储只有自建 MinIO**；前端只经自建 HTTP 封装访问后端。
- 命名：删除所有以 `local` 作为「相对平台」区分的文件名与公开符号；认证/合同/存储使用正式路径与模块名（见 FR-14 对照表）。不保留旧 `/local-*` 别名。
- 品牌：现行对外与对内项目名统一为 **LexHubPro**（见 FR-16）；技术标识用 `lexhubpro`（小写）。归档迭代文档可保留历史用词作追溯。
- 数据库：建表 DDL（含 Alembic）必须带表用途注释与每个字段的用途注释；已有且本迭代仍保留的 `tb_*` 若库内无注释，必须补 `COMMENT ON`（与 ORM 文案一致）。
- 存储：一切 OSS 语义（上传、预签名下载、删除、建桶）只针对本地 MinIO；删除平台 OSS 适配器、平台 OSS HTTP 服务客户端、脚手架 `/api/v1/storage/*`、web-sdk 存储调用、`STORAGE_MODE` 与 `OSS_SERVICE_URL`/`OSS_API_KEY`。
- 规约：删除全部平台硬约束（禁改脚手架文件、web-sdk 义务、OIDC 唯一、平台注入变量不可覆盖、entities 自动隔离、平台 Publish 作为主部署路径）。
- 规约：视觉设计从 `.agent/constraints.md` 迁到 `.agent/design.md`；阅读清单与文档门禁纳入该文件。
- 规约：审查结果由后端落库；不再把「前端经 entities 写报告」写成架构决策。
- 代码：删除平台登录、OIDC 表与路由、web-sdk 认证/entities/storage 调用、双模式开关、平台存储适配器、平台 OSS `StorageService` 与 `/api/v1/storage` 路由。
- 代码：合同/报告只走一套自建 REST；仓储按令牌强制 `tenant_id + user_id`；状态词只留一套。
- 代码：认证前端只保留自建登录注册链路；管理路由与全站共用同一套登录状态。
- 验证脚本与细则（`docs/rules`、模板、指针摘要、`.atoms` 架构）与 `.agent/` 对齐，去掉 `routers/`、OIDC、entities、平台 Publish 主路径等过时表述。

### 2.2 本次明确不做

- 不新造一套 AI 网关产品。现有 HTTP 调用封装可继续用环境变量指向可用模型服务；只删除「必须走平台 AI 网关」的规约与分支。
- 不把支付、博客做成完整产品。
- **不把脚手架 `/api/v1/storage` OSS 管理台改接到 MinIO 做成存储控制台**；该组平台 OSS 接口直接删除。业务文件读写（合同 PDF）统一走自建存储 API + MinIO。
- 不把历史超行数文件一次性拆完；本迭代只处理因删除平台路径而必须改动的文件。
- 不引入社交登录或其它第二套认证。
- 不保留 `AUTH_MODE=platform` / `STORAGE_MODE=platform` 兼容层，也不做双模式回滚开关。
- 不保留 `local_*` 文件名或 `/api/v1/local-*` 兼容别名（前端与脚本同步改正式路径）。
- 不把已有 OIDC 用户自动迁移进 `tb_user`（身份模型不同，本产品不再支持平台账号）。
- 不回写 `logs/`，不强制改写已归档 FEAT-001～006 / 已关闭 BUG 文档中的历史产品名。
- 不重新上传 CDN 上文件名含 legalguard 的历史 logo 对象；只改展示文案与 alt。
- 不要求改与双模式无关的用语：主机名 `localhost`、PDF **本机**抽取（相对调用 AI，如 `extract_text_locally`）可以保留，因为它们不是「相对平台的自建形态」命名。

## 3. 用户故事

1. 作为使用者，我只用邮箱密码注册登录，登出后回到本站登录页，不再跳到外部 IdP。
2. 作为部署者，我只配自建 JWT 密钥与自建 MinIO，不必再选 platform/local，也不必配平台 OSS 地址或密钥。
3. 作为开发者，我看到的模块和路由就是 `auth` / `contracts` / `storage`，没有 `local_` 前缀，也不会再碰到 OIDC、entities 或平台 OSS。
4. 作为使用者，我上传的合同 PDF 只进自建 MinIO 私有桶；下载链接由本服务用 MinIO 预签名，不经过平台对象存储。
5. 作为规范执行者，我在 `.agent/` 里看不到平台禁改清单、web-sdk 义务和「按 STORAGE_MODE 选平台 OSS」；视觉问题去 `design.md`。
6. 作为使用者，我在页头、登录页、邮件标题看到的产品名是 LexHubPro，而不是法盾审约或 LegalGuard。

## 4. 功能需求

| 编号 | 需求描述 | 输入 | 期望输出 | 备注 |
|------|----------|------|----------|------|
| FR-1 | 认证唯一实现为自建邮箱密码 + JWT | 登录/注册/刷新/登出 | 只经自建接口完成；无 OIDC 跳转 | 删除平台登录 |
| FR-2 | 用户只存在自建用户表 | 账号生命周期 | 不再读写平台 OIDC 用户/state 表 | 表名保持 `tb_user` |
| FR-3 | **对象存储唯一实现为自建 MinIO** | 上传/预签名下载/删除/审查取文件 | 字节只进 MinIO 私有桶；库内只存 `bucket_name` + `object_key`，禁止存签名 URL | 无第二套 OSS |
| FR-4 | 前端唯一访问后端通道为自建 HTTP 封装 | 页面数据/认证/存储 | 页面不 import web-sdk，不散落 fetch/axios | |
| FR-5 | 合同与报告只暴露一套 REST | CRUD | 删除 entities 路径与双状态词映射 | 归属只取令牌 |
| FR-6 | 审查在 AI 完成后由后端写报告并更新合同状态；PDF 从 MinIO 读取 | 已上传合同 | 前端不再传 PDF data URI，也不再经 entities 落库 | 事务不跨越 AI / 不跨越存储调用 |
| FR-7 | 规约清除全部平台硬约束与双模式条款 | `.agent/`、指针、`docs/rules`、模板 | 现行条款中不再出现平台登录/web-sdk/平台 OSS/`STORAGE_MODE`/禁改脚手架/entities 义务 | |
| FR-8 | 视觉规范独立成 `design.md` | 原 constraints 视觉章节 | constraints 不再含设计 token；门禁校验 design.md 存在且非空 | |
| FR-9 | 全站与管理端共用自建登录状态 | 管理页 | 不再使用 axios OIDC 客户端或第二套 AuthContext | |
| FR-10 | 配置只保留自托管项 | `.env.example` / compose | 删除 AUTH_MODE、STORAGE_MODE、VITE_*_MODE、OIDC、OSS_SERVICE_URL、OSS_API_KEY；MinIO 项必填 | JWT 只保留一个密钥名 |
| FR-11 | **删除全部平台 OSS 代码** | 存量平台存储实现 | 无 `PlatformStorageProvider`、无 `StorageService`（平台 HTTP）、无 `/api/v1/storage/*` 脚手架、无 `client.storage`、无 `STORAGE_MODE` 工厂 | 不改接到 MinIO 做管理台 |
| FR-12 | **业务文件只经自建存储 API** | 合同 PDF 上传/下载 | 唯一 HTTP：`/api/v1/storage/upload` 与 `/api/v1/storage/download-url`（MinIO）；无模式门闩 | 前端 `storage-access` 无 platform 分支 |
| FR-13 | compose 中 MinIO 为一等且唯一对象存储 | 部署 | `minio` + `minio-init` 必起；预签名按 `MINIO_PUBLIC_ENDPOINT`；缺失凭据或连不上则启动失败，禁止回退平台 OSS | |
| FR-14 | **去除 `local` 过渡命名** | 现有 `local_*` 文件、路由、配置、类型 | 全部改为正式自建名（见下方对照表）；仓库中不再存在以 `local_` 或 `local-` 命名的业务文件；公开 API 不再含 `/local-` | 见对照表；无兼容别名 |
| FR-15 | **建表 DDL 与存量表必须含表用途注释、字段用途注释** | 保留的 `tb_*` 及后续新表 | ORM `comment=`、Alembic/DDL 的 `COMMENT ON TABLE` / `COMMENT ON COLUMN`、库内 `pg_description` 三者一致；存量缺则幂等补齐 | 即将删除的 OIDC 表不必补 |
| FR-16 | **项目表示统一为 LexHubPro** | 现行 UI、邮件、规约、compose、env、容器名、指针文件 | 不再出现 LegalGuard / legalguard / 法盾审约 / 契审云 作为现行产品名；技术 id 为 `lexhubpro` | 见 §4.2；历史 FEAT 文档可保留 |

### 4.1 命名对照（旧名全部废止，无别名）

`local` 只用于曾经区分平台。删掉平台之后，自建实现就是正名。

| 类别 | 废止 | 正式名 |
|------|------|--------|
| HTTP | `/api/v1/local-auth/*` | `/api/v1/auth/*`（登录注册刷新登出 `/me` 等） |
| HTTP | `/api/v1/local-data/contracts`、`/reports` | `/api/v1/contracts`、`/api/v1/reports` |
| HTTP | `/api/v1/local-storage/*` | `/api/v1/storage/upload`、`/api/v1/storage/download-url` |
| 文件 | `api/local_auth.py` | `api/auth.py`（先删 OIDC 版 `api/auth.py`） |
| 文件 | `api/local_data.py` | `api/contracts.py` + `api/reports.py`（先删 entities 版） |
| 文件 | `api/local_storage.py` | `api/storage.py`（先删平台 OSS 版） |
| 文件 | `services/local_auth_accounts.py`、`local_auth_sessions.py` | `services/auth_accounts.py`、`services/auth_sessions.py` |
| 文件 | `schemas/local_auth.py`、`local_data.py`、`local_storage.py` | `schemas/auth.py`、`schemas/contracts.py`、`schemas/reports.py`、`schemas/storage.py` |
| 文件 | `auth_providers/local_provider.py` | `auth_providers/jwt_provider.py`（或并入唯一实现，文件名不得含 local） |
| 文件 | `tests/test_local_auth.py`、`test_local_data.py` | `tests/test_auth.py`、`tests/test_contracts.py` |
| 类型 | `LocalUser`、`LocalRefreshToken`、`LocalContract`、`LocalAuthError` 等 | `User`、`RefreshToken`、`Contract`、`AuthError` |
| 配置 | `LOCAL_AUTH_SECRET_KEY` | `JWT_SECRET_KEY`（唯一密钥名） |
| 配置 | `LOCAL_AUTH_PUBLIC_BASE_URL`、`LOCAL_AUTH_REQUIRE_EMAIL_VERIFICATION`、`LOCAL_AUTH_MAX_LOGIN_FAILURES`、`LOCAL_AUTH_LOCK_MINUTES` | `AUTH_PUBLIC_BASE_URL`、`AUTH_REQUIRE_EMAIL_VERIFICATION`、`AUTH_MAX_LOGIN_FAILURES`、`AUTH_LOCK_MINUTES` |
| 前端 | `isLocalAuthMode` / `isLocalDataMode` / `LOCAL_*_PREFIX` | 删除模式判断；前缀即上述正式 HTTP |

### 4.2 产品名对照（现行表示，无旧名并存）

展示名一律 **LexHubPro**。资源标识、容器、库名、网络、默认账号一律 **lexhubpro**（小写、无连字符，除非文件名需要）。

| 类别 | 废止 | 正式 |
|------|------|------|
| 产品名 | LegalGuard、法盾审约、契审云 | LexHubPro |
| 规约/文档现行标题 | 「法盾审约（LegalGuard）」 | LexHubPro |
| UI / `VITE_APP_NAME` / 页头 / `index.html` title | 法盾审约、契审云、LegalGuard | LexHubPro |
| 邮件标题 | 【法盾审约】 | 【LexHubPro】 |
| Grok 指针文件 | `.grok/rules/00-legalguard-rules.md` | `.grok/rules/00-lexhubpro-rules.md`（verify.sh 同步） |
| compose 容器 | `legalguard-db` 等 | `lexhubpro-db`、`lexhubpro-minio`、`lexhubpro-backend`、`lexhubpro-frontend` |
| compose 网络 / 数据卷 | `legalguard`、`legalguard_pgdata`、`legalguard_minio_data` | `lexhubpro`、`lexhubpro_pgdata`、`lexhubpro_minio_data`（已有卷按 plan 迁移，避免丢数据） |
| Postgres / MinIO 默认用户与库名 | `legalguard` | `lexhubpro` |
| `JWT_ISSUER` | `legalguard` | `lexhubpro`（换签发者后旧 access token 失效，需重新登录） |
| 前端 logo alt | LegalGuard 标识 | LexHubPro 标识 |
| 远端 CDN 上 `logo-legalguard-*.png` 的 URL 路径 | 不强制改对象存储里的历史文件名 | 展示文案与 alt 用 LexHubPro；URL 可保留，plan 注明 |

不改：已归档 `docs/features/FEAT-001`～`FEAT-006`、已关闭 BUG 文档中的历史叙述（追溯用）。`logs/` 不回写。

## 5. 异常与边界场景

| 编号 | 场景 | 期望行为 |
|------|------|----------|
| E-01 | 未登录访问需鉴权接口 | 401，前端进入登录页，不误判为业务失败 |
| E-02 | 访问令牌过期 | 用刷新令牌换新；刷新失败则回到登录页 |
| E-03 | 请求体携带 `user_id` / `tenant_id` | 服务端忽略，归属只取令牌 |
| E-04 | 访问他人合同或报告 | 统一 404，不 403 |
| E-05 | MinIO 不可达或缺少 `MINIO_*` | 启动失败或上传失败，明确配置项名称，**不**静默落到平台 OSS |
| E-06 | 审查时 AI 失败 | 保持 402/422/503/500 语义；合同可标 failed，不写残缺成功报告 |
| E-07 | 空库首次使用 | 可引导管理员；登录/注册页可用；历史页空态 |
| E-08 | 仍请求已删除的 OIDC / entities / mode / 旧平台 OSS 管理台，或 **旧 `/api/v1/local-*`** | 404，不提供兼容别名 |
| E-09 | 下载他人 object_key 或伪造 bucket | 服务端按令牌与对象键规则拒绝，不签发他人文件的预签名 URL |
| E-10 | 配置里仍写 `STORAGE_MODE=platform` 或 `OSS_SERVICE_URL` | 这些变量不再被读取；不得据此启用任何存储实现 |

## 6. 非功能需求

| 维度 | 要求 |
|------|------|
| 性能 | 审查仍允许长耗时；前端对审查接口超时保持 600s；普通 CRUD 短请求 |
| 可靠性 | 审查：短事务建记录 → 无事务 AI → 短事务写结果；失败可按状态重试，不产生「成功无报告」 |
| 安全与隐私 | 行级隔离在仓储；日志仍禁止合同正文、PDF base64、prompt 全文、密钥、签名 URL |
| 可观测性 | 登录/刷新/锁定继续打 `[BIZ]`；写库 `[DB_OP]`；AI `[AI_OP]`；均带 `trace_id` |
| 兼容性 | **故意不兼容**平台 OIDC、entities、平台 OSS；已有自建账号与 MinIO 中的合同对象必须仍能登录与下载 |
| 可维护性 | 四层单向；api 不直接打仓储；一个聚合一套 model/repository/service/api；**文件与路由名即正式资源名，不用 local 前缀** |

## 7. 验收标准

- [ ] AC-01：现行 `.agent/`（含指针摘要）中不再把平台 OIDC、web-sdk、entities、`AUTH_MODE=platform`、`STORAGE_MODE=platform`、禁改 `core/**` / `AuthCallback.tsx` / `index.html` / `.mgx/config.yaml` 作为有效硬约束
- [ ] AC-02：`.agent/design.md` 存在且包含原视觉规范；`.agent/constraints.md` 不再包含设计 token 条款；文档门禁将 `design.md` 列为必需文件
- [ ] AC-03：仓库中不再存在平台认证实现（OIDC 路由、OIDC 用户/state 模型、web-sdk `client.auth`、`AuthCallback` 页、axios OIDC 客户端）
- [ ] AC-04：登录、注册、刷新、登出、找回密码只走 `/api/v1/auth/*`；浏览器旅程不出现外部 IdP 跳转
- [ ] AC-05：合同/报告只走 `/api/v1/contracts` 与 `/api/v1/reports`；无 `/api/v1/entities/*`；前端不再调用 `client.entities`；状态词只有一套且与库 CHECK 一致
- [ ] AC-06：仓库中不再存在平台 OSS 实现：无 `PlatformStorageProvider`、无调用 `OSS_SERVICE_URL` 的 `StorageService`、无脚手架式建桶/列举管理台、无 `client.storage`、无 `STORAGE_MODE` 分支；业务存储 HTTP 为 `/api/v1/storage/upload` 与 `/download-url`
- [ ] AC-07：前端 `package.json` 不再依赖 `@metagptx/web-sdk`；页面与 lib 不再 import 该包
- [ ] AC-08：配置与 compose 不再出现 platform 模式开关、OIDC 项、`OSS_SERVICE_URL`/`OSS_API_KEY`；JWT 只需一个密钥名；MinIO 项为必填
- [ ] AC-09：`tb_oidc_user` / `tb_oidc_state` 不再被应用创建或读写；唯一账号表为 `tb_user`
- [ ] AC-10：审查成功后报告出现在历史/详情中，即使前端不再单独 POST 报告实体；事务不跨越 AI 调用
- [ ] AC-11：管理端与全站使用同一自建登录状态，管理员路由不再依赖已删除的 OIDC AuthContext
- [ ] AC-12：`docs/rules`、模板、`.atoms/ARCHITECTURE.md`、`verify.sh` 与 `.agent/` 无「必须走 routers/entities/OIDC/平台 Publish」的现行条款；`verify.sh` 编译 `api/` 等实际目录
- [ ] AC-13：既有自建账号（如本地管理员）在清平台代码后仍能登录；`bash scripts/verify.sh --docs-only` 与后端 pytest、前端 lint/build 按 verification 顺序通过
- [ ] AC-14：合同上传、下载、删除、审查取文件全部只打自建 MinIO；前端存储封装无 platform 分支；存储 API 无模式门闩
- [ ] AC-15：规约与 `docs/rules/03`、`08`、`.env.example` 将对象存储描述为「唯一 MinIO」，不再写「平台 OSS 或 MinIO 二选一」
- [ ] AC-16：`app/backend` 与 `app/frontend/src` 下无以 `local_` / `local-` 命名的业务文件；无 `LocalUser` 等过渡类型作为公开名；无 `LOCAL_AUTH_*` 配置；无 `/api/v1/local-` 路由；`.agent/` 与 `docs/rules` 现行条款不再把自建实现叫作 local 模式
- [ ] AC-17：`.agent/architecture.md`、`.agent/rules.md`、`docs/rules/07` 现行条款要求建表 DDL 含 `COMMENT ON TABLE` 与每列 `COMMENT ON COLUMN`；保留表（`tb_user`、`tb_refresh_token`、`tb_one_time_token`、`tb_auth_audit`、`tb_contract`、`tb_review_report`）在库内 `obj_description` / `col_description` 均非空，且与 ORM `comment` 一致
- [ ] AC-18：现行代码、compose、`.env.example`、`.agent/`、`docs/README.md`、`docs/rules`、指针文件、UI 与邮件中，产品名与默认技术标识为 LexHubPro / `lexhubpro`；对 `app/`、`.agent/`、`docker-compose.yml`、`.env.example`、`scripts/verify.sh` 检索 `legalguard` / `LegalGuard` / `法盾审约` / `契审云` 无现行命中（归档 FEAT/BUG 文档与 `logs/` 除外）

## 8. 影响面评估

| 维度 | 影响 |
|------|------|
| 涉及页面/入口 | 删除 OIDC 回调/错误页；登录注册等自建页保留；管理路由改挂自建 hook；审查/历史/报告改为只走自建数据面；上传下载只走自建存储封装；**页头/登录/首页/title 改为 LexHubPro** |
| 涉及接口 | 删除 OIDC `/api/v1/auth`、`/api/v1/entities/*`、`/api/v1/auth/mode`、平台 OSS 管理台、**全部 `/api/v1/local-*`**；正式接口为 `/api/v1/auth`、`/api/v1/contracts`、`/api/v1/reports`、`/api/v1/storage/upload|download-url`、审查 |
| 数据结构变化 | 停止使用 OIDC 表；合同/报告归属列与状态 CHECK 收口；**保留表补齐库内表/字段注释**（不改列语义则向后兼容） |
| 配置项变化 | 删除 AUTH_MODE、STORAGE_MODE、VITE_*_MODE、OIDC、OSS_*、**LOCAL_AUTH_***；JWT 唯一密钥名 `JWT_SECRET_KEY`；`VITE_APP_NAME`/`JWT_ISSUER`/Postgres/MinIO 默认标识改为 LexHubPro / `lexhubpro` |
| 对现有功能的风险 | 平台部署与平台 OSS 中的对象不可再访问；自托管登录、已有 `tb_*` 与 MinIO 桶内对象必须保住 |

## 9. 待确认问题

| 编号 | 问题 | 结论 |
|------|------|------|
| Q-01 | 是否保留 `AUTH_MODE=platform` 兼容开关？ | **否**。按本次要求全部清除，不留兼容层。 |
| Q-02 | 平台对象存储是否一并删除？OSS 是否全部走自建 MinIO？ | **是（2026-08-27 确认）**。存储全部自建；平台 OSS 全部删除；业务文件统一 MinIO。不把脚手架 OSS 管理台改接到 MinIO。 |
| Q-07 | 统一后是否还保留 `local_*` 文件名和 `/local-*` 路由？ | **否（2026-08-27 确认）**。`local` 仅为相对平台的过渡前缀。文件、模块、路由、配置、类型一律改正式名，不留别名。 |
| Q-08 | 建表 DDL 与存量表是否必须有表/字段用途注释？ | **是（2026-08-27 确认）**。ORM、DDL、库内 `COMMENT ON` 一致；存量保留表缺注释则补齐。 |
| Q-09 | 产品名是否统一为 LexHubPro，替换 LegalGuard / legalguard / 法盾审约？ | **是（2026-08-27 确认）**。现行表示一律 LexHubPro；技术 id 用 `lexhubpro`。归档迭代文档不强制改写。 |
| Q-03 | 视觉规范放到哪里？ | `.agent/design.md`，并纳入文档门禁必需文件。 |
| Q-04 | 审查是否改为后端落库？ | **是**。这是去掉 entities 后保持架构统一的必要部分。 |
| Q-05 | 是否本迭代实现自建 AI 网关？ | **否**。只去掉平台绑定；模型地址走配置。 |
| Q-06 | 原先禁改的 `core/**` 等是否解禁？ | **是**。不再作为平台硬约束；本迭代只改认证密钥等必要处，不借机重写全部脚手架。 |

---

## 确认记录

| 日期 | 确认人 | 结论 | 备注 |
|------|--------|------|------|
| 2026-08-27 | 用户 | 确认 | 开始实施 |
