# 需求规格说明：FEAT-006 后端四层与表命名规约

> 2026-08-27 用户提出并确认：为 Grok build 与 DSH 补充数据库设计与分层规约；废止禁止修改 models。

## 1. 背景与问题

现规约把 `app/backend/models/**` 列为禁改，ORM 无法随需求迭代。为绕开该禁令，自建认证把表放到 `local_auth/` 等旁路目录，四层（模型 / 仓储 / 服务 / HTTP）被拆散，Grok build 与 DSH 无法按统一分层改库、改接口。

表命名缺少 `tb_` 前缀，也没有强制的表用途注释与字段意义注释，读库无法判断表和列干什么。

## 2. 目标

1. 后端强制四层：`models`、`repositories`、`services`、`api`，调用单向。
2. 废止「禁止修改 models」及同类堵死分层迭代的条款。
3. 表命名 `tb_<业务>`，表必须有用途注释，字段必须有意义注释。
4. 规约写进 `.agent/`（Grok / DSH / 所有工具同一事实源），并在架构文档里写死。
5. **本迭代完成存量重构与迁移**（原 §3 非目标升格为本期目标）：
   - 存量表全部改为 `tb_*`（含启动时对旧表名的幂等 RENAME）。
   - 全部 HTTP 模块从 `routers/` 迁入 `api/`。
   - `local_auth/`、`local_data/` 整包收回四层后删除旁路包。

## 3. 非目标

- 不把平台 OIDC 用户表与自建邮箱用户表合成一张（主键类型不同：平台 `sub` 字符串 vs 自增整型）。
- 不改前端页面结构与视觉规范。
- 不解决自托管 AI 网关。

## 4. 用户故事

1. 作为 Grok build / DSH 使用者，我改表结构时可以直接改 `models/`，并补仓储与 API，不必绕开禁改。
2. 作为读库的人，我看到 `tb_contract` 和列注释就知道这张表、这个字段干什么。
3. 作为评审者，我能按四层目录判断改动有没有越层。

## 5. 功能需求

| 编号 | 需求 |
|------|------|
| FR-1 | `.agent/architecture.md` 增加后端四层铁律；目录、职责、禁止项可判定 |
| FR-2 | `.agent/rules.md` 分层表改为 api / services / repositories / models |
| FR-3 | `.agent/constraints.md` 从禁改清单删除 `models/**`；删除「禁止把用户表写入 models」 |
| FR-4 | `main.py` 增加扫描 `api` 包，且规约允许为此修改路由发现 |
| FR-5 | 07 规范：表名 `tb_<业务>`；表 comment；字段 comment 强制 |
| FR-6 | Grok 指针 `.grok/rules/00-legalguard-rules.md` 与 DSH 入口 `AGENTS.md` 红线摘要同步 |
| FR-7 | 存量表 RENAME 为 `tb_*`，并为每张表、每个字段补 comment |
| FR-8 | `routers/` 业务模块全部迁入 `api/`，`main.py` 以 `api` 为 HTTP 发现入口 |
| FR-9 | `local_auth/`、`local_data/` 的模型进 `models/`、仓储进 `repositories/`、引导进 `services/`，然后删除旁路包 |

## 6. 验收标准

| 编号 | 标准 |
|------|------|
| AC-01 | `.agent/` 中不再出现「禁止修改 models」或「models 平台托管禁改」作为现行条款 |
| AC-02 | 架构文档写明四层目录、单向调用、新表 `tb_*`、表/字段必须有 comment |
| AC-03 | 指针摘要（AGENTS.md / CLAUDE.md / grok rules）与 `.agent/` 一致 |
| AC-04 | `docs/rules/01`、`06`、`07` 与 `.agent/` 无相互矛盾 |
| AC-05 | `app/backend/api/` 与 `repositories/` 包存在；`main.py` 扫描 `api` |
| AC-06 | `bash scripts/verify.sh --docs-only` 通过 |
| AC-07 | 代码中新表名均为 `tb_*`；启动可将旧表名幂等重命名 |
| AC-08 | `app/backend/routers/` 不再承载业务路由模块 |
| AC-09 | 仓库中不再存在作为长期分层的 `local_auth/`、`local_data/` 包 |
| AC-10 | 既有 pytest 回归通过 |

## 7. 影响面

规约、四层目录、存量表名、HTTP 包路径、启动建表/重命名。运行中的 compose 库会在后端重启时 RENAME 旧表。
