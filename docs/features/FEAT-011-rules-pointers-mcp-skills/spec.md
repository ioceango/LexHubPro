# Spec：规约指针纯路标、细则校准、Grok 遵守 .agent、MCP/Skills 布局

## 基本信息

| 项 | 内容 |
|----|------|
| 迭代号 | FEAT-011-rules-pointers-mcp-skills |
| 类型 | 需求 |
| 优先级 | P1 |
| 提出人 | 用户 |
| 创建日期 | 2026-08-28 |
| 确认状态 | ✅ 已确认 |

## 1. 背景与问题

仓库已有「`.agent/` 单一事实源 + 各工具指针」设计，但指针里仍复制红线摘要；`docs/rules` 部分条款仍写 web-sdk / AIHub / claude-opus-5，和现行 JWT+MinIO 打架。Grok 另有 `.grok/rules` 与 `.grok/config.toml`，容易被理解成「Grok 自己一套规则」。后续还要在仓库里积累 vibe coding skills，并希望 MCP 尽量跨工具共用。

## 2. 评估结论（约束后续方案）

### 2.1 指针收成纯路标 — 可行且应做

`AGENTS.md`、`CLAUDE.md`、`.grok/rules/00-lexhubpro-rules.md` 里的「关键红线摘要」是正文的拷贝。应删掉条款列表，只保留：这是谁的入口、必读 `.agent/` 清单、冲突以 `.agent/` 为准、验证命令。改规则仍然只改 `.agent/`。

### 2.2 校准 `docs/rules` — 可行且应做

`docs/rules` 是给人读的细则；`.agent/` 是给工具执行的硬约束。两者不得矛盾。当前 01/03/05/06 仍有平台脚手架表述。本迭代校准过时条款，并在 `docs/README.md` 标明：执行以 `.agent/` 为准，细则是展开。

### 2.3 `.grok/rules` 能否整包搬进 `.agent/` — **不能取消 Grok 入口，但正文已经可以只在 `.agent/`**

Grok Build / Grok CLI 会自动加载：

- 仓库根 `AGENTS.md`（以及 `Claude.md`）
- `<repo>/.grok/rules/*.md`（**始终扫描**，这是 Grok 官方机制）

因此：

- **Grok 会遵守 `.agent/`**：只要 `AGENTS.md` 与 `.grok/rules` 都指向 `.agent/` 并禁止在指针里写新条款（现状已如此，本迭代把指针再缩短）。
- **不能删除所有 Grok 入口文件** 还指望 Grok「自己找到」`.agent/`；官方不会去读一个未在入口列出的目录作为唯一规则源。
- **正确收敛**：规则正文只在 `.agent/`；`.grok/rules/00-*.md` 继续当纯路标（可与 `AGENTS.md` 同构、更短）。不要把 `.agent/rules.md` 再复制进 `.grok/rules/`。

### 2.4 Skills 积累放哪 — 正文放 `.agent/skills/`，Grok 用配置/发现去读

Grok 默认发现的是 `.grok/skills/`、**`.agents/skills/`（复数）**，以及 Claude/Cursor 的 skills 目录，**不是** `.agent/skills/`（单数）。

本迭代约定：

- **规范与技能包的权威目录是 `.agent/skills/`**（与规约同树，跨工具一份）。
- Grok 遵守方式：在项目 `.grok/config.toml` 的 `[skills].paths` 增加 `.agent/skills`（官方支持额外扫描目录）。不在 `.grok/skills` 再放一份正文。
- 本迭代只建目录约定与说明，**不编写具体业务 skill 正文**（后续按需往 `.agent/skills/<name>/SKILL.md` 加）。

### 2.5 MCP 是否仅 Grok、能否通用

| 事实 | 含义 |
|------|------|
| MCP **协议**通用 | 同一个 Playwright 进程可被任何 MCP 客户端调用 |
| **配置文件格式/路径不通用** | Grok：`.grok/config.toml` 的 `[mcp_servers.*]`；Cursor：`.cursor/mcp.json`；另有项目根 `.mcp.json`（Grok 也会读，优先级低于 `config.toml`） |
| 仓库里现有 Playwright MCP | 只写在 `.grok/config.toml`，所以目前是 **Grok 项目级配置** |

结论：不能指望只留一份 TOML 让 Cursor/Claude/Codex 都原生读取。应增加一份 **通用 MCP 清单**（项目根 `.mcp.json`），Grok 继续可用 `.grok/config.toml`（优先级更高，适合 Grok 专有超时、`PLAYWRIGHT_BROWSERS_PATH`）。两处命令应对齐；密钥仍用环境变量，不入库。

## 3. 范围

### 3.1 本次要做

- 三个指针文件改为纯路标（无红线条款拷贝）。
- 校准 `docs/rules` 过时条款，与 `.agent/` 对齐；目录索引写明两层关系。
- `.agent/README.md` 写清：Grok 如何通过指针遵守 `.agent/`；skills 权威目录；MCP 通用清单 vs Grok TOML。
- 预留 `.agent/skills/README.md`；`.grok/config.toml` 增加 `[skills] paths`。
- 新增项目根 `.mcp.json`（Playwright，与现有 Grok 配置等价的 command/args），并在 `.agent` 说明维护方式。

### 3.2 本次明确不做

- 不把 `.grok/` 整个删掉（Grok 仍需要入口与项目 MCP/skills 接线）。
- 不编写具体审查/部署 skill 内容。
- 不改业务代码、不改表。
- 不强制 Cursor/Claude 配置文件（无这些工具入口则不加；只提供 `.mcp.json` 供它们选用）。
- 不把 MCP 密钥写入仓库。

## 4. 用户故事

- 作为维护者，我改一条红线只改 `.agent/`，换 Grok/Codex/Claude 行为一致。
- 作为维护者，我读 `docs/rules` 时看到的应与现行 JWT+MinIO 架构一致。
- 作为后续贡献者，我知道 skill 往 `.agent/skills/` 放，而不是每个工具目录各放一份。
- 作为用 Playwright MCP 的开发者，我知道通用清单在 `.mcp.json`，Grok 专有项在 `.grok/config.toml`。

## 5. 验收标准

- [x] AC-01：`AGENTS.md`、`CLAUDE.md`、`.grok/rules/00-lexhubpro-rules.md` 不含具体红线条目列表，仅路标 + 必读清单 + 验证命令。
- [x] AC-02：`docs/rules/01` 不再把 web-sdk/entities/AIHub 当作现行适配器；`03` 不再把 claude-opus-5 当作现行审查模型。
- [x] AC-03：`docs/README.md` 与 `.agent/README.md` 写明三层关系及「执行以 `.agent/` 为准」。
- [x] AC-04：`.grok/rules` 仍存在且为指针；说明 Grok Build 通过它与 `AGENTS.md` 遵守 `.agent/`。
- [x] AC-05：存在 `.agent/skills/README.md`；`.grok/config.toml` 能扫描该目录。
- [x] AC-06：存在 `.mcp.json` 描述 Playwright MCP；与 `.grok/config.toml` 的 command 一致。
- [x] AC-07：`bash scripts/verify.sh --docs-only` 通过。
- [x] AC-08：Playwright 截图 S01 起（打开规约入口页或仓库说明即可，证明文档迭代有端到端记录）。

## 6. 影响面

| 维度 | 影响 |
|------|------|
| 页面/接口/表 | 无 |
| 配置 | `.grok/config.toml` 增加 skills.paths；新增 `.mcp.json` |
| 工具行为 | 指针变短后，模型必须读 `.agent/` 才看得到红线（这是目标） |
