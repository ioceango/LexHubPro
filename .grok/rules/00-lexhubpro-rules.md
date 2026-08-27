# Grok 规则入口指针（规约正文不在本文件）

> 本文件是 **Grok build / Grok CLI** 在本仓库的规则入口。
> Grok 会自动加载仓库根 `AGENTS.md` 与 `<repo>/.grok/rules/*.md`，因此本文件必须保留，但**只指路**。
>
> **规约正文全部位于 `.agent/`，本文件不抄写条款、不另立一套 Grok 规则。**
> 同时请读取仓库根 `AGENTS.md`（同为指针）。发生任何冲突，一律以 `.agent/` 为准。

## 必读清单（开工前按序读完，不可跳过）

1. `.agent/README.md`
2. `.agent/workflow.md`
3. `.agent/constraints.md`
4. `.agent/rules.md`
5. `.agent/architecture.md`
6. `.agent/verification.md`
7. `.agent/design.md`

细则展开见 `docs/rules/0X-*.md`。技能包权威目录：`.agent/skills/`（由 `.grok/config.toml` 的 `[skills].paths` 扫描）。MCP：通用清单 `.mcp.json`，Grok 专有超时/环境变量写在 `.grok/config.toml`。

## 验证入口

```bash
bash scripts/verify.sh --docs-only
bash scripts/verify.sh FEAT-005-your-slug
```

## 维护规则

规约变更只改 `.agent/`；本文件为纯路标，禁止在其中新增、改写或扩写规则条款。禁止把 `.agent/rules.md` 再复制进 `.grok/rules/`。
