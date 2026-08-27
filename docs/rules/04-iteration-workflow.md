# 04 需求与 Bug 迭代流程

> 铁律：**每个需求、每个 Bug 都必须先有 `spec.md` 与 `plan.md`，经用户确认后才允许写业务代码。** 未确认即开发的产出视为无效交付。

## 1. 流程总览

```
① 收集与澄清 ──▶ ② 取编号建目录 ──▶ ③ spec.md ──▶ ④【用户确认门 A】
                                                        │ 未通过 → 回 ①
                                                        ▼
                                   ⑤ plan.md ──▶ ⑥【用户确认门 B】
                                                        │ 未通过 → 回 ⑤
                                                        ▼
                        ⑦ checklist.md 初始化 ──▶ ⑧ 编码实现
                                                        ▼
              ⑨ 自动化验证（docs gate / lint / test / build / Playwright）
                                                        ▼
     ⑩ test-report.md + 该迭代 test-report/S01-*.png 编号截图（每个 FEAT/BUG 强制）
                                                        ▼
                                     ⑪【用户验收】──▶ ⑫ 归档（索引 + 必要时 DDL）
                                                        ▼
                          ⑬ 在编号分支上按 09 提交并合入 main（有 .git 时强制）
```

## 2. 目录与命名（编号目录制，强约束）

需求与 Bug **分库存放**，各自独立编号：

| 类型 | 目录 | 命名格式 | 示例 |
|------|------|----------|------|
| 需求 | `docs/features/` | `FEAT-<3位序号>-<英文短slug>/` | `docs/features/FEAT-004-batch-review/` |
| Bug | `docs/bug-fix/` | `BUG-<3位序号>-<英文短slug>/` | `docs/bug-fix/BUG-003-report-export-empty/` |

每个编号目录下**固定四份文档，缺一不可**：

```
docs/features/FEAT-004-batch-review/
├── spec.md          # 第 1 步：写完等用户确认
├── plan.md          # 第 2 步：写完等用户确认
├── checklist.md     # 第 3 步：开发同步勾选
├── test-report.md   # 第 4 步：验证后生成（必须引用编号截图）
└── test-report/     # Playwright 截图目录，与 md 同级
    ├── S01-<slug>.png
    └── S02-<slug>.png
```

Bug 迭代同样必须有 `test-report/` 与 `S01` 起的编号 png。细则见 `.agent/verification.md` §3.1。

**命名与编号规则**

1. 序号为 **3 位零填充**（`001`、`012`、`105`），需求与 Bug 各自独立计号。
2. 序号**全局单调递增，不复用、不跳号占位**。建目录前必须先执行 `ls docs/features` / `ls docs/bug-fix` 取现有最大号 +1。
3. `slug` 为英文小写 + 短横线，2-4 个词概述主题；禁止中文、下划线、空格、大写。
4. 目录名与 `spec.md` 标题中的编号必须一致。
5. Bug 修复与需求走**同一套流程**，仅所在目录与 `spec.md` 的「类型」字段不同（`需求` / `Bug`）。
6. 新建迭代必须**同步登记**到 `docs/features/README.md` 或 `docs/bug-fix/README.md` 的索引表，未登记视为文档不合规。
7. 四份文档均不得留空或仅保留未完成占位标记。

**自动校验**：以上规则由 `bash scripts/verify.sh --docs-only` 强制校验，不通过则整个验证流程以非零码失败。

## 3. 各阶段要求

### ① 收集与澄清

- 必须明确：使用者是谁、触发场景、期望结果、异常场景、验收标准。
- 需求存在两种以上合理解释时，**先提问再写 spec**，不得自行假设。
- Bug 必须拿到：复现步骤、实际表现、期望表现、发生环境、可关联的 `trace_id` 或错误编号。

### ② 取编号建目录

- 先 `ls docs/features` / `ls docs/bug-fix` 确认当前最大号，再取 +1。
- 建目录后立即在对应 `README.md` 索引表登记一行（状态先写 `spec 待确认`）。

### ③ `spec.md`（做什么）

使用 [templates/spec-template.md](../templates/spec-template.md)。必须包含：范围边界（含**明确的不做事项**）、用户故事、功能需求、非功能需求、验收标准（可测、可判定真假）、影响面评估。

**禁止**：在 spec 中写技术方案、库选型、文件路径。

### ④ 确认门 A

- 向用户展示 spec 摘要与关键取舍点，等待明确「确认」。
- 用户提出修改 → 更新 spec 并重新确认，**不得带着未确认的 spec 进入 plan**。

### ⑤ `plan.md`（怎么做）

使用 [templates/plan-template.md](../templates/plan-template.md)。必须包含：架构影响、分层落点（哪些 router / service / repository / page / hook / lib）、数据库变更、配置项变更、设计模式选择及理由、任务拆分（每项 ≤ 半天粒度）、风险与回滚方案、测试策略。

