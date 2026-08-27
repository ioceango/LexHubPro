# 03 配置管理规范

> 核心原则：**一切可变的东西都是配置，一切配置都有默认值、有说明、有归属层级；业务代码里出现第二个魔法值即为缺陷。**

## 1. 配置读取机制（本项目实况）

### 1.1 后端

`app/backend/core/config.py` 中的 `Settings` 基于 `pydantic-settings`，并实现了 `__getattr__` 动态回退：访问 `settings.foo_bar` 会自动读取环境变量 `FOO_BAR`，**若环境变量不存在则抛 `AttributeError`**。

这带来一条必须遵守的铁律：

```python
# ❌ 危险：变量未注入时抛 AttributeError，被框架转成 500（登出接口曾因此报 500）
base_url = settings.frontend_url

# ✅ 正确：显式默认值 + 占位符校验 + 降级
raw = getattr(settings, "frontend_url", "") or ""
if not raw or raw.startswith("$$"):          # 平台占位符未被替换
    raw = fallback_from_request(request)      # 降级并记 WARNING
```

**规则**：
1. 读取动态配置**必须**使用 `getattr(settings, name, default)`，禁止裸属性访问。
2. 必须校验「占位符未替换」情形（形如 `$$XXX$$`），命中即降级并记 `WARNING`（见 02 §4.3）。
3. 关键配置缺失若无法降级，应在启动或首次使用时明确报错（`CRITICAL`），不得静默 500。
4. 模块级配置通过环境变量 + `getattr` 读取。JWT 只认 `JWT_SECRET_KEY`。

### 1.2 前端

- 只允许通过 `import.meta.env.VITE_*` 读取构建期配置，并统一在 `src/lib/config.ts` 集中导出，页面/组件禁止直接读 `import.meta.env`。
- **前端配置一律视为公开信息**：任何密钥、token、私有端点禁止放入 `VITE_*`。需要密钥的能力必须走后端自定义 API。
- 前端经同源 `/api` 反代访问后端，**禁止在页面里硬编码 API host**。

## 2. 禁止硬编码清单

以下值出现在业务代码中即为缺陷，必须提为常量（同一模块内固定）或配置项（跨环境可变）：

| 类别 | 反例 | 正确做法 |
|------|------|----------|
| 服务地址 / 回调地址 | `"https://xxx.mgx.dev/logout-callback"` | 由 `FRONTEND_URL` + 常量路径拼接，带请求 host 降级 |
| 超时时间 | `invoke(..., { timeout: 600000 })` 散落各处 | `src/lib/config.ts` 导出 `REVIEW_API_TIMEOUT_MS` |
| 文件限额 | `22 * 1024 * 1024` 内联 | `MAX_PDF_DATA_URI_LENGTH` 常量 + `MAX_CONTRACT_FILE_MB` 配置 |
| AI 模型名 | `"claude-opus-5"` 或平台默认模型硬编码 | 审查只用用户当前启用的一个 DeepSeek / OpenRouter 模型（FEAT-008）；无启用模型则拒绝审查，无平台兜底 |
| 采样参数 | `temperature=0.2` 内联 | 常量 `REVIEW_TEMPERATURE` |
| 桶名 | `"contracts"` 多处字符串 | `CONTRACT_BUCKET` 常量 |
| 分页大小 / 重试次数 | `limit=50`、`range(3)` | 具名常量或配置项 |
| 文案与状态枚举 | 散落中文字符串比较 | 集中在 `lib/review.ts` 的常量与类型 |

判定标准：**同一字面量在项目中出现 ≥ 2 次，或它在不同环境需要不同取值 → 必须外提。**

## 3. 配置项清单

### 3.1 平台注入（禁止覆盖 / 禁止写入自建 `.env`）

自托管通过环境变量注入，清单见 `.env.example`。必填项包括 `DATABASE_URL`、`JWT_SECRET_KEY`、`MINIO_ENDPOINT` / `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY`。

### 3.2 应用可配置项（写入 `.env.example`）

见项目根目录 `.env.example`，每项均标注含义、默认值、是否必填。新增配置必须**同步**更新：`.env.example` → 本文档 → 使用处的 `getattr` 默认值。

认证与 MinIO 项写入 `.env.example`。JWT 只使用 `JWT_SECRET_KEY`。

## 4. `.env` 管理规则

1. `.env.example` 必须提交仓库并保持与代码同步；`.env` **禁止提交**（已在 `.gitignore` 覆盖，新增变体如 `.env.local` 需一并忽略）。
2. `.env.example` 中**只能放示例值/占位符**，禁止任何真实密钥。
3. 变量命名：`UPPER_SNAKE_CASE`；前端专用一律 `VITE_` 前缀；布尔用 `true` / `false`；时间统一以毫秒（`*_MS`）或秒（`*_SECONDS`）显式结尾；容量以 `*_MB` 结尾。
4. 配置**分级优先级**：进程环境变量 > `.env` > 代码默认值。默认值必须能让服务以「功能降级但不崩溃」的方式启动。
5. 删除配置项前必须全局搜索确认无引用（`Editor.grep`），并在 `plan.md` 记录影响面。
6. 平台 Publish 场景下，密钥通过平台密钥管理注入，**不通过 `.env` 传递**；`.env` 主要服务于本地开发与 Docker Compose 自托管。

## 5. 变更流程

任何配置项新增/修改必须在迭代文档中留痕：

1. `spec.md`：说明为什么需要该配置（哪个环境差异或哪个可调参数）。
2. `plan.md`：给出变量名、类型、默认值、是否必填、读取位置、降级策略。
3. 代码：`getattr(settings, ...)` + 默认值 + 占位符校验 + `WARNING` 日志。
4. `.env.example`：新增条目与注释。
5. `checklist.md`：勾选「配置项已文档化」「缺失该变量时服务可降级启动」两项验证。