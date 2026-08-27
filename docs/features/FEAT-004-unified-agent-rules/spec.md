# 需求规格说明：FEAT-004 跨工具统一 `.agent/` 规约

## 1. 背景与问题

本仓库已有三类约束载体，但存在结构性问题：

1. `.atoms/`（ATOMS.md / ARCHITECTURE.md / PROGRESS.md）是平台内团队协作上下文，写法偏「记录」而非「指令」，外部 AI 编码工具不会主动读取，也不便直接当规约执行。
2. FEAT-003 建立的根 `AGENTS.md` 承载了完整规则正文，导致：单文件过长、与 `docs/rules/` 内容部分重复、Codex 侧存在 32 KiB 指令体积上限风险。
3. 各工具入口（`AGENTS.md`、`CLAUDE.md`、`.grok/rules/`）虽已声明「指针」，但缺少一个**独立于任何单一工具**的规约目录，规则仍事实上寄生在某个工具入口里，后续新增工具会再次面临「往哪指」的问题。

结果是：不同 AI 编码工具（Grok build、DeepSeek harness、Codex、Claude Code）在本仓库的行为约束不一致，且规则容易多处漂移。

## 2. 目标

1. 建立 `.agent/` 作为**跨工具单一事实源**，把 `.atoms/` 中对 AI 编码有约束力的内容重组为强指令式规约（「必须 / 禁止 / 校验方式」句式），而非原文搬运。
2. 各工具入口文件统一降级为**纯指针**：只保留关键红线摘要 + 指向 `.agent/` 的必读清单，消除内容漂移。
3. 明确 `.atoms/` 与 `.agent/` 的职责边界与同步责任。
4. 把上述约束转化为**可自动判定的门禁**，规则不再只依赖自觉。

## 3. 非目标

- 不改动任何业务代码逻辑、页面行为、接口契约。
- 不废弃 `.atoms/`，也不废弃 `docs/rules/` 细则全文。
- 不为 DeepSeek harness 臆造专有入口文件格式。
- 不改变 FEAT-003 已确立的编号目录制本身。

## 4. 用户故事

1. 作为使用 Grok build 的开发者，我在仓库根看到 `AGENTS.md` 与 `.grok/rules/`，两者都明确把我导向 `.agent/`，我读完六份规约即掌握全部约束。
2. 作为使用 Codex 的开发者，根 `AGENTS.md` 体积很小、加载稳定，细则按需展开，不会撞上指令体积上限。
3. 作为使用 DeepSeek harness 的开发者，即便该工具没有专有约定文件，我仍能通过通用的根 `AGENTS.md` 获得完全一致的约束。
4. 作为使用 Claude Code 的开发者，`CLAUDE.md` 与其他工具入口的红线摘要完全一致，不会出现工具间行为差异。
5. 作为项目维护者，我只改 `.agent/` 一处即可让所有工具同步生效，并能用一条命令验证规约与指针是否完好。

## 5. 功能需求

### FR-1 `.agent/` 规约目录

新建六份职责单一的规约文件：

| 文件 | 职责 | 内容来源 |
|------|------|---------|
| `.agent/README.md` | 入口与阅读顺序、单一事实源声明、工具入口映射、与 `.atoms/` 关系 | 新编写 |
| `.agent/architecture.md` | 系统架构、技术栈、模块职责、关键链路、扩展指引 | `.atoms/ARCHITECTURE.md` 重组 |
| `.agent/rules.md` | 分层、设计原则、代码量化阈值、导入约束、异常处理、注释命名、测试 | `.atoms/ATOMS.md` + `docs/rules/01/06` 提炼 |
| `.agent/constraints.md` | 禁改文件、平台能力边界、配置读取、日志脱敏、业务硬约束、视觉规范、交付诚实性 | `.atoms/ATOMS.md` Constraints 重组 |
| `.agent/workflow.md` | 迭代流程与双确认门、编号目录规范、取号方法、各文档职责、Bug 附加要求 | `docs/rules/04` 提炼 |
| `.agent/verification.md` | 验证命令与固定顺序、门禁判定项、测试要求、完成定义 | `docs/rules/05` 提炼 |

要求：强指令式表述；职责单一不重复；与 `docs/rules/` 不得出现互相矛盾的表述。

### FR-2 工具入口降级为指针

- 重写 `AGENTS.md`、`CLAUDE.md`、`.grok/rules/00-legalguard-rules.md`：只保留必读清单 + 红线摘要 + 验证入口 + 维护规则。
- 三份指针均必须显式出现 `.agent/` 路径引用。
- 在 `.agent/README.md` 中给出各工具的入口映射表，并说明 dsh 的兜底策略与不臆造格式的理由。

### FR-3 职责边界与同步责任

在 `.agent/README.md` 写明：`.atoms/` 为平台协作上下文，`.agent/` 为对外部工具生效的执行依据；重叠内容以 `.agent/` 为准；任何架构/决策/红线变更须在同一迭代内同步更新两侧。

### FR-4 门禁可校验

增强 `scripts/verify.sh` 的文档合规 gate：
- 校验 `.agent/` 六份必需文件存在且非空；
- 校验三份工具指针文件存在、非空、且内容确实包含 `.agent/` 引用；
- 不合规时以非零退出码失败，并逐项列出问题。

## 6. 验收标准（AC）

| 编号 | 标准 |
|------|------|
| AC-01 | `.agent/` 下六份规约文件均存在且非空 |
| AC-02 | 规约为强指令式表述，覆盖架构、规范、约束、流程、验证五个维度 |
| AC-03 | `AGENTS.md`、`CLAUDE.md`、`.grok/rules/00-legalguard-rules.md` 均为指针且均包含 `.agent/` 引用 |
| AC-04 | 指针文件中不再承载完整规则正文 |
| AC-05 | `.agent/README.md` 含工具入口映射表，覆盖 Grok / Codex / dsh / Claude Code，并说明 dsh 兜底策略 |
| AC-06 | `.agent/README.md` 明确 `.atoms/` 与 `.agent/` 的边界、优先级与同步责任 |
| AC-07 | 门禁校验 `.agent/` 六份文件与三份指针，合规时退出码 0 |
| AC-08 | 故意缺失 `.agent/` 文件时门禁非零退出并指出缺失项 |
| AC-09 | 故意让指针文件不指向 `.agent/` 时门禁非零退出并指出该问题 |
| AC-10 | 反向验证后现场完全恢复，复跑门禁通过 |
| AC-11 | 未改动任何业务代码，前端 lint 与 build 通过 |
| AC-12 | FEAT-004 四份文档齐全并在 `docs/features/README.md` 登记 |

## 7. 边界与约束

- 纯文档与校验脚本任务，禁止改动业务代码。
- 不得修改禁改文件清单中的任何文件。
- 反向验证使用的临时文件必须在验证后立即清理。
- 测试报告只写真实执行结果。

## 8. 影响面

| 类型 | 路径 |
|------|------|
| 新增 | `.agent/README.md`、`.agent/architecture.md`、`.agent/rules.md`、`.agent/constraints.md`、`.agent/workflow.md`、`.agent/verification.md` |
| 新增 | `docs/features/FEAT-004-unified-agent-rules/`（四份文档） |
| 修改 | `AGENTS.md`、`CLAUDE.md`、`.grok/rules/00-legalguard-rules.md`（降级为指针） |
| 修改 | `scripts/verify.sh`（门禁扩展） |
| 修改 | `docs/features/README.md`、`.atoms/ATOMS.md`、`.atoms/PROGRESS.md` |
| 不动 | `app/**` 全部业务代码 |