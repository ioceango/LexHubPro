# BUG-007 合同与审查报告的 user_id 类型不一致且无用户外键

## 1. 基本信息

| 项 | 内容 |
|----|------|
| 编号 | BUG-007 |
| 类型 | Bug |
| 严重级别 | 严重（数据完整性：归属列无法被数据库强制） |
| 提出人 | 用户 |
| 日期 | 2026-08-28 |
| 状态 | 已修复 |
| 确认 | ✅ 已确认（用户「开始实施」，2026-08-28） |

## 2. 复现步骤

1. 对照 `tb_user.id`、`tb_contract.user_id`、`tb_review_report.user_id` 的类型与外键。
2. 在本机 PostgreSQL 执行 `\d tb_contract`、`\d tb_review_report`、`\d tb_user`。

## 3. 实际表现

现场库（2026-08-28）实测：

| 表 | `user_id` 类型 | 指向 `tb_user.id` 的外键 |
|----|----------------|--------------------------|
| `tb_user` | `id` 为 `integer` PK | — |
| `tb_refresh_token` / `tb_one_time_token` / `tb_user_llm_*` | `integer` | 有，`ON DELETE CASCADE` |
| `tb_contract` | `varchar(64)` | **无** |
| `tb_review_report` | `varchar(64)` | **无**（仅有 `contract_id` → `tb_contract.id`） |

- 合同表 5 行、报告表 1 行，现有 `user_id` 值均为数字字符串 `"1"`，可转为整数。
- ER 文档已写明该偏差，但 ORM 与库内结构未改。

## 4. 期望表现

- `tb_contract.user_id`、`tb_review_report.user_id` 与 `tb_user.id` 同为整数。
- 两表均有指向 `tb_user(id)` 的外键；`tb_review_report.contract_id` 继续指向 `tb_contract(id)`。
- 基数：**一个用户多份合同**；**一份合同多轮审查、多份报告**（不把 `contract_id` 做成唯一）。
- 归属仍只从登录令牌写入，禁止信任请求体中的 `user_id`。
- **类型以模型层为准**：`tb_user.id` 为 integer，则进程内 `AuthUser.id`、`Owner.user_id`、仓储/服务入参、对外 JSON 的用户主键均为整数。JWT `sub` 仅在令牌序列化时写成字符串（RFC 7519 要求），解码后立刻还原为 int，禁止再在业务层来回 `str`/`int`。

## 5. 根因

合同/报告表沿用早期「令牌主体是字符串」的建模：`AuthUser.id` 与 JWT `sub` 为字符串，仓储 `Owner.user_id` 也是 `str`，ORM 用 `String(64)` 落库。认证表与 LLM 表后来按 `tb_user.id` 整型外键建模，两边没有对齐。

`create_all(checkfirst=True)` **不会**把已存在的 `varchar` 列改成 `integer`，所以启动自检也补不上外键。

定位：

- `app/backend/models/contract.py`：`user_id = Column(String(64), …)`，无 `ForeignKey`
- `app/backend/models/review_report.py`：同上；仅 `contract_id` 有外键
- `app/backend/repositories/contract.py`：`Owner.user_id: str`
- `app/backend/api/contracts.py`：`Owner(..., user_id=str(auth_user.id))`
- `docs/ddl/database-ddl-er.md` 已注明该不一致

应用层已经按「用户 1:N 合同、合同 1:N 报告」写入（每次审查 `create_report` 插入新行，没有 `UNIQUE(contract_id)`）。缺的是数据库类型与外键。

身份类型也分裂：JWT 解码已经把 `sub` 转成 `int` 回查 `tb_user`，随即又 `AuthUser(id=str(record.id))`；合同路径用 `str(auth_user.id)`，LLM 路径用 `int(auth_user.id)`。这是「上层迁就字符串令牌」而不是「上层对齐模型」。

## 6. 影响范围

- 表结构：`tb_contract.user_id`、`tb_review_report.user_id`（类型 + 外键）。
- 写入/查询路径：仓储 `Owner`、合同/报告/审查/LLM API；`AuthUser`、`UserResponse` / `UserProfile`。
- 启动建表：`services/schema_bootstrap.py` 必须能对存量表做 `ALTER`，不能只靠 `create_all`。
- 对象键路径仍是字符串路径片段（`default/1/202608/...`），调用处 `str(user_id)`，不改 MinIO 已有对象。
- 登录/资料 JSON 的 `user.id` 从字符串变为数字；前端 `AuthProfile.id` 改为 `number`。合同/报告列表本身不含 `user_id`。
- 删除用户时：与 LLM/令牌表一致，级联删除该用户合同；报告随合同 `ON DELETE CASCADE` 删除。对象存储文件不在本迭代清理。

## 7. 验收标准

- [x] AC-01：ORM 与 DDL 中 `tb_contract.user_id`、`tb_review_report.user_id` 为整数，且 `REFERENCES tb_user(id)`。
- [x] AC-02：`tb_review_report.contract_id` 仍 `REFERENCES tb_contract(id) ON DELETE CASCADE`；同一 `contract_id` 允许插入多份报告。
- [x] AC-03：现场/启动后库内列类型为 integer，外键存在；存量数字字符串 `"1"` 能迁成整数 `1`。
- [x] AC-04：查询与写入仍按令牌中的用户过滤；请求体即使带 `user_id` 也不被采用。
- [x] AC-05：回归用例注释 `# BUG-007 回归`：Owner 用整型 user_id；同一用户两份合同、同一合同两份报告均可插入；外键类型与 LLM 表一致。
- [x] AC-06：`docs/ddl/database-ddl-er.md` 的 ER 与 DDL 与实现一致。
- [x] AC-07：Playwright 截图 S01 起（登录后合同/历史相关页），证明改表后主路径可打开。
- [x] AC-08：进程内 `AuthUser.id`、`Owner.user_id` 为 `int`；签发 JWT 时 `sub = str(user.id)`，解码后 `int(sub)` 失败则令牌无效。业务层禁止再 `str(auth_user.id)` / `int(auth_user.id)` 成对转换（对象键等必须字符串的出口除外）。
- [x] AC-09：`UserResponse` / `UserProfile` 的 `id` 为 int；前端 `AuthProfile.id` 为 `number`。`/api/v1/auth/me` 返回数字 id。

## 8. 不做事项

- 不把 JWT 载荷里的 `sub` 改成 JSON 数字（违反 RFC 7519：`sub` 必须是字符串）。序列化边界写字符串，进程内仍是 int。
- 不改报告 JSON 子结构，不拆报告明细表。
- 不清理 MinIO 孤儿对象，不改删除用户的产品流程（无「删账号」入口则仅约束层就绪）。
- 不把 `tb_auth_audit.user_id` 纳入本迭代（可空、失败登录可无用户，语义不同）。

## 9. 待确认问题

| 编号 | 问题 | 建议 | 结论 |
|------|------|------|------|
| Q-01 | 用户删除时合同/报告是否级联删除 | 与 LLM/令牌表一致：`ON DELETE CASCADE` | 默认采纳，反对请说明 |

---

## 确认记录

| 日期 | 确认人 | 结论 | 备注 |
|------|--------|------|------|
| 2026-08-28 | 用户 | 确认 | 开始实施；进程内身份类型对齐 int |
