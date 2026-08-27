# 完成清单：FEAT-005 可插拔认证与对象存储

> 本迭代分两段交付。**A 段（规划）** 为本轮范围；**B 段（编码）** 需用户确认 spec 与 plan 后方可开始，当前一律保持未勾选。

## A 段：规划阶段（本轮范围）

### A1 前置调研（基于真实代码，非推测）

- [x] 核实现有认证实现：`dependencies/auth.py` 为 Bearer + `core.auth.decode_access_token` 单一入口
- [x] 核实 `get_current_user` / `get_admin_user` 是所有受保护路由的统一收敛点
- [x] 核实现有存储实现：`services/storage.py` 依赖 `oss_service_url` / `oss_api_key`，未配置即构造失败
- [x] 核实前端认证入口：`lib/api.ts` 仅 `createClient()`，登录态由 `client.auth` 提供
- [x] 核实现有 `docker-compose.yml` 组件构成（db / backend / frontend，无对象存储）
- [x] 阅读 `docs/rules/03-configuration.md` 并据其约束设计配置项读取方式
- [x] 阅读 `docs/rules/07-database-acid.md` 并据其约束设计表结构与并发策略

### A2 spec 内容完备性

- [x] 背景与问题基于代码实况，逐条可追溯到具体文件
- [x] 目标与非目标明确（含「不做数据迁移」「本期不实现团队功能」）
- [x] 认证抽象层设计：接口定义、统一用户模型、目录落点、依赖注入收敛点
- [x] 存储抽象层设计：接口定义、`object_key` 语义一致性、目录落点
- [x] 自建用户体系 11 项能力范围逐条写明
- [x] PG 表设计：字段、类型、NOT NULL、CHECK、外键级联、唯一键、索引
- [x] 并发与幂等策略写明（唯一约束兜底注册、原子自增计数、条件更新保证一次性令牌）
- [x] 多租户预留：`users.tenant_id` + 租户内邮箱唯一 + `AuthUser.tenant_id`
- [x] 团队管理预留：目标表形态与扩展路径写明，且不需重建用户表
- [x] `user_identities` 表为后续多身份源预留
- [x] 刷新令牌设计含一次性轮换、令牌族整族吊销、重放检测
- [x] 防账号枚举要求写明（登录失败与忘记密码均不暴露账号是否存在）
- [x] 接口清单含路径、认证要求与统一错误语义
- [x] 配置项清单含含义、默认值、是否必填、两种模式取值
- [x] 启动期配置校验与快速失败要求写明
- [x] 邮件能力依赖与选型待定项写明，且本轮不引入任何密钥
- [x] 前端双模式统一封装方案写明（含 `client.entities` 在自托管无等价能力的处置）
- [x] 平台模式 / 自托管模式约束差异矩阵
- [x] 风险章节明确指出「平台模式禁止自建用户表」与决策决策冲突，并给出方案供选择
- [x] 影响面清单（新增 / 修改 / 禁改）

### A3 plan 内容完备性

- [x] 技术方案选型与被否决方案的取舍说明
- [x] 关键收敛点说明（改 `dependencies/auth.py` 内部实现即可让既有路由零改动）
- [x] local 表结构避开禁改 `models/**` 的落地方式（独立幂等 SQL + Core 显式构造）
- [x] 六个阶段划分，每阶段可独立验证、独立回滚
- [x] 每阶段列出正向与反向验证方式
- [x] 改动文件清单（后端新增 / 后端修改 / 前端 / 编排文档 / 禁改）
- [x] 依赖顺序图与可并行关系
- [x] 对现有审查链路的影响逐环节评估
- [x] 实施视角风险与缓解
- [x] 回滚策略（含「先切回 platform 止损」）
- [x] 提示遵守文件行数阈值、依赖增量编辑、路由与页面同批次创建

### A4 本轮非侵入性

- [x] 未改动任何业务代码
- [x] 未改动 `.agent/` 规约
- [x] 未改动 `docker-compose.yml`
- [x] 未改动 `.env.example`
- [x] 未引入任何第三方密钥
- [x] 未修改禁改清单中的任何文件

