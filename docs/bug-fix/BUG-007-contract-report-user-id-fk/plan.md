# Plan：BUG-007 统一合同/报告 user_id 为整型外键

## 基本信息

| 项 | 内容 |
|----|------|
| 迭代号 | BUG-007-contract-report-user-id-fk |
| 对应 Spec | `./spec.md` |
| 预估工作量 | 0.5–1 人时 |
| 确认状态 | ✅ 已确认 |

## 1. 方案概述

把 `tb_contract.user_id`、`tb_review_report.user_id` 改成与 `tb_user.id` 相同的 `Integer`，并加 `ForeignKey("tb_user.id", ondelete="CASCADE")`。报告继续外键到合同，**不加** `UNIQUE(contract_id)`，以保留多轮审查。

存量表 `create_all` 不会改列类型，因此在 `schema_bootstrap` 增加幂等 `ALTER COLUMN ... TYPE integer USING user_id::integer`，再 `ADD CONSTRAINT` 外键。

**类型以 `tb_user.id: int` 为单一事实**：`AuthUser.id`、`Owner.user_id`、仓储/服务、Pydantic 用户视图均为 `int`。JWT 只在签发时 `sub = str(user.id)`，解码时 `int(sub)` 后不再当字符串用。对象键等路径片段在出口 `str(user_id)`。

### 备选方案对比

| 方案 | 优点 | 缺点 | 是否采用 |
|------|------|------|----------|
| A：两表 user_id → integer FK；进程内身份类型全部 int；JWT sub 仅序列化成字符串 | 与模型一致；消灭 str/int 双路径 | `/me` 的 id 从 JSON 字符串变为数字 | ✅ |
| B：只改库表，AuthUser.id 仍为 str，边界处 int() | 改动面小 | 上层继续迁就令牌字符串，LLM 与合同各转一次 | ❌ 已否决 |
| C：报告去掉 user_id，只经合同关联用户 | 少一列 | 列表过滤必须 join | ❌ |

## 2. 架构与分层落点

| 层 | 文件 | 改动 | 职责 |
|----|------|------|------|
| models | `app/backend/models/contract.py` | 修改 | `user_id` Integer + FK |
| models | `app/backend/models/review_report.py` | 修改 | `user_id` Integer + FK；保留 contract_id FK |
| auth | `app/backend/auth_providers/base.py`、`jwt_provider.py` | 修改 | `AuthUser.id: int`；decode 后保持 int |
| schemas | `app/backend/schemas/auth.py` | 修改 | `UserResponse.id` / `UserProfile.id` 为 int |
| repositories | `app/backend/repositories/contract.py` | 修改 | `Owner.user_id: int` |
| api | `contracts.py` / `reports.py` / `contract_review.py` / `user_llm.py` / `storage.py` / `auth.py` | 修改 | `Owner(user_id=auth_user.id)`，去掉 `str`/`int` 互转；对象键出口 `str(auth_user.id)` |
| tokens | `app/backend/utils/auth_tokens.py` | 保持 | `sub: str(user.id)` 仅此处字符串化 |
| services | `app/backend/services/schema_bootstrap.py` | 修改 | 存量表 varchar→int + 补 FK |
| frontend | `app/frontend/src/lib/auth-provider.ts` 及引用 `AuthProfile.id` 处 | 修改 | `id: number` |
| tests | `app/backend/tests/test_contracts.py` 等 | 修改 | Owner / AuthUser 用 int；`# BUG-007 回归` |
| docs | `docs/ddl/database-ddl-er.md` | 修改 | ER + DDL + 变更记录 |
| e2e | `app/frontend/e2e/` | 新增或改 | 登录后合同/历史页截图 |

对象键 `build_object_key(..., user_id: str)` 签名可保留（路径片段只能是字符串），调用处传入 `str(auth_user.id)`。

### 禁改自查

- 不合并 schemas 与 models；表变更同步 DDL 目录
- 不改 `index.html`、`.mgx/config.yaml`、`AuthCallback.tsx`

## 3. 接口契约

合同/报告响应仍不含 `user_id`。审查仍每次插入新报告。

登录 / `/me` / 用户资料的 `id`：**JSON number**（原先为 JSON string `"1"`）。这是与模型对齐的契约修正，不是事故。前端 `AuthProfile.id` 同步为 `number`。

JWT 载荷：`{"sub": "1", ...}` 仍为字符串 claim（RFC）。

## 4. 数据库变更

| 表 | 变更 | 注释 | 兼容 | 回滚 |
|----|------|------|------|------|
| `tb_contract` | `user_id` varchar(64) → integer；`FOREIGN KEY (user_id) REFERENCES tb_user(id) ON DELETE CASCADE` | 归属用户主键，由令牌写入 | 存量数字字符串可 USING 转换 | 再改为 varchar（不推荐） |
| `tb_review_report` | 同上；保留 `contract_id` FK | 同上 | 同上 | 同上 |

存量迁移（bootstrap，幂等）：

1. 若列已是 integer 且外键已存在则跳过。
2. 若存在非纯数字 `user_id`，启动失败并记条数（不记合同正文）。
3. 若转换后的 id 在 `tb_user` 中不存在，启动失败（避免加 FK 炸掉）。本机现状：全部为 `"1"` 且用户存在。
4. `ALTER COLUMN user_id TYPE integer USING user_id::integer`。
5. `ADD CONSTRAINT ... FOREIGN KEY (user_id) REFERENCES tb_user(id) ON DELETE CASCADE`（IF NOT EXISTS 语义用查 `pg_constraint`）。

SQLite 内存测：新库 `create_all` 直接建 integer+FK；部分用例只建合同表时 SQLite 默认不强制 FK，Owner 改为 int 即可。

## 5. 实施顺序

1. 改 ORM 两列类型与 FK。
2. `AuthUser.id` / `Owner.user_id` / 用户 schema 改为 int；签发仍 `str`、解码仍 `int`。
3. 去掉 API 层成对的 `str(auth_user.id)` / `int(auth_user.id)`。
4. 写 bootstrap ALTER。
5. 前端 `AuthProfile.id` 改为 number。
6. 更新 DDL/ER。
7. 回归测试 + Playwright。
8. 重启 backend 使 bootstrap 落到现场库。

## 6. 风险与回滚

- 风险：非数字存量或孤儿 user_id 会阻断启动。缓解：先查询再 ALTER；本机已核实无此类行。
- 回滚：恢复 ORM 为 String 不能自动把 integer 改回；若必须回滚需手写 ALTER。本变更方向正确，以修 bootstrap 为主。
