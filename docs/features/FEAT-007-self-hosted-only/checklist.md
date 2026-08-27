# Checklist：FEAT-007 清除平台认证与硬约束，统一为自建登录与自托管架构

> 条目对应 `spec.md` 验收标准与 `plan.md` 任务。编码尚未开始，状态全部未完成。

| 项 | 内容 |
|----|------|
| 迭代号 | FEAT-007-self-hosted-only |
| 关联文档 | `./spec.md`、`./plan.md` |
| 最后更新 | 2026-08-27 |

## 1. 功能验收（对应 spec 的 AC）

| 编号 | 验证项 | 状态 | 实际结果 / 证据 |
|------|--------|------|-----------------|
| AC-01 | `.agent/` 与指针摘要不再把 OIDC、web-sdk、entities、platform 模式、脚手架禁改列为有效硬约束 | ⬜ | |
| AC-02 | `.agent/design.md` 存在且含原视觉规范；constraints 不再含设计 token；门禁将 design.md 列为必需 | ⬜ | |
| AC-03 | 仓库无平台认证实现（OIDC 路由/模型、web-sdk client.auth、AuthCallback、axios OIDC 客户端） | ⬜ | |
| AC-04 | 登录注册刷新登出找回密码只走 `/api/v1/auth/*`，无外部 IdP 跳转 | ⬜ | |
| AC-05 | 合同/报告只走 `/api/v1/contracts` 与 `/api/v1/reports`；无 entities；状态词一套 | ⬜ | |
| AC-06 | 无平台 OSS 管理台与 client.storage；业务存储为 `/api/v1/storage/upload|download-url` | ⬜ | |
| AC-07 | 前端不再依赖 `@metagptx/web-sdk`，无对应 import | ⬜ | |
| AC-08 | 配置无 platform 开关、OIDC、OSS_SERVICE_*；JWT 一个密钥名；MinIO 必填 | ⬜ | |
| AC-09 | 应用不再创建或读写 `tb_oidc_user` / `tb_oidc_state`；账号表只有 `tb_user` | ⬜ | |
| AC-10 | 审查成功后后端已写报告；事务不跨 AI | ⬜ | |
| AC-11 | 管理端与全站共用 `hooks/use-auth`，无 OIDC AuthContext | ⬜ | |
| AC-12 | docs/rules、模板、atoms 架构、verify.sh 与 .agent 对齐；编译目标含 api/ 等实际目录 | ⬜ | |
| AC-13 | 既有自建管理员可登录；docs-only、pytest、lint、build 按序通过 | ⬜ | |
| AC-14 | 合同上传/下载/删除/审查取文件只打 MinIO；storage-access 无 platform 分支 | ⬜ | |
| AC-15 | 规约与 env/compose 将对象存储写为「唯一 MinIO」，不再二选一 | ⬜ | |
| AC-16 | 无 `local_`/`local-` 业务文件、无 `LOCAL_AUTH_*`、无 `/api/v1/local-`、无 LocalUser 公开类型 | ⬜ | |
| AC-17 | 规约要求 DDL 含表/字段用途注释；六张保留表库内 obj_description/col_description 非空且与 ORM 一致 | ⬜ | |
| AC-18 | 现行代码/规约/compose/UI/邮件产品名为 LexHubPro；检索 legalguard/法盾审约/契审云无现行命中（归档文档与 logs 除外） | ⬜ | |

## 2. 异常场景验证

| 编号 | 场景 | 期望行为 | 状态 | 实际结果 |
|------|------|----------|------|----------|
| E-01 | 未登录访问需鉴权接口 | 401，前端进登录页 | ⬜ | |
| E-02 | 访问令牌过期 | 刷新成功续期；刷新失败回登录 | ⬜ | |
| E-03 | 请求体携带身份字段 | 忽略，归属只取令牌 | ⬜ | |
| E-04 | 访问他人合同或报告 | 404 | ⬜ | |
| E-05 | MinIO 不可达或缺少 MINIO_* | 启动或上传失败并指出配置，不落到平台 OSS | ⬜ | |
| E-06 | 审查 AI 失败 | 402/422/503/500 语义；不写残缺成功报告 | ⬜ | |
| E-07 | 空库首次使用 | 可引导管理员；历史空态 | ⬜ | |
| E-08 | 请求已删除 OIDC/entities/mode/平台 OSS 管理台或旧 `/local-*` | 404，无别名 | ⬜ | |
| E-09 | 下载他人 object_key | 不签发预签名 | ⬜ | |
| E-10 | 配置仍写 STORAGE_MODE=platform 或 OSS_SERVICE_URL | 变量不被读取，无存储实现被启用 | ⬜ | |

## 3. 分层与设计规范