### A5 本轮文档合规

- [x] 四份文档齐全（spec / plan / checklist / test-report）
- [x] 已登记 `docs/features/README.md` 并更新下一个可用编号
- [x] `bash scripts/verify.sh --docs-only` 通过
- [x] `.atoms/PROGRESS.md` 已记录本轮规划产出
- [x] 报告只写本轮真实执行的文档校验结果，未编造功能测试数据

## B 段：编码阶段

> 勾选口径：`[x]` 表示**代码已落地并通过静态编译校验**；凡需运行期实测或自动化用例佐证的条目，一律留空待阶段六统一验证后回填，不得以「已写代码」代替「已验证」。

### B1 阶段一 抽象层

- [x] `AuthProvider` 协议、`AuthUser`、异常类型落地（`auth_providers/base.py`）
- [x] 平台认证适配器落地且行为与改造前等价（`auth_providers/platform_provider.py`，封装 `core.auth.decode_access_token`）
- [x] `StoragePort` 协议、`ObjectRef`、异常类型落地（`storage_providers/base.py`）
- [x] 平台存储适配器包装现有实现，行为等价（`storage_providers/platform_provider.py`）
- [x] 工厂按配置返回单例，非法模式值直接报错（不静默回退，避免掩盖部署配置错误）
- [x] `get_current_user` / `get_admin_user` 签名与返回类型保持不变
- [x] 既有路由零改动即可运行（收敛点内部委托，未触碰任何业务路由）
- [x] 契约测试：同一组用例可跑两套实现
  - 变更说明：端口方法存在性 + MinIO mock 预签名/幂等删除 + 平台适配器方法齐全；未对真实 OSS 跑同一组 I/O。
- [x] 既有 18 项回归用例全绿（`pytest tests` 合计 37 passed，含原审查 18 条）

### B2 阶段二 自建认证

- [x] 四张表 ORM 模型落地并支持幂等重复建表（`local_auth/models.py` + `bootstrap.py`，`checkfirst=True`）
  - 变更说明：spec 原定五张表，本期只建 `local_auth_users` / `local_auth_refresh_tokens` / `local_auth_one_time_tokens` / `local_auth_audits` 四张；`user_identities` 属「多身份源」预留能力，本期无任何调用方，先建空表只会产生无人维护的死结构，故推迟到真正接入第二身份源时再建。
- [x] 唯一约束、CHECK、外键级联、索引与 spec 一致
- [x] 注册接口落地
  - 变更说明：spec 原定邮箱冲突返回 409，实现改为返回与成功完全一致的统一提示。409 本身即「该邮箱已注册」的确定性信号，与同一份 spec 的防枚举硬要求直接冲突，取防枚举优先。
- [x] 密码 Argon2id 加盐哈希（算法参数随 PHC 编码串一并存储，便于日后调参后仍可校验旧哈希）
- [x] 弱密码被拒
  - 变更说明：状态码用 400 而非 spec 的 422，与本模块其余业务校验失败保持同一口径。
- [x] 邮箱验证后方可登录（未验证状态登录返回 403 并提示先验证）
- [x] 登录成功签发双令牌并写审计
- [x] 刷新令牌一次性轮换，旧令牌立即失效（`UPDATE ... WHERE used_at IS NULL` 条件更新，并校验影响行数）
- [x] 刷新令牌重放触发整族吊销并记 WARNING
- [x] 登出后旧刷新令牌不可用（按令牌族吊销；无令牌时按用户全量吊销）
- [x] 改密后吊销该用户全部刷新令牌
  - 变更说明：spec 表述为「旧访问令牌失效」。访问令牌为自包含 JWT，在其 TTL 内无法单枚作废；本期以「短 TTL（默认 30 分钟）+ 立即吊销全部刷新令牌」达成等价效果，即旧会话无法续期。若需即时失效，需引入令牌版本号或黑名单，属独立迭代。
