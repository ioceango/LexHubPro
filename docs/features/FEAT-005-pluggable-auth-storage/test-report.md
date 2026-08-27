# 测试验证报告：FEAT-005（A 段 规划阶段）

## 1. 报告信息

| 项 | 内容 |
|----|------|
| 迭代编号 | FEAT-005 |
| 报告阶段 | A 段：规划阶段 |
| 执行日期 | 2026-08-26 |
| 本轮范围 | 仅产出需求分析与规划文档，不改动任何业务代码 |
| 结论 | A 段通过（B 段编码尚未开始） |

## 2. 本轮实际执行的验证

| 步骤 | 命令 | 退出码 | 结果 |
|------|------|--------|------|
| 文档合规门禁 | `bash scripts/verify.sh --docs-only` | 0 | 通过 |

本轮只在四份文档与索引登记完成后执行了一次门禁，未构造补齐前的失败基线（该反向能力已在 FEAT-004 报告中实测过，此处不重复声明）。具体输出见 §3。

## 3. 关键输出摘要

```
==== ⓿ 文档合规 gate ====
  跨工具规约(.agent)：6/6 份文件就绪
  工具入口指针：3/3 份有效并指向 .agent/
  需求(FEAT)：发现 5 个编号目录
  缺陷(BUG)：发现 2 个编号目录
.agent 规约齐全、工具指针有效、编号目录命名与四文档齐全性、非占位与索引登记全部通过
✓ ⓿ 文档合规 gate 通过

仅执行文档合规 gate（--docs-only），跳过代码验证步骤

==== 验证汇总 ====
  ✓ ⓿ 文档合规 gate 退出码 0

结论：通过
DOCS_EXIT=0
```

判定要点：需求编号目录数由 4 增至 5，说明 FEAT-005 目录已被识别；四文档齐全性、非占位内容与索引登记三项校验均通过。

## 4. 本轮未执行的验证（如实声明）

本轮为规划阶段，以下验证**均未执行**，不得以预期值代替实测：

- 后端 `python -m py_compile`（本轮未新增或修改任何 Python 文件）
- 后端 `python -m pytest tests`（本轮未新增或修改任何用例）
- 前端 `pnpm run lint` / `pnpm run build`（本轮未改动任何前端文件）
- 认证双模式切换的任何功能验证
- 自建注册、登录、令牌轮换、锁定、重置密码等任何功能验证
- MinIO 上传、预签名 URL、删除等任何功能验证
- `docker compose config` 或容器启动验证
- `.agent/` 规约中立化后的关键词残留检索

上述验证归属 B 段，将在用户确认 spec 与 plan 并完成编码后，按 `plan.md` 各阶段的验证方式逐项执行，并在本报告追加 B 段结果。

## 5. A 段验收标准对照

| 编号 | 标准 | 结果 |
|------|------|------|
| AC-17 | 本轮文档四份齐全、已登记索引、文档门禁通过 | 通过（见 §2） |
| AC-18 | 本轮未改动任何业务代码 | 通过（改动仅限本迭代文档目录、需求索引与进度记录） |

其余 AC-01 至 AC-16 为设计与实现类标准，其中设计完备性已在 `checklist.md` A2 / A3 段逐项自查勾选，实现验证归属 B 段，本轮不作结论。

## 6. 本轮改动文件清单（用于确认非侵入性）

| 类型 | 路径 |
|------|------|
| 新增 | `docs/features/FEAT-005-pluggable-auth-storage/spec.md` |
| 新增 | `docs/features/FEAT-005-pluggable-auth-storage/plan.md` |
| 新增 | `docs/features/FEAT-005-pluggable-auth-storage/checklist.md` |
| 新增 | `docs/features/FEAT-005-pluggable-auth-storage/test-report.md` |
| 修改 | `docs/features/README.md`（登记本迭代并更新下一个可用编号） |
| 修改 | `.atoms/PROGRESS.md`（记录本轮规划产出） |

`app/**` 下无任何文件改动。

## 7. 待用户决策事项（阻塞 B 段开始）

1. **平台模式与自建用户表的冲突**（详见 `spec.md` §10 R-1）：平台形态明确禁止自建用户表与禁改 `models/**`。若无指示，我将按「代码交付 + 平台形态由启动自检禁用 local + 自托管生效」执行，自建认证仅在自托管形态端到端可用。
2. **自托管缺 AI 网关**（R-3）：本迭代不解决，自托管形态可跑通登录与上传，但审查会失败，需单独迭代补齐。是否接受此边界。
3. **刷新令牌存储方式**（R-5）：倾向访问令牌存内存 + 刷新令牌 `HttpOnly` Cookie + CSRF 双提交；若前后端跨域部署需强制 HTTPS。
4. **邮件服务选型**：本轮未引入任何密钥，开发期用 console 打印。B 段开始前需确认选型。