- [ ] 改动落在 plan 声明位置；api 不直接 import repository；文件名为 auth/contracts/storage 正名
- [ ] service 不处理 HTTP、不裸 SQL
- [ ] repository 只做数据访问，commit 由 service 控制
- [ ] 表名 `tb_*`，表与字段有用途 comment；DDL/库内 `COMMENT ON` 已落地；无 OIDC 业务表依赖
- [ ] 前端页面无 web-sdk、无内联 JSON.parse 领域逻辑
- [ ] 原平台禁改政策已从规约删除；本迭代未借机重写无关脚手架
- [ ] 新改业务文件尽量 ≤ 400 行；`components/ui/**` 与未改动历史超标已豁免
- [ ] 已删除死代码：axios OIDC 客户端、AuthContext、垫片模型别名、空 routers 扫描

## 4. 日志与追踪

- [ ] 改动路由挂载 `bind_trace_id`
- [ ] 登录/写库/AI 埋点不含敏感正文与密钥
- [ ] 越权不在对外响应中确认资源存在

## 5. 配置管理

- [ ] `.env.example` 与 compose 已去掉 platform/OIDC/双模式变量
- [ ] JWT 文档只保留一个密钥名
- [ ] MinIO 项为无条件必填；已删除 STORAGE_MODE 与 OSS_SERVICE_URL / OSS_API_KEY
- [ ] 读取仍校验 `$$` 占位符

## 6. 数据库与事务

- [ ] 审查事务不跨 AI / 存储下载可在事务外完成
- [ ] 写报告与合同状态同一短事务
- [ ] 状态条件更新，0 行按幂等处理
- [ ] 报告 `contract_id` 有 FK；归属列自建场景必填
- [ ] 启动路径不再为平台表做破坏性 DDL
- [ ] 保留表已补 `COMMENT ON TABLE/COLUMN`，与 ORM 文案一致

## 7. 任务勾选（对应 plan T-01～T-17）

- [ ] T-01 规约与 design.md（含 DDL 注释条款与产品名 LexHubPro，改架构文档时不得删掉）
- [ ] T-02 verify.sh / verification.md
- [ ] T-03 删除 OIDC 后端
- [ ] T-04 唯一 JWT 密码认证落到 `api/auth.py`；删除 `LOCAL_AUTH_*` 与 `local_auth*` 文件
- [ ] T-05 删除全部平台 OSS
- [ ] T-06 合同/报告落到 `api/contracts.py` + `api/reports.py`
- [ ] T-07 审查从 MinIO 读对象并后端落库
- [ ] T-08 前端去掉 web-sdk；封装打正式 `/api/v1/auth|contracts|reports|storage`
- [ ] T-09 管理路由与页面收口
- [ ] T-10 残留清理
- [ ] T-11 验证与报告；旧 `/local-*` 为 404
- [ ] T-12 存储正名为 `api/storage.py`；唯一 MinIO
- [ ] T-13 前端 storage-access 删除 client.storage
- [ ] T-14 存储配置与规约改为唯一 MinIO
- [ ] T-15 去 `local` 扫尾：业务文件/符号/路由/配置无过渡名
- [ ] T-16 保留表库内表/字段用途注释补齐；新 DDL 必须带 COMMENT ON
- [ ] T-17 现行表示统一为 LexHubPro；compose 卷迁移说明；指针文件改名

## 8. 自动化验证（按固定顺序执行）

| 顺序 | 命令 | 状态 | 结果摘要 |
|------|------|------|----------|
| ① | `bash scripts/verify.sh --docs-only` | ⬜ | |
| ② | 后端 `py_compile`（api/services/repositories/models 等） | ⬜ | |
| ③ | `cd app/backend && python -m pytest tests -q` | ⬜ | |
| ④ | `cd app/frontend && pnpm i && pnpm run lint` | ⬜ | |
| ⑤ | `cd app/frontend && pnpm run build` | ⬜ | |

- [ ] 测试不打真实 AI / 真实网络（MinIO 测试用 mock 或测试容器说明）
- [ ] 关键旅程：首页 → 自建登录 → 上传进 MinIO → 审查 → 报告详情（MinIO 预签名下载）→ 历史 → 登出回本站

## 9. 文档同步

- [ ] `spec.md`、`plan.md` 已获用户确认
- [ ] `test-report.md` 已用真实命令填写
- [ ] `.atoms/PROGRESS.md`、`.atoms/ATOMS.md`、`.atoms/ARCHITECTURE.md` 已同步
- [ ] 索引表状态在完成后改为「已完成」

## 10. 豁免项记录

| 编号 | 豁免内容 | 理由 | 确认人 |
|------|----------|------|--------|
| X-01 | 不在本迭代拆 `services/aihub.py` 与未改动的超行数 UI | spec 非目标 | 待确认时一并确认 |
| X-02 | 不强制删除 `lambda_handler.py`、`.mgx/config.yaml` | 解除禁改即可，避免无关 diff | 待确认时一并确认 |

> 状态图例：⬜ 未完成 / ✅ 已完成 / ⚠️ 有条件通过（须在豁免项说明）
