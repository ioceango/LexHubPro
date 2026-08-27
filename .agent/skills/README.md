# `.agent/skills/` — 仓库技能包权威目录

本目录是 LexHubPro 的 **skill 正文唯一落点**。不在 `.grok/skills/`、`.claude/skills/`、`.cursor/skills/` 再各放一份。

## 约定

- 每个技能一个子目录：`.agent/skills/<name>/SKILL.md`（YAML frontmatter + markdown 步骤）。
- 本目录只放项目相关、可复用的任务包；通用规约仍写在 `.agent/*.md`，不要把 skill 正文塞进指针文件。

## 已登记

| 名称 | 何时用 |
|------|--------|
| [code-review](code-review/SKILL.md) | 按架构 / 后端 / 前端 / 数据库四视角审查 LexHubPro 改动；结果写入该迭代 `review-report/Rnn-YYYY-MM-DD.md`；`/code-review` |

## 各工具如何读到这里

| 工具 | 方式 |
|------|------|
| Grok Build / Grok CLI | 项目 `.grok/config.toml` 的 `[skills] paths = [".agent/skills"]`。Grok 默认扫描的是 `.grok/skills/` 与 `.agents/skills/`（复数），**不是** `.agent/skills/`，因此必须显式配置。 |
| Claude / Cursor 等 | 按其官方 skills 发现机制把本目录加入额外路径，或做软链。禁止复制正文。 |

## 维护

新增或修改 skill 只改本目录。发现其他工具目录里出现拷贝，以本目录为准并删除拷贝。