**约束校验（写 plan 时必须自查）**：
1. 是否把 `schemas` 与 `models` 合并？禁止。`models/` 可改；新表必须 `tb_*` 且含表/字段注释。表变更必须同步 `docs/ddl/database-ddl-er.md`。
2. 改动是否落在 `api → services → repositories → models` 四层？旁路包不得承接新的长期业务。
3. 是否引入数据库事务跨 AI 调用？是则重新设计（见 06）。
4. 是否有新硬编码值？有则转配置项（见 03）。
5. 是否超出 01 的复杂度阈值？超出则给出拆分或书面豁免理由。
6. 是否新增第三方服务（需要密钥）？是则在 plan 中列出所需密钥名称与用途。

### ⑥ 确认门 B

- 展示 plan 摘要（改动文件清单、数据库/配置变更、风险项），等待用户明确确认。
- 开发过程中若方案发生实质变化（新增表、改动契约、变更技术选型），**必须回到本门重新确认**并在 plan 追加「变更记录」。

### ⑦ `checklist.md` 初始化

按 [templates/checklist-template.md](../templates/checklist-template.md) 从 plan 的任务与验收标准逐条生成，全部初始化为 `- [ ]`。checklist 是开发期唯一进度真相来源。

### ⑧ 编码实现

- 严格按 plan 的分层落点实现，遵循 01 全部标准。
- 每完成一项立即把对应行改为 `- [x]`（连同实际改动文件路径一并记录）。
- 出现 plan 未覆盖的问题：小范围偏差在 plan 追加「实施备注」；实质偏差回门 B。

### ⑨ 自动化验证

按 [05 测试验证规范](05-testing-and-automation.md) 的固定顺序执行（文档合规 gate → 静态检查 → 测试 → 构建 → **Playwright 端到端**），全部通过才进入下一步。每个 FEAT / BUG 都必须跑 Playwright，不得跳过。

### ⑩ `test-report.md` 与编号截图

按 [templates/test-report-template.md](../templates/test-report-template.md) 生成，必须附真实命令输出摘要与结论，禁止「预计通过」这类未执行结论。

Playwright 截图必须写入本迭代 `test-report/` 目录，文件名 `S01-<slug>.png` 起连续编号；`test-report.md` 用表格引用每一张并标注覆盖的 AC。缺截图或未引用不得宣称完成。细则见 `.agent/verification.md` §3.1。

### ⑪ 用户验收

- 提交内容：变更摘要、验收标准逐条对照、`test-report.md` 结论、已知限制。
- 用户提出问题 → 视为新的 Bug 迭代（走完整流程）或在本迭代内补充（更新四份文档）。

### ⑫ 归档

- 迭代文档保留在 `docs/features/` 或 `docs/bug-fix/` 的编号目录内，不删除、不重命名、不复用编号。
- 更新对应索引 `docs/features/README.md` / `docs/bug-fix/README.md`：状态改为 `已完成` / `已修复`，并更新「下一个可用编号」。
- 若架构发生变化，同步 `.agent/architecture.md`。

### ⑬ Git 提交与合入（有 `.git` 时强制）

按 [09 Git 提交与分支规范](09-git-commit-and-branch.md)：工作在 `feat/FEAT-xxx-slug` 或 `fix/BUG-xxx-slug`；每次 commit 主题必须含本迭代编号；合入 `main` 后删工作分支。无 `.git` 时跳过本步，不视为未完成。

## 4. 紧急线上 Bug 例外通道

仅适用于「功能完全不可用」的阻塞级故障（如登出 500、审查接口全量失败）：

1. 允许先做**最小止血修复**（不超过 2 个文件、不含数据库结构变更、不含新依赖）。
2. 止血后 **24 小时内必须补齐**编号目录与四份文档，并在 spec 中标注「例外通道：紧急止血」。
3. 例外通道不得用于新功能、重构、依赖升级。

## 5. 完成定义（Definition of Done）

一个迭代只有全部满足下列条件才算完成：

- [ ] 编号目录命名合规（`FEAT-XXX-<slug>` / `BUG-XXX-<slug>`），四份文档齐全且非占位
- [ ] 已登记到 `docs/features/README.md` 或 `docs/bug-fix/README.md` 索引表
- [ ] `bash scripts/verify.sh --docs-only` 通过
- [ ] `spec.md`、`plan.md` 均已获用户确认
- [ ] `checklist.md` 全部条目为 `- [x]`（或已注明豁免并获确认）
- [ ] 前端 `pnpm run lint && pnpm run build` 通过
- [ ] 后端改动文件 `python -m py_compile` 通过，相关测试通过
- [ ] Playwright 端到端已通过；`test-report/` 含 `S01-*.png` 起的编号截图，且已在 `test-report.md` 引用
- [ ] `test-report.md` 已生成且结论为通过或有条件通过
- [ ] 新增/变更配置已写入 `.env.example` 并文档化
- [ ] 关键路径已按 02 补齐日志与 `trace_id` 埋点
- [ ] 索引表状态已更新；架构变更已同步 `.agent/architecture.md`
- [ ] 若存在 `.git`：提交主题含本迭代 `FEAT-NNN` 或 `BUG-NNN`，且工作分支名含同一编号（见 09）