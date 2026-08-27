# 09 Git 提交与分支规范

> 目标：每一次提交、每一条工作分支都能对上一个已存在的 `FEAT-xxx` 或 `BUG-xxx` 编号目录，历史可检索、可回滚、不混线。
> 硬约束提炼见 `.agent/workflow.md` §7 与 `.agent/rules.md` §10。
> 仓库可以暂时没有 `.git`；**一旦存在 `.git`，本规范立即生效。**

## 1. 对齐编号目录（强制）

| 对象 | 必须含有 | 必须已存在 |
|------|----------|------------|
| 提交主题 | `FEAT-<3位>` 或 `BUG-<3位>` | `docs/features/FEAT-<3位>-*/` 或 `docs/bug-fix/BUG-<3位>-*/` |
| 工作分支名 | 同一编号 | 同上 |

**必须（always）**
- 先有编号目录（及已确认的 spec/plan，若改业务代码），再提交该迭代的代码或文档。
- 一次提交只对应 **一个** 编号。禁止把 `FEAT-008` 与 `BUG-007` 的改动打进同一次 commit。
- 一条工作分支只服务 **一个** 编号。做完合入 `main` 后删除分支；下一个编号新开分支。

**禁止（never）**
- 无编号提交、编号目录尚不存在就提交。
- 用 `chore` / `wip` / `update` 等无编号主题绕过目录制。
- 在 `main` 上直接堆多个未完成迭代。

一次性 `git init` 的空提交可以写 `chore(FEAT-012): initialize git repository`（或当时已存在的初始化编号），不得作为长期例外。

## 2. 提交说明

主题一行，格式：

```
<type>(<FEAT-NNN|BUG-NNN>): <不超过 50 字的说明>
```

| type | 何时用 |
|------|--------|
| `feat` | 该 FEAT 的功能实现 |
| `fix` | 该 BUG 的修复 |
| `docs` | 仅迭代文档 / 规约 |
| `test` | 仅测试与截图 |
| `refactor` | 该编号范围内、行为不变的整理 |

示例：

```
feat(FEAT-012): add git commit and branch rules
fix(BUG-007): unify contract report user_id as int fk
docs(FEAT-012): register git rules in docs README
```

正文（可选）写：编号目录路径、为何这样改、回滚注意。禁止把合同正文、密钥、prompt 全文写进 commit message。

## 3. 分支

| 项 | 规则 |
|----|------|
| 默认分支 | `main` |
| 需求分支 | `feat/FEAT-<3位>-<与目录相同的 slug>` |
| 缺陷分支 | `fix/BUG-<3位>-<与目录相同的 slug>` |
| 起点 | 从最新 `main` 拉出 |
| 合入 | 该编号验证通过后再合入 `main`，然后删远程与本地工作分支 |

禁止：`tmp`、`alex-wip`、`new-new` 这类无法对应目录的分支名；禁止一条分支连续做完 FEAT-012 再接着做 FEAT-013。

## 4. 回滚与历史保护

- 已推送、已合入 `main` 的改动：**用 `git revert` 回滚**，保留历史。按编号检索相关提交后逐条或一次 merge revert。
- **禁止**对 `main` 执行 `git push --force` / `--force-with-lease`（除非仓库负责人书面确认抢救损坏的默认分支）。
- **禁止**对已推送提交 `rebase -i`、`commit --amend` 后强推。未推送的本地提交可以 amend，但主题仍须带同一编号。
- 一次提交应是可独立 revert 的逻辑单元：不要把「改审查」和「顺便升级所有依赖」绑在一起。

## 5. 可追溯

从任意 commit 应能找到：

1. 主题中的 `FEAT-NNN` / `BUG-NNN`
2. 目录 `docs/features/…` 或 `docs/bug-fix/…`
3. 该目录的 `spec.md` / `test-report.md`

分支名与目录 slug 保持一致，避免 `feat/FEAT-012-foo` 对应目录却叫 `FEAT-012-bar`。

## 6. 禁止纳入版本库

与日志脱敏一致，**禁止提交**：

- `.env`、真实密钥、证书私钥
- 合同 PDF / 正文、prompt 全文、签名 URL
- `node_modules/`、`.venv/`、构建产物、日志、IDE 目录、本机 `.env`（以根 `.gitignore` 为准，已忽略的不得 `git add -f`）

误提交后不得只靠「再提交一版删除」了事：须按密钥轮换流程处理，并在对应 BUG 目录记录。

## 7. 与迭代流程的衔接

编码与验证仍走 [04 迭代流程](04-iteration-workflow.md)。Git 操作落在确认门之后：

```
spec/plan 已确认 → 编号分支上实现 → verify / Playwright → 带编号的 commit → 合入 main
```

无 `.git` 时：不把「尚未 git commit」当成交付失败。初始化仓库后的第一次提交必须挂到某个已存在编号。

## 8. 检查清单（提交前）

- [ ] 主题含 `FEAT-NNN` 或 `BUG-NNN`，且 `ls docs/features` / `ls docs/bug-fix` 能看到该目录
- [ ] 当前分支名含同一编号
- [ ] 暂存区没有第二个编号的业务改动
- [ ] 没有 `.env` / 密钥 / 合同文件
- [ ] 不需要 force-push `main`
