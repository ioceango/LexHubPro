# 实现方案：FEAT-004 跨工具统一 `.agent/` 规约

## 1. 技术方案

### 1.1 为什么用 `.agent/` 目录而不是继续堆 `AGENTS.md`

| 方案 | 取舍 |
|------|------|
| 继续把规则全写在根 `AGENTS.md` | 单文件持续膨胀；Codex 有 32 KiB 指令上限；与 `docs/rules/` 重复度高；新增工具时规则仍寄生在某个工具入口 |
| 每个工具各写一份完整规则 | 必然漂移，维护成本随工具数量线性增长（已在 FEAT-003 明确否决） |
| **`.agent/` 独立规约目录 + 各工具入口做指针**（采用） | 规约与工具解耦；单点维护；根入口体积小、加载稳定；新增工具只需加一个指针 |

### 1.2 为什么不为 dsh 新建专有入口

联网核实结论：
- `AGENTS.md` 是跨工具开放约定，已被 Codex、Cursor、Jules、Copilot、Aider、Gemini CLI、Windsurf 等广泛读取；Codex 自项目根向工作目录逐层合并，深层覆盖浅层，并支持同目录 `AGENTS.override.md` 优先。
- DeepSeek harness (dsh) 侧**未见**官方公开的仓库指令文件约定。

因此采用「通用根 `AGENTS.md` 兜底 + 在 `.agent/README.md` 记录入口映射」的方式，不新建 `.dsh/` 等臆造结构。后续若 dsh 公布官方约定，只需新增一份指向 `.agent/` 的指针文件，规约正文零改动。

### 1.3 内容重组原则

不做原文搬运，按「指令强度」改写：
- `.atoms/` 的陈述句（「本项目采用 X」）改为约束句（「必须用 X，禁止 Y，校验方式 Z」）。
- 按提问维度拆分文件，让工具读一份就能回答一个问题：何时能改（workflow）、不能做什么（constraints）、怎么写（rules）、改哪里（architecture）、何时算完（verification）。
- 细则全文仍留在 `docs/rules/`，`.agent/` 只做可判定的强约束与索引，避免三处重复。

### 1.4 门禁扩展设计

在 `scripts/verify.sh` 的 `run_docs_gate` 中新增两组检查，复用现有 `add_issue` 汇总机制与非零退出逻辑：

```
check_agent_spec()      # .agent/ 六份必需文件：存在 + 非空
check_tool_pointers()   # 三份指针：存在 + 非空 + 内容包含 .agent/ 引用
```

- 复用现有问题汇总模式：所有问题一次性输出，便于一轮修完。
- 指针指向性校验用固定字符串匹配 `.agent/`，判定明确、不易误报。
- 不引入新外部依赖，保持脚本只读不改源码、不执行版本控制操作、不访问网络。

## 2. 涉及文件清单

**新增**
- `.agent/README.md` — 单一事实源声明 + 工具入口映射 + 与 `.atoms/` 关系
- `.agent/workflow.md` — 流程与确认门
- `.agent/constraints.md` — 禁改与红线
- `.agent/rules.md` — 工程规范
- `.agent/architecture.md` — 架构与模块
- `.agent/verification.md` — 验证与 DoD
- `docs/features/FEAT-004-unified-agent-rules/{spec,plan,checklist,test-report}.md`

**修改**
- `AGENTS.md`、`CLAUDE.md`、`.grok/rules/00-legalguard-rules.md` — 降级为指针
- `scripts/verify.sh` — 门禁扩展
- `docs/features/README.md` — 登记 FEAT-004
- `.atoms/ATOMS.md`、`.atoms/PROGRESS.md` — 决策与进度同步

**禁改（本迭代绝不触碰）**
- `app/backend/core/**`、`app/backend/models/**`、`main.py`、`lambda_handler.py`、`AuthCallback.tsx`、`index.html`、`.mgx/config.yaml`
- `app/**` 下全部业务代码

## 3. 分步实施顺序

1. 联网核实 Codex 与 dsh 的入口约定，确定映射策略。
2. 读取 `.atoms/ARCHITECTURE.md` 与现有 `AGENTS.md`、`verify.sh`，明确可复用内容与避免重复的边界。
3. 写 `.agent/` 六份规约。
4. 重写三份工具入口为纯指针。
5. 建 FEAT-004 编号目录并写 spec / plan。
6. 扩展 `scripts/verify.sh` 门禁。
7. 正向验证：`bash -n` 语法检查 + `--docs-only` 通过。
8. 反向验证：临时移除 `.agent/` 某文件 → 期望失败；临时让指针不含 `.agent/` → 期望失败；逐项恢复并复跑至通过。
9. 前端回归：`pnpm run lint` + `pnpm run build`。
10. 写 `checklist.md` 与 `test-report.md`，登记索引，同步 `.atoms/`。

## 4. 数据与接口变更

无。本迭代不涉及数据库表结构、接口契约、配置项变更，因此 `.env.example` 无需改动。

## 5. 风险与回滚

| 风险 | 应对 |
|------|------|
| 反向验证临时改动指针文件后未恢复，污染仓库 | 用备份文件保存原内容，验证后立刻还原并复跑门禁确认退出码 0 |
| `.agent/` 与 `docs/rules/` 出现矛盾表述 | `.agent/` 只写可判定强约束并显式声明细则以 `docs/rules/` 展开；冲突时以 `.agent/` 为执行依据 |
| 指针文件被后续迭代重新塞入规则正文 | 在三份指针与 `.agent/README.md` 同时写明维护规则，并由门禁校验指向性 |
| 门禁字符串匹配过宽导致误判通过 | 指针校验要求同时满足存在、非空、含 `.agent/` 三条 |
| 改动波及业务代码 | 本迭代不触碰 `app/**`，最后以前端 lint + build 回归确认 |

回滚方式：本迭代为纯新增文档 + 脚本增量，回滚只需移除 `.agent/` 目录与门禁新增的两个检查函数，指针文件恢复为 FEAT-003 版本即可。