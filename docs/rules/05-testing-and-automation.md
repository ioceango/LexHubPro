# 05 自动化测试验证规范

> 目标：每个迭代都能用**一条命令**跑完静态检查 + 构建 + 测试，并自动产出可归档的验证报告。

## 1. 测试分层与职责

| 层级 | 范围 | 位置 | 工具 | 覆盖要求 |
|------|------|------|------|----------|
| L1 静态检查 | 类型、代码风格、语法 | 全项目 | `eslint`（前端）、`python -m py_compile`（后端） | 100% 无错误，`--quiet` 下零输出 |
| L2 单元测试 | 纯函数、归一化、解析、工具 | `app/backend/tests/unit/`、`app/frontend/src/**/*.test.ts` | `pytest`、`vitest` | 领域纯函数覆盖率 ≥ 80% |
| L3 集成测试 | router + service（AI/DB 用 mock 或测试库） | `app/backend/tests/integration/` | `pytest` + `httpx.AsyncClient` | 每个自定义 API 至少覆盖 成功 / 入参非法 / 依赖失败 三条路径 |
| L4 构建验证 | 产物可构建、无未解析导入 | `app/frontend` | `pnpm run build` | 必须成功 |
| L5 端到端与 UI | 关键用户旅程、页面渲染 | `app/frontend/e2e/` 与迭代 `test-report/` | Playwright（MCP 或 `pnpm run e2e`） | 每个 FEAT/BUG 必须跑；截图编号写入报告 |

**必须写单元测试的模块（本项目）**：
- `services/contract_review.py` 的 `_extract_json_block`、`_normalize_payload`、`_normalize_risk_level`、`_normalize_score`、`_as_list_of_dict/_as_list_of_str`（纯函数、高风险、直接影响报告正确性）；
- 前端 `lib/review.ts` 的 `parseJsonField`、报告文本生成、下载链接解析；
- 配置降级逻辑（`frontend_url` 缺失 / 占位符 / 正常三种情况）。

**AI 调用本身不做真实请求测试**：必须 mock `AIInvoker` / `llm_providers` 的补全接口，用固定桩数据验证编排与容错（含 JSON 修复重试路径）。禁止打真实供应商额度。

## 2. 用例编写要求

1. 命名表达意图：`test_normalize_score_falls_back_when_value_missing`，禁止 `test_1`、`test_ok`。
2. 结构固定 **Arrange / Act / Assert** 三段，用空行分隔。
3. **一个用例一个断言主题**；多个无关断言必须拆用例。
4. 必须覆盖三类输入：正常值、边界值（0 / 100 / 空字符串 / 空列表 / 超限长度）、异常值（`None`、类型错误、非法枚举、被截断的 JSON）。
5. 断言具体值，禁止只断言 `assert result` 或 `assert response.status_code != 500`。
6. 测试**不得依赖外部网络、真实 AI、真实对象存储**；不得依赖执行顺序与全局状态。
7. 每个 Bug 修复必须补一条**回归用例**，用例注释注明迭代编号（例如 `# regression: BUG-002-ai-review-failure`）。
8. 前端组件测试只测行为（渲染关键文案、点击触发回调、加载/错误态切换），不断言 class 名与像素。

## 3. 执行顺序（不得调换）

```bash
# ⓿ 文档合规 gate（编号目录命名 / 四文档齐全非占位 / 索引已登记）
bash scripts/verify.sh --docs-only

# ① 后端静态检查（只检查本次改动的 .py）
cd app/backend && python -m py_compile api/*.py services/*.py repositories/*.py models/*.py

# ② 后端测试
cd app/backend && python -m pytest tests -q

# ③ 前端依赖与 Lint
cd app/frontend && pnpm i && pnpm run lint

# ④ 前端单元测试（存在测试文件时）
cd app/frontend && pnpm run test -- --run

# ⑤ 前端构建（最终门禁：捕获未解析导入等致命问题）
cd app/frontend && pnpm run build

# ⑥ Playwright 端到端（截图落到 docs/.../test-report/Sxx-*.png）
cd app/frontend && HTTP_PROXY= HTTPS_PROXY= NO_PROXY='*' pnpm run e2e
```

