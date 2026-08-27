# 测试验证报告：FEAT-007 清除平台认证与硬约束，统一为自建登录与自托管架构

## 1. 报告信息

| 项 | 内容 |
|----|------|
| 迭代号 | FEAT-007-self-hosted-only |
| 关联文档 | `./spec.md`、`./plan.md`、`./checklist.md` |
| 执行人 | Grok |
| 执行日期 | 2026-08-27 |
| 被测版本 | 工作区未提交实现 |
| 结论 | ⚠️ 有条件通过 |

## 2. 环境信息

| 项 | 值 |
|----|-----|
| 前端 | React 18 + TypeScript + Vite |
| 后端 | FastAPI + SQLAlchemy Async + PostgreSQL |
| 运行环境 | 本机静态检查与单元测试；compose 端到端未重跑 |
| Python | 3.11（pytest 现场） |
| Node | 已有 node_modules；宿主 pnpm 11 因 minimumReleaseAge 无法 install |

## 3. 自动化执行结果

| 顺序 | 步骤 | 命令 | 退出码 | 结果 | 耗时 |
|------|------|------|--------|------|------|
| ⓿ | 文档合规 | `bash scripts/verify.sh --docs-only` | 0 | ✅ | |
| ① | 后端静态检查 | `python -m py_compile api/*.py services/*.py repositories/*.py models/*.py ...` | 0 | ✅ | |
| ② | 后端测试 | `cd app/backend && python -m pytest tests -q` | 0 | ✅ 37 passed | ~3.5s |
| ③ | 前端 Lint | `./node_modules/.bin/eslint --quiet ./src` | 0 | ✅ | |
| ④ | 前端构建 | `./node_modules/.bin/vite build` | 0 | ✅ | ~6.7s |
| — | `pnpm i` | 宿主 corepack pnpm 11 | 1 | 未执行完整安装 | hono@4.13.5 minimumReleaseAge |

### 关键输出摘要

```text
docs-only: .agent 7/7 份文件就绪；指针 3/3 有效；结论：通过
pytest: 37 passed, 5 warnings in 3.47s
eslint: quiet, exit 0
vite build: 1836 modules, built in 6.67s
```

## 4. 测试用例统计

| 层级 | 总数 | 通过 | 失败 | 跳过 | 覆盖率 |
|------|------|------|------|------|--------|
| 单元/集成（pytest） | 37 | 37 | 0 | 0 | 未测覆盖率 |
| 合计 | 37 | 37 | 0 | 0 | |

## 5. 验收标准逐条对照

| 编号 | 验收标准 | 验证方式 | 实际结果 | 结论 |
|------|----------|----------|----------|------|
| AC-01 | 规约清除平台硬约束 | 阅读 `.agent/constraints.md` | 已改为 JWT+MinIO，无 OIDC/web-sdk 义务 | ✅ |
| AC-02 | design.md 与门禁 | 文件存在，verify.sh 含 design.md | 7/7 通过 | ✅ |
| AC-03 | 无平台认证实现 | 代码检索 | 已删 OIDC 路由/模型/AuthCallback | ✅ |
| AC-04 | `/api/v1/auth` | 代码 | prefix 已改；端到端登录未在本报告重跑 compose | ⚠️ |
| AC-05 | contracts/reports | 代码 | 正式路径已落地 | ✅ |
| AC-06 | 无平台 OSS | 代码 | 已删 PlatformStorageProvider 与脚手架 storage 管理台 | ✅ |
| AC-07 | 无 web-sdk | package.json + vite + src | 依赖已移除，源码无 import；lockfile 仍列出旧包 | ⚠️ |
| AC-08 | 无 platform 配置开关 | compose/.env.example | AUTH_MODE/STORAGE_MODE 已从 compose 去掉 | ✅ |
| AC-09 | 无 OIDC 表读写 | models/schema_bootstrap | 不再 create_all OIDC 表 | ✅ |
| AC-10 | 审查后端落库 | 代码 | analyze 写报告；无集成测打真实 AI | ⚠️ |
| AC-11 | 管理端同一登录态 | ProtectedAdminRoute | 改用 hooks/use-auth | ✅ |
| AC-12 | 细则与 verify.sh | docs-only + verification.md | 编译目标含 api/ | ✅ |
| AC-13 | 回归 | pytest + eslint + vite | 通过；compose 登录未执行 | ⚠️ |
| AC-14 | 文件只走 MinIO | 代码 | storage-access 只打 /api/v1/storage | ✅ |
| AC-15 | 规约唯一 MinIO | architecture/08 | 已写 | ✅ |
| AC-16 | 无 local_ 业务文件 | ls api/ | 无 local_*.py | ✅ |
| AC-17 | COMMENT ON | schema_bootstrap._apply_comments | 启动时幂等写入；库内未用 psql 现场核对 | ⚠️ |
| AC-18 | LexHubPro 品牌 | UI/compose | 页头与容器名已改；CDN logo 文件名仍含 legalguard | ⚠️ |

## 6. 异常场景验证

| 编号 | 场景 | 期望 | 实际 | 结论 |
|------|------|------|------|------|
| E-01～E-04 | 鉴权与越权 | 401/404 | pytest test_contracts / test_auth 覆盖部分 | ⚠️ 部分 |
| E-05 | MinIO | 启动失败 | 未打真实 MinIO | 未执行 |
| E-06 | AI 失败 | 分类状态码 | 既有 test_contract_review | ✅ 抽取/分类 |
| E-08 | 旧 /local-* | 404 | 未起服务探测 | 未执行 |

## 7. 关键旅程走查

| 旅程 | 步骤 | 结果 | 备注 |
|------|------|------|------|
| 主链路 | 登录 → 上传 MinIO → 审查 → 报告 | 未执行 | compose 未在本轮重启 |
| 认证 | 登出回本站 | 未执行 | |

## 8. 缺陷清单

| 编号 | 描述 | 严重级别 | 状态 |
|------|------|----------|------|
| D-01 | 宿主 `pnpm i` 因 minimumReleaseAge（hono@4.13.5）失败 | 一般 | 遗留：用已有 node_modules 完成 lint/build |
| D-02 | pnpm-lock 仍含 web-sdk 条目（未重新生成锁文件） | 一般 | 遗留 |
| D-03 | 存量 Docker 卷仍可能叫 legalguard_* | 一般 | 需运维改名 |

## 9. 规范符合性核对

- [x] 分层与注释条款已写入规约
- [x] 测试报告只写真实命令
- [ ] compose 全链路人工走查未做
- [ ] 库内 pg_description 未用 psql 核对

## 10. 遗留风险与建议

| 编号 | 遗留项 | 影响 | 建议处理时机 |
|------|--------|------|--------------|
| R-01 | 未重启 compose 验证登录 | 运行时配置（JWT_SECRET_KEY）需与旧 LOCAL_AUTH 对齐 | 部署时把 `.env` 的 LOCAL_AUTH_SECRET_KEY 复制为 JWT_SECRET_KEY |
| R-02 | AI 网关仍需外部凭据 | 无凭据时审查失败 | 后续 |
| R-03 | 锁文件未刷新 | 镜像构建 `pnpm install` 可能仍装到 web-sdk | 能跑 pnpm i 时刷新 lock |

## 11. 结论

**有条件通过。** 规约、后端单元测试、前端 eslint 与 vite build 已真实执行并通过。未执行 compose 端到端登录/上传，未 psql 核对 COMMENT ON。宿主 pnpm install 被 minimumReleaseAge 挡住。
