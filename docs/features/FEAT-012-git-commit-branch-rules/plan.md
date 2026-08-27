# Plan：FEAT-012 Git 提交与分支规范

## 基本信息

| 项 | 内容 |
|----|------|
| 迭代号 | FEAT-012-git-commit-branch-rules |
| 对应 Spec | `./spec.md` |
| 预估工作量 | 0.5 人时 |
| 确认状态 | ✅ 已确认 |

## 1. 方案概述

新增 `docs/rules/09-git-commit-and-branch.md` 作为细则。硬约束写入 `.agent/workflow.md`（提交发生在确认门与验证之后，属于流程）。`docs/README.md` 索引 + `04-iteration-workflow.md` 增加「归档时按编号提交」的步骤。不改业务代码，不 `git init`。

提交主题约定（实施时写入 09）：

```
<type>(<FEAT-NNN|BUG-NNN>): <50 字内说明>
```

`type` 取 `feat` / `fix` / `docs` / `test` / `refactor`，但括号内编号必须与本次迭代目录一致。

分支：`feat/FEAT-012-git-commit-branch-rules`、`fix/BUG-007-contract-report-user-id-fk`。从 `main` 拉出，合并回 `main` 后删分支。

### 备选方案对比

| 方案 | 优点 | 缺点 | 是否采用 |
|------|------|------|----------|
| A：09 细则 + `.agent/workflow` 硬约束 | 与三层规约一致；工具会读 | 无 git 时不能用 hook 强制 | ✅ |
| B：只写 docs/rules，不改 `.agent` | 少改 | 工具可能不读细则就乱提交 | ❌ |
| C：本迭代加 hook + git init | 强制力强 | 仓库现状无 `.git`；越出「先立规」范围 | ❌ |

## 2. 架构与分层落点

| 层 | 文件 | 改动 | 职责 |
|----|------|------|------|
| 细则 | `docs/rules/09-git-commit-and-branch.md` | 新增 | 提交格式、分支、回滚、追溯、禁止项 |
| 索引 | `docs/README.md` | 修改 | 收录 09 |
| 流程 | `docs/rules/04-iteration-workflow.md` | 修改 | 验证后按编号提交/合入 |
| 硬约束 | `.agent/workflow.md` | 修改 | 工具提交必须带本迭代编号 |
| 硬约束 | `.agent/rules.md`（短节） | 修改 | 可判定条款：无编号不得提交 |

### 禁改自查

- 不改业务代码与表
- 不 `git init`、不提交密钥

## 3. 接口契约

无 HTTP 接口。

## 4. 数据库变更

无。

## 5. 规范要点（写入 09 的提纲）

1. **对齐编号**：commit 与 branch 必须出现已存在的 `FEAT-NNN` 或 `BUG-NNN`。
2. **单迭代单分支**：禁止一条分支连续做多个编号；禁止一次 commit 包含两个编号的文件集（文档目录混入除外：本迭代自己的四份文档）。
3. **可回滚**：已推送用 revert；禁止 `push --force` 到 `main`；禁止 `rebase -i` 改写已共享提交。
4. **可追溯**：主题含编号；正文可写目录路径；不要把无关格式化/依赖升级塞进功能提交。
5. **主分支**：日常工作在编号分支；`main` 只接收完整迭代（spec 已确认且验证过的合入）。
6. **禁止提交**：`.env`、密钥、合同 PDF、签名 URL、`node_modules`、`.venv`。
7. **无仓库**：没有 `.git` 不算违反「未提交」；有 `.git` 后首次提交也必须挂到某个编号（本 FEAT-012 或专门的初始化 FEAT）。

## 6. 实施顺序

1. 写 `docs/rules/09-git-commit-and-branch.md`。
2. 更新 `docs/README.md`、`04-iteration-workflow.md`。
3. 更新 `.agent/workflow.md`、`.agent/rules.md`。
4. docs-only + Playwright。

## 7. 风险与回滚

- 风险：无 `.git` 时无法用 hook 证明提交格式。缓解：AC-06 明确；规范先行。
- 回滚：删除 09 并还原索引与 `.agent` 增补。