## 8. 最终结论

**A 段通过**：需求分析与规划文档已完整产出并通过文档合规门禁，本轮未触碰任何业务代码。B 段编码在用户确认 spec、plan 及 §7 决策事项后方可开始。

---

# 测试验证报告：FEAT-005（B 段 续作）

## 1. 报告信息

| 项 | 内容 |
|----|------|
| 迭代编号 | FEAT-005 |
| 报告阶段 | B 段：编码与验证 |
| 执行日期 | 2026-08-27 |
| 本轮范围 | 规约允许 local 自建登录；补齐前端认证、存储接入、管理端、测试 |
| 结论 | 有条件通过（自动化门禁通过；平台预览四条链路未做；`pnpm i` 被环境策略拦截） |

## 2. 本轮实际执行的验证

| 步骤 | 命令 | 退出码 | 结果 |
|------|------|--------|------|
| 文档合规门禁 | `bash scripts/verify.sh --docs-only` | 0 | 通过 |
| 后端编译 | `.venv/bin/python -m py_compile app/backend/routers/*.py services/*.py ...` | 0 | 通过 |
| 后端测试 | `cd app/backend && ../../.venv/bin/python -m pytest tests -q` | 0 | **37 passed** |
| 启动探针 | `python scripts/feat005_runtime_probe.py` | 0 | `PROBE_RESULT PASS`（C1–C5） |
| compose 语法 | `LOCAL_AUTH_SECRET_KEY=... JWT_SECRET_KEY=... docker compose config` | 0 | 通过 |
| 前端 Lint | `./node_modules/.bin/eslint --quiet ./src` | 0 | 通过 |
| 前端构建 | `./node_modules/.bin/vite build` | 0 | 通过（预渲染 `/` 与 `/blog/`） |

## 3. 关键输出摘要

pytest：

```
37 passed, 5 warnings in 6.79s
```

探针：

```
PROBE_RESULT PASS
```

文档门禁：

```
✓ ⓿ 文档合规 gate 通过
结论：通过
```

Vite：

```
✓ built in 7.16s
Prerendered 2 pages:
  /
  /blog/
```

## 4. 本轮未执行 / 失败但已说明

- **`pnpm i` 未作为门禁入口成功执行**：corepack pnpm 11.7 的 `minimumReleaseAge` 策略拒绝 lockfile 中 4 个条目（`@tanstack/react-query@5.102.4` 等）。依赖实际已在 `node_modules`，改用本地 eslint/vite 二进制完成 lint/build。`bash scripts/verify.sh FEAT-005-pluggable-auth-storage` 全量脚本因此未跑通第 ③ 步。
- **未执行** `docker compose up`，未启动真实 MinIO/Postgres 容器。
- **未执行** 平台预览环境登录/上传/审查/历史四条链路人工确认。
- **未执行** 浏览器端到端（本环境无浏览器自动化接到开发服务器）。

## 5. 验收标准对照（B 段）

| 编号 | 标准 | 结果 |
|------|------|------|
| AC-01 ~ AC-04 | 认证/存储抽象 + object_key 一致性 + 不持久化签名 URL | 通过（代码 + 单测） |
| AC-05 | 自建用户 11 项能力 | 通过（后端已落地；前端登录注册重置资料页已接通） |
| AC-08 ~ AC-10 | Argon2id、刷新轮换、防枚举与日志脱敏 | 通过（`tests/test_local_auth.py`） |
| AC-11 | 前端统一封装与三态 | 通过（代码审查；无浏览器实测） |
| AC-12 ~ AC-14 | compose MinIO、配置、启动自检 | 通过（compose config + 探针；未实际 up） |
| AC-15 | `.agent/` 完全清除平台条款 | **有意未做全清**：按用户指示改为「允许 local 自建」，禁改清单保留 |
| AC-17 | 四文档 + 索引 + 文档门禁 | 通过 |

## 6. 本轮改动要点

- 规约：`.agent/constraints.md` 等改为 `AUTH_MODE` 二选一，明确 local 自建登录合法。
- 后端：JWT 密钥对齐、`MINIO_PUBLIC_ENDPOINT`、`/api/v1/auth/mode`、`/api/v1/local-storage`、管理端、刷新 Cookie。
- 前端：`auth-provider` / `http` / `storage-access` + 登录注册等页面与路由同批次。
- 测试：新增 auth / local_data / storage 用例，原 18 条审查回归仍绿。

## 7. 最终结论

**有条件通过**。自建登录已在规约中合法，后端与前端双模式封装已落地，自动化测试 37 passed。完整自托管 `compose up` 与平台预览回归仍待运行环境补齐。