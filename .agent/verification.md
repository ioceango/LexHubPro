# .agent/verification.md — 验证命令、顺序与完成定义

> 本文件规定「何时算做完」。顺序不得调换，步骤不得跳过。

## 1. 验证顺序

```bash
# ⓿ 文档合规 gate（.agent 规约 + 工具指针 + 编号目录 + 索引登记）
bash scripts/verify.sh --docs-only

# ① 后端静态检查
cd app/backend && python -m py_compile api/*.py services/*.py repositories/*.py models/*.py dependencies/*.py utils/*.py auth_providers/*.py storage_providers/*.py

# ② 后端测试
cd app/backend && python -m pytest tests -q

# ③ 前端 Lint
cd app/frontend && pnpm i && pnpm run lint

# ④ 前端构建
cd app/frontend && pnpm run build

# ⑤ Playwright 端到端（每个 FEAT / BUG 强制；截图落到该迭代 test-report/）
cd app/frontend && HTTP_PROXY= HTTPS_PROXY= NO_PROXY='*' pnpm run e2e
```

一条命令跑完并生成报告骨架：

```bash
bash scripts/verify.sh FEAT-005-your-slug
```

规则：
- ⓿ 未通过时**禁止**进入任何代码验证步骤，也禁止宣称完成。
- 任一步失败必须修复后**从该步重跑**，不得跳过继续。
- 同一问题修复 3 次仍失败，停止并上报阻塞原因与已尝试方案。
- 模块解析类错误（`Could not resolve`、`Cannot find module`、`Module not found`）为硬门禁，必须清零。

## 2. 文档合规 gate 判定项

| 判定项 | 不合规表现 |
|--------|-----------|
| `.agent/` 规约齐全 | 必需文件（README / architecture / rules / constraints / workflow / verification / design）缺失或为空 |
| 工具指针有效 | `AGENTS.md`、`CLAUDE.md`、`.grok/rules/00-lexhubpro-rules.md` 缺失、为空、未指向 `.agent/`、或含红线条款拷贝 |
| 编号目录命名 | 不匹配 `FEAT-<3位>-<小写slug>` / `BUG-<3位>-<小写slug>` |
| 四文档齐全 | 缺少 spec / plan / checklist / test-report 任一份 |
| 文档非空 | 文件存在但内容为空 |
| 未完成标记 | 文档仍保留未完成占位标记 |
| 索引登记 | 编号目录未出现在对应索引表 |
| 编号唯一 | 同一编号出现多个目录 |
| 表 DDL/ER 目录 | `docs/ddl/database-ddl-er.md` 缺失、为空，或 `models/` 中某 `__tablename__` 未出现在该文件 |

全部问题项一次性汇总输出，便于一轮修完。

## 3. 测试要求

- 每个 Bug 修复至少一条回归用例，注释注明迭代编号。
- AI 调用一律 mock，禁止消耗真实额度。
- 覆盖正常路径、边界、异常分类与可重试性、脱敏断言。
- 报告只写真实执行过的结果；未执行项显式标注为未执行/后续补齐。

## 3.1 Playwright 端到端与编号截图（每个 FEAT / BUG 强制）

**适用范围**：`docs/features/FEAT-*` 与 `docs/bug-fix/BUG-*` 每一个新迭代，无例外。禁止用 curl、读代码、单张渲染图或「本环境无浏览器」代替。

**必须（always）**
1. 用 Playwright 跑与本迭代验收标准对应的端到端用例。优先 Playwright MCP；MCP 未挂载时用仓库内 `app/frontend` 的 Playwright CLI（`pnpm run e2e` 或 `node_modules/.bin/playwright test`）。
2. 截图落到**该迭代目录下的 `test-report/` 子目录**（与 `test-report.md` 同级，不是把 png 塞进 md 同名冲突）：

```
docs/features/FEAT-00X-<slug>/
├── spec.md
├── plan.md
├── checklist.md
├── test-report.md
└── test-report/
    ├── S01-<短slug>.png
    └── S02-<短slug>.png
```

Bug 迭代同理：`docs/bug-fix/BUG-00X-<slug>/test-report/`。

3. 文件名必须匹配 `S<2位序号>-<英文短slug>.png`，序号从 `S01` 起连续，例如 `S01-register-page.png`。
4. `test-report.md` 必须有「编号截图」表，**每一张**列出：编号、相对路径、覆盖的 AC、画面说明。报告正文用 `S01`、`S02` 引用，禁止只写「见附件」。
5. 截图必须覆盖本迭代的主路径与至少一条失败/边界路径；UI 变更还要覆盖相关页面，不能只拍一张静态页。

**禁止（never）**
- 跳过 Playwright 宣称 FEAT/BUG 完成。
- 把截图放到仓库根、`app/frontend/test-results/`、聊天附件而不归档到该迭代 `test-report/`。
- 文件名无编号、编号不连续、或报告未引用已有 png。
- 编造截图、用设计稿或未运行用例的屏幕顶替。

**豁免**：仅当本迭代零 UI（纯后端/纯文档）时，可在 `checklist.md` 豁免项写明理由并获用户确认；否则不得豁免。

## 4. 完成定义（DoD）

- [ ] 编号目录存在且命名合规，四份文档齐全且无未完成标记
- [ ] `spec.md`、`plan.md` 已获用户确认
- [ ] `checklist.md` 全部勾选（豁免项写明理由并获确认）
- [ ] 对应索引表已登记本迭代并更新状态
- [ ] `bash scripts/verify.sh --docs-only` 通过
- [ ] 后端 `py_compile` + `pytest` 通过
- [ ] 前端 `pnpm run lint` + `pnpm run build` 通过
- [ ] Playwright 端到端通过，截图已落入 `test-report/` 且在 `test-report.md` 按编号引用
- [ ] `test-report.md` 附真实命令输出摘要，结论为通过或有条件通过
- [ ] 新增/变更配置已写入 `.env.example`
- [ ] `.atoms/PROGRESS.md`、`.atoms/ATOMS.md` 已更新；架构有变化时 `.atoms/ARCHITECTURE.md` 与 `.agent/architecture.md` 同步更新

以上任一项未达成，不得宣称完成。