顺序理由：静态错误最便宜先排除；构建后再跑 Playwright，避免用旧产物做 UI 断言。**任一步失败必须修复后从该步重跑，禁止跳过继续。** 同一问题修复尝试超过 3 次仍失败，停止并上报。

## 3.1 Playwright 与编号截图（每个 FEAT / BUG 强制）

与 `.agent/verification.md` §3.1 一致，摘要如下：

| 项 | 强制要求 |
|----|----------|
| 谁必须跑 | 每一个 `FEAT-*` 与 `BUG-*`，含纯修复 UI 的迭代 |
| 工具 | Playwright MCP 优先；否则 `cd app/frontend && pnpm run e2e` |
| 截图目录 | `docs/features/<id>/test-report/` 或 `docs/bug-fix/<id>/test-report/`（与 `test-report.md` 同级） |
| 文件名 | `S<2位序号>-<英文短slug>.png`，从 S01 连续 |
| 报告 | `test-report.md` 必须有编号截图表：编号、路径、覆盖 AC、说明 |
| 覆盖 | 本迭代主路径 + 至少一条失败/边界；相关页面都要拍 |
| 禁止 | curl 顶替 UI、截图不归档、无编号、报告不引用、用设计稿顶替 |
| 豁免 | 仅零 UI 迭代，checklist 写明理由并获用户确认 |

`scripts/verify.sh <FEAT-或-BUG-编号>` 在第 ⑥ 步跑 Playwright，并把 `E2E_SCREENSHOT_DIR` 指到该迭代 `test-report/`；跑完后检查至少一张 `S[0-9][0-9]-*.png` 且文件名出现在 `test-report.md`。

## 4. 一键验证脚本

约定脚本 `scripts/verify.sh`（新增时不得改动业务代码），职责：先执行**文档合规 gate**，再按 §3 顺序执行静态检查/测试/构建，收集每步退出码与输出摘要，并生成 `docs/features/<FEAT-XXX-slug>/test-report.md` 或 `docs/bug-fix/<BUG-XXX-slug>/test-report.md`。

用法：

```bash
bash scripts/verify.sh --docs-only              # 仅跑文档合规 gate
bash scripts/verify.sh                          # gate + 全量验证
bash scripts/verify.sh BUG-002-ai-review-failure  # 全量验证并写入该迭代报告
```

**文档合规 gate 判定项（任一不满足即非零退出）**：

| 校验项 | 判定标准 |
|--------|----------|
| 目录命名 | `docs/features/` 下必须匹配 `FEAT-[0-9]{3}-[a-z0-9-]+`；`docs/bug-fix/` 下必须匹配 `BUG-[0-9]{3}-[a-z0-9-]+` |
| 文档齐全 | 每个编号目录必须同时存在 `spec.md`、`plan.md`、`checklist.md`、`test-report.md` |
| 非空占位 | 四份文档均非空，且不含 `TODO` / `待填写` / `<占位` 等未完成标记 |
| 索引登记 | 每个编号目录必须出现在对应目录的 `README.md` 索引中 |
| 编号唯一 | 同一编号不得出现在多个目录名中 |
| 索引存在 | `docs/features/README.md` 与 `docs/bug-fix/README.md` 必须存在 |

要求：
- 任一步失败立即以非零码退出，并在报告中标注失败步骤与关键错误行；
- 输出仅保留摘要（每步末 20 行），避免把完整日志塞进报告；
- 脚本自身不修改源码、不执行 `git` 提交。

## 5. checklist.md 使用规范

- 由 `plan.md` 的任务项 + `spec.md` 的验收标准逐条生成，**一一对应，不允许合并**。
- 条目必须可客观判定真假。
- 存在未完成条目时**不得声明迭代完成**；确需豁免必须写明理由并获用户确认。
- 每个 FEAT / BUG 的 checklist 必须包含 Playwright 第 ⑥ 步与编号截图勾选项。

## 6. 测试验证报告生成流程

1. 自动化步骤（含 Playwright）全部执行完毕后填写报告。
2. 用 [templates/test-report-template.md](../templates/test-report-template.md) 填充，必须含编号截图表。
3. 报告结论只允许：`通过` / `有条件通过（附遗留项）` / `不通过`。
4. **禁止**在未真实执行的情况下填写通过。
5. 报告与截图随编号目录归档。
