# Plan：FEAT-011 规约收敛

## 基本信息

| 项 | 内容 |
|----|------|
| 迭代号 | FEAT-011-rules-pointers-mcp-skills |
| 对应 Spec | `./spec.md` |
| 确认状态 | ✅ 已确认 |

## 1. 方案概述

不改业务代码。指针去重、细则校准、Grok 接线（rules 指针 + skills.paths）、MCP 双文件（通用 `.mcp.json` + Grok TOML）。

## 2. 文件

| 文件 | 改动 |
|------|------|
| `AGENTS.md` `CLAUDE.md` `.grok/rules/00-lexhubpro-rules.md` | 删红线列表，只留路标 |
| `docs/rules/01,03,05,06` 与 `docs/README.md` | 去掉 web-sdk/AIHub/opus 现行表述；标明 `.agent/` 优先 |
| `.agent/README.md` | 增补 skills/MCP/Grok 遵守路径 |
| `.agent/skills/README.md` | 新增：权威技能目录约定 |
| `.grok/config.toml` | `[skills] paths = [".agent/skills"]` |
| `.mcp.json` | 新增 Playwright stdio，对齐现有 node cli.js |
| `scripts/verify.sh` | 指针仍检查存在且含 `.agent/`；可断言指针文件不含「未经用户确认」这类条款句（可选，避免误伤） |

## 3. MCP 维护约定

- 新增/修改 MCP **命令与参数**：先改 `.mcp.json`，再同步 `.grok/config.toml` 中同名 server（Grok 专有 env/timeout 只写 TOML）。
- Grok 优先级：`config.toml` > `.mcp.json`。同名时以 TOML 为准。

## 4. 无数据库变更
