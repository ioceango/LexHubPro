# 完成清单：FEAT-004 跨工具统一 `.agent/` 规约

## 前置调研

- [x] 联网核实 Codex 的 `AGENTS.md` 加载机制（逐层合并、深层覆盖、`AGENTS.override.md` 优先、32 KiB 上限）
- [x] 联网核实 DeepSeek harness (dsh) 是否有官方仓库指令文件约定（结论：未见公开约定）
- [x] 确认不为 dsh 臆造入口格式，采用通用根 `AGENTS.md` 兜底
- [x] 读取 `.atoms/ARCHITECTURE.md`、现有 `AGENTS.md`、`scripts/verify.sh`，界定复用与去重边界

## `.agent/` 规约建设

- [x] `.agent/README.md`：单一事实源声明 + 阅读顺序 + 工具入口映射 + 与 `.atoms/` 关系与同步责任
- [x] `.agent/workflow.md`：强制流程与双确认门、编号目录规范、取号方法、各文档职责、Bug 附加要求
- [x] `.agent/constraints.md`：禁改清单、平台能力边界、配置读取、日志脱敏、业务硬约束、视觉规范、交付诚实性
- [x] `.agent/rules.md`：分层职责、量化阈值、内聚耦合、禁止堆砌、导入约束、结构化输出、异常处理、注释命名、测试
- [x] `.agent/architecture.md`：系统概览、技术栈、模块职责表、关键决策、扩展指引
- [x] `.agent/verification.md`：验证顺序、门禁判定项、测试要求、完成定义
- [x] 内容为强指令式（必须/禁止/校验方式），非 `.atoms/` 原文搬运
- [x] 六份文件职责单一，未出现互相重复的规则正文

## 工具入口指针化

- [x] `AGENTS.md` 重写为指针（Grok / Codex / dsh / Cursor 等通用入口）
- [x] `CLAUDE.md` 重写为指针（Claude 系工具）
- [x] `.grok/rules/00-legalguard-rules.md` 重写为指针（Grok build / Grok CLI）
- [x] 三份指针均只含必读清单 + 红线摘要 + 验证入口 + 维护规则，不含完整规则正文
- [x] 三份指针均显式包含 `.agent/` 路径引用
- [x] 三份指针均写明「规约变更只改 `.agent/`，禁止在指针内新增或改写规则」

## 门禁扩展

- [x] `scripts/verify.sh` 新增 `.agent/` 六份必需文件存在性与非空校验
- [x] `scripts/verify.sh` 新增三份工具指针的存在性、非空、指向 `.agent/` 校验
- [x] 复用既有问题汇总机制，所有问题项一次性输出
- [x] 脚本头部职责说明同步更新
- [x] 未引入新外部依赖，脚本仍不修改源码、不执行版本控制操作、不访问网络

## 非侵入性

- [x] 未改动任何业务代码与页面逻辑
- [x] 未变更技术栈、接口契约、数据库结构
- [x] 未修改禁改清单中的任何文件
- [x] 本迭代无配置项变更，`.env.example` 无需改动

## 自动化验证

- [x] `bash -n scripts/verify.sh` 通过
- [x] 门禁能正确识别 `.agent/` 六份规约与三份指针（输出 6/6、3/3）
- [x] 文档齐备时 `bash scripts/verify.sh --docs-only` 退出码 0
- [x] 缺失 `.agent/` 单个规约文件时门禁非零退出并指出缺失项
- [x] `.agent/` 目录整体缺失时门禁非零退出并指出目录缺失
- [x] 指针文件不指向 `.agent/` 时门禁非零退出并指出该问题
- [x] 反向验证后现场完全恢复，复跑门禁退出码 0
- [x] 前端 `pnpm run lint` 通过
- [x] 前端 `pnpm run build` 通过

## 文档同步

- [x] `docs/features/README.md` 已登记 FEAT-004 并更新下一个可用编号
- [x] `.atoms/ATOMS.md` 已新增「`.agent/` 为跨工具规约单一事实源」决策
- [x] `.atoms/PROGRESS.md` 已记录本次改造

## 已知未覆盖项（见测试报告遗留风险）

- 门禁的「指针文件为空」分支未单独构造实测场景（与缺失分支同一检查路径）
- dsh 若后续公布官方入口约定，需新增一份指向 `.agent/` 的指针文件并纳入门禁清单