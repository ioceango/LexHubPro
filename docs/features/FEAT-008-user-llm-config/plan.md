# Plan：用户自备 DeepSeek / OpenRouter 模型配置

## 基本信息

| 项 | 内容 |
|----|------|
| 迭代号 | FEAT-008-user-llm-config |
| 对应 Spec | `./spec.md` |
| 预估工作量 | 1 个工作日量级 |
| 确认状态 | ✅ 已确认（用户要求开始实施，2026-08-27） |

## 1. 方案概述

审查不再使用平台 `APP_AI_*` / 写死的 `claude-opus-5`。每个登录用户自己保存 DeepSeek 或 OpenRouter 的 API Key（库内对称加密，只回显末四位），拉取目录后把模型加入列表。**同一用户 `enabled=true` 至多一条**（跨提供商）；启用新模型时把其余全部关掉。`/api/v1/review/analyze` 只使用当前这一条启用模型。未启用则 409，前端审查页先拦。

文字提取仍 PyMuPDF 优先；扫描件不再走原 `analyze_pdf` 平台能力，直接 422。

### 备选方案对比

| 方案 | 优点 | 缺点 | 是否采用 |
|------|------|------|----------|
| A：用户级 Key + 互斥启用一个模型 | 与「自己的模型」一致，隔离清晰 | 每人自己充值 | ✅ |
| B：环境变量全局一套 Key | 实现少 | 无法按用户、无法选模型、密钥在运维侧 | ❌ |
| C：审查时前端直连提供商 | 后端不碰 Key | Key 暴露在浏览器、无法统一埋点与超时 | ❌ |

## 2. 架构与分层落点

### 2.1 后端

| 层 | 文件 | 改动 | 职责 |
|----|------|------|------|
| models | `app/backend/models/user_llm.py` | 新增 | `tb_user_llm_provider`、`tb_user_llm_model`，含 COMMENT |
| repositories | `app/backend/repositories/user_llm.py` | 新增 | 按 tenant_id+user_id 读写 |
| services | `app/backend/services/user_llm.py` | 新增 | 只编排：存 Key、互斥启用、解析当前启用模型。**不**直接 import 某家 SDK URL |
| llm_providers | `app/backend/llm_providers/` | 新增包 | 提供商端口 + 注册表 + 各厂商适配器，见 §2.4 |
| services | `app/backend/services/contract_review.py` | 修改 | gentxt 使用传入的 model + invoker；去掉写死 REVIEW_MODEL |
| services | `app/backend/services/ai_invoker.py` | 修改 | 支持注入「按用户凭据的客户端」；配置错误文案改为请检查自己的 Key |
| api | `app/backend/api/user_llm.py` | 新增 | `/api/v1/llm/*` |
| api | `app/backend/api/contract_review.py` | 修改 | 无启用模型 → 409；有则注入用户 invoker |
| schemas | `app/backend/schemas/user_llm.py` | 新增 | 入参出参，Key 只出 suffix |
| utils | `app/backend/utils/secret_box.py` | 新增 | Fernet，密钥由 `JWT_SECRET_KEY` SHA-256 派生 |
| tests | `app/backend/tests/test_user_llm.py` | 新增 | mock 提供商 HTTP，禁止真实 Key 出网 |

### 2.2 前端

| 层 | 文件 | 改动 | 职责 |
|----|------|------|------|
| page | `pages/ModelSettings.tsx` | 新增 | 按 `GET /llm/providers` 动态渲染卡片（填 Key、拉取、加入、单选启用），不写死厂商列表 |
| lib | `lib/user-llm.ts` | 新增 | 走 `localRequest` 的 API 封装 |
| page | `pages/Review.tsx` | 修改 | 进入时拉 active；无则横幅+禁用提交；409 跳配置 |
| App | `App.tsx` | 修改 | 路由 `/settings/models` |
| nav | `components/SiteHeader.tsx` | 修改 | 「模型配置」入口（登录后） |

### 2.3 禁改自查

