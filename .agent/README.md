# .agent/ — 跨 AI 编码工具统一规约（单一事实源）

> 本目录是本仓库对**所有外部 AI 编码工具**生效的强制规约集合。
> Grok build / Grok CLI、DeepSeek harness (dsh)、Codex、Claude Code、Cursor 等工具在本仓库工作时，
> 必须以本目录内容为唯一执行依据。
> **任何冲突，一律以 `.agent/` 为准。**

## 1. 阅读顺序（不可跳过）

| 顺序 | 文件 | 内容 |
|------|------|------|
| 1 | `.agent/README.md`（本文件） | 单一事实源声明、工具入口映射 |
| 2 | `.agent/workflow.md` | 迭代流程与用户确认门（决定你**何时才允许改代码**） |
| 3 | `.agent/constraints.md` | 禁改文件、平台能力边界、红线（决定你**不能做什么**） |
| 4 | `.agent/rules.md` | 工程规范硬约束（决定你**怎么写**） |
| 5 | `.agent/architecture.md` | 系统架构与模块职责（决定你**改哪里**） |
| 6 | `.agent/verification.md` | 验证命令、顺序与完成定义（决定你**何时算做完**） |
| 7 | `.agent/design.md` | 视觉设计（非安全红线） |

规约六份 + `design.md` 读完，才允许开始动手。视觉实现以 `design.md` 为准。

## 2. 单一事实源声明

- 规约正文**只写在 `.agent/`**。
- 根 `AGENTS.md`、`CLAUDE.md`、`.grok/rules/*.md` 一律为**纯路标**：只保留「这是谁的入口 + 指向 `.agent/` 的必读清单 + 验证命令」。**禁止**在指针里复制红线条目或其他条款。
- **禁止**在指针文件中新增、改写、扩写任何规则。发现指针文件与 `.agent/` 不一致时，以 `.agent/` 为准并修正指针（通常是删掉指针里多出来的条款）。
- 规约变更只允许改 `.agent/` 下对应文件。
- `docs/rules/0X-*.md` 是给人读的细则展开；与 `.agent/` 冲突时**改细则、不改执行口径**。

## 3. 工具入口映射

| 工具 | 官方入口机制 | 本仓库生效路径 |
|------|-------------|---------------|
| Grok build / Grok CLI | 读取根 `AGENTS.md` 与 `.grok/rules/*.md` | `AGENTS.md`（指针）+ `.grok/rules/00-lexhubpro-rules.md`（指针）→ `.agent/` |
| Codex | 读取根 `AGENTS.md`，自项目根向工作目录逐层合并，深层覆盖浅层；支持同目录 `AGENTS.override.md` 优先 | 根 `AGENTS.md`（指针）→ `.agent/` |
| Claude Code | 读取 `CLAUDE.md` | `CLAUDE.md`（指针）→ `.agent/` |
| DeepSeek harness (dsh) | 未见官方公开的仓库指令文件约定 | 按业界通用约定走根 `AGENTS.md`（指针）→ `.agent/` |
| Cursor / Jules / Copilot 等 | 通用 `AGENTS.md` 约定 | 根 `AGENTS.md`（指针）→ `.agent/` |

说明：
- `AGENTS.md` 是跨工具通用的开放约定（"给 agent 看的 README"），因此作为兜底入口最稳妥。
- **Grok 如何遵守 `.agent/`**：Grok Build / Grok CLI 官方会加载根 `AGENTS.md` **以及** `<repo>/.grok/rules/*.md`。两处都是指针，读完必读清单后执行 `.agent/` 正文。不能删除 `.grok/rules/` 还指望 Grok 自己找到 `.agent/`。也不要把 `.agent/rules.md` 再复制进 `.grok/rules/`。
- dsh 侧**没有**已核实的专有入口文件约定，因此本仓库**不臆造** `.dsh/` 之类的目录或文件格式，统一由根 `AGENTS.md` 承接。若后续 dsh 公布官方约定，只需新增一个指向 `.agent/` 的指针文件，规约正文无需改动。
- Codex 存在 32 KiB 指令体积上限，这也是本仓库把细则拆进 `.agent/` 多文件、只在根入口放路标的原因。

## 4. `.agent/` 与 `docs/` 的关系

- `.agent/` 是给 AI 编码工具的执行硬约束。
- 进度与决策落在 `docs/features/`、`docs/bug-fix/` 编号目录；架构执行口径以 `.agent/architecture.md` 为准。
- `docs/rules/0X-*.md` 是细则展开；与 `.agent/` 冲突时改细则。
- 已废弃平台协作目录 `.atoms/`（不参与运行与部署，内容易与 `.agent/` 漂移）。
- **产品名**：LexHubPro。认证仅自建 JWT；存储仅 MinIO。
- **后端四层强制**：`api → services → repositories → models`，调用单向。
- **表/字段用途注释**：ORM `comment=` 与 DDL 的 `COMMENT ON` 必须同时存在。
- **无 `local_` 业务文件名**，HTTP 不用 `/local-` 前缀。
- 视觉见 `.agent/design.md`。

## 5. 自检

规约与指针文件的存在性、非空性、指向正确性由文档门禁自动校验：

```bash
bash scripts/verify.sh --docs-only
```

该命令会校验 `.agent/` 必需文件（含 `design.md`）齐全非空，以及各工具指针文件存在、指向 `.agent/`、且不含红线条款拷贝；不合规以非零退出码失败并列出具体问题项。

## 6. Skills

- **权威目录**：`.agent/skills/`（与规约同树，跨工具一份正文）。
- 每个技能一个子目录：`.agent/skills/<name>/SKILL.md`。目录约定见 `.agent/skills/README.md`。
- **不要**在 `.grok/skills/`、`.claude/skills/`、`.cursor/skills/` 再放一份正文。
- Grok 默认不扫描 `.agent/skills/`（它扫描的是 `.grok/skills/` 与 **`.agents/skills`（复数）**）。本仓库在项目 `.grok/config.toml` 设置 `[skills] paths = [".agent/skills"]`，让 Grok 读权威目录。
- 本迭代不编写具体业务 skill；后续按需添加。

## 7. MCP

- MCP **协议**通用；**配置文件格式不通用**。
- **通用清单**：仓库根 `.mcp.json`（Playwright stdio：仓库内 `@playwright/mcp` cli，不走 npx）。Cursor / Claude / 其他客户端可选用此文件。
- **Grok 专有**：`.grok/config.toml` 的 `[mcp_servers.*]`（可含 `startup_timeout_sec`、`PLAYWRIGHT_BROWSERS_PATH` 等）。Grok 优先级：`config.toml` > `.mcp.json`，同名以 TOML 为准。
- **维护**：改 MCP 的 command/args 时先改 `.mcp.json`，再同步 TOML 中同名 server。密钥只用环境变量，禁止写入仓库。
- 不为 Cursor/Claude 强制新建一整套产品配置树；仓库没有 `.cursor/` 则不加。