# 测试验证报告：FEAT-006

## 1. 报告信息

| 项 | 内容 |
|----|------|
| 迭代编号 | FEAT-006 |
| 执行日期 | 2026-08-27 |
| 范围 | 规约与分层目录，不迁存量表 |
| 结论 | 通过 |

## 2. 实测命令

| 步骤 | 命令 | 退出码 | 结果 |
|------|------|--------|------|
| 文档门禁 | `bash scripts/verify.sh --docs-only` | 0 | 通过；需求目录 6 个（含 FEAT-006） |

```
==== ⓿ 文档合规 gate ====
  跨工具规约(.agent)：6/6 份文件就绪
  工具入口指针：3/3 份有效并指向 .agent/
  需求(FEAT) 发现 6 个编号目录
  缺陷(BUG) 发现 2 个编号目录
.agent 规约齐全、工具指针有效、编号目录命名与四文档齐全性、非占位与索引登记全部通过
✓ ⓿ 文档合规 gate 通过
结论：通过
```

## 3. 验收对照

| 编号 | 结果 |
|------|------|
| AC-01 | 通过：现行 `.agent/` 不再把 models 列为禁改 |
| AC-02 | 通过：architecture §3 四层铁律 + tb_* 注释 |
| AC-03 | 通过：AGENTS.md / CLAUDE.md / grok rules 已同步 |
| AC-04 | 通过：01 / 06 / 07 已改 |
| AC-05 | 通过：`api/`、`repositories/` 已建；`main.py` 扫描 api |
| AC-06 | 通过：docs-only 退出码 0 |

pytest（重构后复跑）：

```
37 passed, 5 warnings in 3.95s
```

## 4. 未执行

未在已有 compose 库上手工 `psql` 核对 RENAME（后端重启时由 `schema_bootstrap` 幂等执行）。未跑平台 entities 端到端。