- 不改 `core/config.py` 类定义以外的平台禁区；不改 `AuthCallback.tsx`、`index.html`
- 前端禁止页面内散落 `fetch` 调提供商（拉模型必须后端代理，避免 Key 二次暴露）

### 2.4 提供商扩展（强制）

对齐现有 `auth_providers/`：端口 + 注册表 + 单文件适配器。审查与用户配置服务只依赖端口，不出现 `if provider == "deepseek"`。

```
app/backend/llm_providers/
  base.py           # LlmProvider 协议：provider_id / display_name / base_url / extra_headers()
                    # list_models(api_key) -> [{id, name}]
                    # 不负责落库、不负责启用互斥
  registry.py       # register() / get(id) / all_ids()；未知 id 抛领域错误
  deepseek.py       # 仅 DeepSeek：https://api.deepseek.com ，GET /models
  openrouter.py     # 仅 OpenRouter：https://openrouter.ai/api/v1 + Referer/Title
```

Chat Completions 走统一 OpenAI 兼容客户端（`base_url` + `extra_headers` 由适配器提供），不在每个适配器里复制一份 `chat.completions` 编排。若某后续厂商不兼容 OpenAI 协议，再为该适配器实现可选 `complete()`；本迭代两家都兼容，完整实现放在共享 `openai_compat.py`（只做 HTTP 调用，不做业务判断）。

**新增一家提供商的改动面（目标 ≤ 这些，禁止改审查主流程）：**

1. 新增 `llm_providers/<slug>.py` 实现 `LlmProvider`
2. 在 `registry` 注册
3. 前端配置页已按 `GET /llm/providers` 动态渲染，原则上零改或只加展示名/说明文案

**禁止**

- 在 `contract_review.py` / `api/contract_review.py` / `user_llm.py` 按厂商名分支
- 把两家 URL 写进环境变量强迫运维改（厂商 URL 是适配器常量）
- `tb_user_llm_provider.provider` 用过死的 CHECK 绑死两家——用 `String(32)` + 应用层校验「必须在 registry 内」，以免加厂商还要改 DDL

`user_llm` 单一职责：用户凭据与「同时只启用一个」的领域规则。  
`llm_providers` 单一职责：怎么跟某一家 HTTP 说话。  
`secret_box` 单一职责：加解密。  
`ai_invoker` 单一职责：埋点、分类、重试。  
`contract_review` 单一职责：抽文本 + 结构化审查。

## 3. 接口契约

提供商 id 以 **registry 为准**（本迭代注册 `deepseek`、`openrouter`）。未知 id → 400。

各适配器内固定 Base URL（不配进用户表、不写进审查服务）：

- DeepSeek：`https://api.deepseek.com`
- OpenRouter：`https://openrouter.ai/api/v1`（`HTTP-Referer` / `X-Title: LexHubPro`）

### `GET /api/v1/llm/providers`

鉴权。响应：`[{ "provider", "name", "configured", "key_suffix" }]`

### `PUT /api/v1/llm/providers/{provider}/key`

请求：`{ "api_key": "..." }`  
响应：`{ "configured": true, "key_suffix": "xxxx" }`  
400 空/占位；401 未登录。

### `DELETE /api/v1/llm/providers/{provider}/key`

删除该提供商 Key 及其下已选模型。

### `POST /api/v1/llm/providers/{provider}/models/refresh`

用已存 Key 请求提供商 `GET /models`（事务外）。  
200：`{ "items": [{ "id", "name" }] }`  
401/400：密钥无效；503：提供商繁忙。

### `GET /api/v1/llm/models`

当前用户已选模型：`[{ "id", "provider", "model_id", "display_name", "enabled" }]`  
同一用户至多一条 `enabled=true`。

### `PUT /api/v1/llm/models`

`{ "provider", "model_id", "display_name?", "enabled" }`  
`enabled=true` 时该用户其他模型全部 `enabled=false`（同一事务）。

### `PATCH /api/v1/llm/models/{id}`