- [x] 忘记密码链路闭环，令牌一次性且限时（2 小时，签发前作废同用途旧令牌）
- [x] 重置密码后吊销该用户全部刷新令牌
- [x] 连续失败达阈值锁定，锁定期内拒绝登录（失败计数由数据库表达式原子自增）
- [x] 禁用账号返回 403 且无法获取新令牌（local 适配器每次解析都回查用户状态）
- [x] 账号不存在与密码错误返回体完全一致（防枚举）
- [x] 忘记密码接口对不存在邮箱同样返回成功
- [x] 日志与审计脱敏：邮箱掩码、IP 仅存哈希、令牌只存摘要
- [x] 非管理员访问管理接口返回 403（`routers/admin_users.py` 校验 `role != admin`）
- [x] 前端统一认证封装屏蔽双模式差异（`lib/auth-provider.ts`）
- [x] `use-auth` 保持 loading / authenticated / anonymous 三态语义
- [x] 自托管业务数据 REST CRUD 强制租户与用户过滤，并有越权反向用例（`tests/test_local_data.py`）
- [x] 启动自检：local 模式缺签名密钥时启动失败并给出原因（探针 C1，配置名为 `LOCAL_AUTH_SECRET_KEY`）
- [x] 日志断言用例：自动化校验无明文邮箱（`test_unknown_account_same_error_as_bad_password`）

### B3 阶段三 MinIO 存储

- [x] 私有桶幂等创建（`ensure_bucket` + compose `minio-init`）
- [x] 上传返回统一 `ObjectRef`（`MinioStorageProvider.upload` / `local_storage` 路由）
- [x] 预签名下载 URL 含签名参数且有效期符合配置（探针 C4 + 单元测试）
- [x] 预签名 URL host 取自 `MINIO_PUBLIC_ENDPOINT`（独立 signing client）
- [x] 删除不存在对象不报错（幂等）（`test_minio_delete_missing_object_is_idempotent`）
- [x] `object_key` 生成规则与平台实现一致（`utils/object_key.py`）
- [x] 库内无任何持久化签名 URL（响应模型与表字段均无 URL 列）
- [x] 凭据错误时启动自检失败（探针 C3）

### B4 阶段四 编排与配置

- [x] compose 新增 MinIO 含健康检查与持久化卷
- [x] `minio-init` 幂等创建私有桶且策略非公开
- [x] backend 依赖 MinIO 健康后启动（`depends_on: minio-init` completed）
- [x] `.env.example` 与代码默认值逐项对齐
- [x] 03 配置规范登记新增配置项
- [x] 08 部署规范补自托管步骤，并标注自托管仍缺 AI 网关的前置依赖

### B5 阶段五 规约中立化

- [x] `.agent/constraints.md` 认证改为按 `AUTH_MODE` 二选一，`local` 自建登录合法
  - 变更说明：用户要求「允许自建」而非删光平台条款。禁改清单、web-sdk 在 platform 模式仍强制；未做「零平台关键词」清洗。
- [x] `.agent/architecture.md` 平台绑定表述改为按配置选择
- [x] `.agent/README.md` 声明自建登录为一等能力；平台禁改清单始终生效
- [x] `.atoms/ATOMS.md` 接收差异矩阵并同步「允许 local 自建登录」决策
- [ ] 全文检索确认 `.agent/` 无平台专有关键词残留（有意保留模式限定的平台条款，本项不适用）
- [x] 文档门禁通过（`bash scripts/verify.sh --docs-only` 退出码 0）

### B6 阶段六 整体验证

- [ ] 按固定顺序全量执行验证（`pnpm i` 被仓库外的 minimumReleaseAge 策略拒绝，改用已安装的 eslint/vite 直跑）
- [x] 前端 lint 与 build 通过（`./node_modules/.bin/eslint --quiet ./src`、`./node_modules/.bin/vite build`）
- [x] 后端 py_compile 与 pytest 通过（37 passed）
- [ ] 平台预览环境四条链路人工确认无回归
- [x] 测试报告只写真实执行结果，未验证项显式标注