`{ "enabled" }`  
启用时同样互斥关闭其余。

### `GET /api/v1/llm/active`

`{ "configured": false }` 或 `{ "configured": true, "provider", "model_id", "display_name" }`

### 审查 `POST /api/v1/review/analyze`

无启用模型 → **409**，`detail=请先配置并启用一个审查模型`。  
有启用模型 → 用该用户解密 Key + 提供商 Base URL 调用 chat.completions，`model=model_id`。

## 4. 数据库变更

| 表 | 变更 | 注释与约束 | 兼容 | 回滚 |
|----|------|------------|------|------|
| `tb_user_llm_provider` | 新增 | 用户在某提供商下的加密 Key。唯一 `(tenant_id, user_id, provider)`。`provider` 为短字符串，合法值由 registry 校验，**不加写死两家的 CHECK** | 是 | DROP TABLE |
| `tb_user_llm_model` | 新增 | 用户勾选的模型。唯一 `(tenant_id, user_id, provider, model_id)`。`enabled` 布尔。部分唯一索引：同一 `(tenant_id, user_id)` 下 `enabled=true` 至多一行 | 是 | DROP TABLE |

字段均 `comment=`，DDL `COMMENT ON TABLE/COLUMN`。不存明文 Key。可存 `key_suffix`（最多 8 字符）便于 UI。

加密：`utils/secret_box.py`，Fernet key = SHA256(JWT_SECRET_KEY) 的 urlsafe_base64。轮换 JWT 会导致旧 Key 无法解密，需用户重填——plan 接受并在配置页提示「更换系统密钥后请重填 API Key」。

## 5. 审查调用链（改后）

```
analyze API
  → 读 active 模型（短读，无事务跨网）
  → 无则 409
  → MinIO 取 PDF → PyMuPDF
  → 文本不足 → 422 请上传文字版 PDF
  → Chat Completions（用户 Key，当前启用 model_id）结构化 JSON
  → 短事务写报告
```

`AIInvoker` 增加可注入的 `completion_fn` 或 `UserModelClient`，避免审查再走 `APP_AI_KEY`。

## 6. 前端交互

1. `/settings/models`：两张卡片（DeepSeek / OpenRouter）。
2. 输入框 type=password + 显示切换；保存后输入框清空，展示 `已保存 · ****abcd`。
3. 「拉取模型」→ 多选列表；「加入我的模型」。
4. 「我的模型」表格：启用用 **radio / 互斥开关**（不是多选 checkbox）。启用 B 即关闭 A。允许全部关闭。
5. `/review`：`GET /llm/active`，`configured=false` 时 Alert + 按钮「去配置模型」，主按钮 disabled。
6. 视觉遵循 `.agent/design.md`（outline 按钮透明底）。

## 7. 测试

- pytest mock httpx/openai：保存 Key 不回明文；refresh 401；启用第二条时第一条自动关闭；无启用时 analyze 409；有启用时 gentxt 使用该 model_id。
- 禁止测试打真实 DeepSeek/OpenRouter。
- Playwright：未配置审查拦截（S01）；配置页两提供商（S02）；无 Key 拉模型失败提示（S03）；mock 或测试桩拉列表后启用其中一个（若 e2e 无真实 Key，后端测为主）。优先：审查页拦截不依赖真实 Key。

## 8. 风险与回滚

| 风险 | 缓解 |
|------|------|
| 用户 Key 泄露进日志 | 统一脱敏；禁止 print request headers |
| JWT 轮换导致 Key 无法解密 | 配置页提示重填 |
| OpenRouter 模型极多 | 前端搜索过滤，不分页也可先截断展示 200 + 搜索 |
| 扫描件不可审 | spec 已声明；文案写清 |

回滚：停用 `/llm` 路由并恢复审查走 `APP_AI_*`（不推荐）；或仅停前端入口。

## 9. 请确认

确认 spec 与本 plan 后开始编码。已纳入：同一用户只能启用一个模型；提供商以注册表扩展，审查编排不写死厂商。
