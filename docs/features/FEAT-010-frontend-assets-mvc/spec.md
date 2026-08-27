# Spec：前端资源迁移、图片加载与结构清理

## 基本信息

| 项 | 内容 |
|----|------|
| 迭代号 | FEAT-010-frontend-assets-mvc |
| 类型 | 需求 |
| 优先级 | P1 |
| 提出人 | 用户 |
| 创建日期 | 2026-08-28 |
| 确认状态 | ✅ 已确认（用户指定 feat 范围，2026-08-28） |

## 1. 背景与问题

品牌图放在仓库根 `assets/`，前端却从平台 CDN 拉 1–2MB 的 PNG，首页和 Logo 加载慢。前端还留着 blog 预渲染、大量未用 UI、对已删除的 admin settings 的调用。分层需要按既有 pages/hooks/lib 对齐 MVC，而不是再开一套目录。

## 2. 范围

### 2.1 本次要做

- 把 `assets/` 迁到前端资源目录，页面只加载同源压缩图。
- 优化加载：压缩体积、首屏 Logo/主图优先、非首屏懒加载。
- 去掉 blog 预渲染、Atoms sitemap 主机名、未用脚手架组件与已删除后端对应的 settings API 封装。
- 在架构规约写清前端 MVC 对应关系：pages/components=View，hooks=Controller，lib=Model，assets=静态资源。

### 2.2 本次明确不做

- 不把 schemas 与 models 那套后端分层搬到前端另开 `mvc/` 目录。
- 不改审查、登录、模型配置业务语义。
- 不新增 npm 图片插件（用现有 cwebp + Vite 资源导入）。
- 不在本迭代清理 pnpm lock 里未引用的 radix 包（避免 lockfile 策略失败）。

## 3. 用户故事

- 作为访客，我希望首页图立刻从本站加载且体积小，以便快速看到产品。
- 作为维护者，我希望图片和页面代码都在 `app/frontend`，分层能对上 MVC。

## 4. 功能需求

| 编号 | 需求 | 期望 |
|------|------|------|
| F-01 | 品牌图在前端目录 | 根目录不再作为运行时资源源 |
| F-02 | 页面使用本地图 | 不再请求 metadl/mgx CDN 图片 |
| F-03 | 体积与加载策略 | Logo/主图优先；能力区图懒加载 |
| F-04 | 去掉 blog 脚手架 | 无 blog 路由、无 prerender 博客 |
| F-05 | 架构文档 | 前端 MVC 映射可查 |

## 5. 验收标准

- [ ] AC-01：`app/frontend/src/assets/` 含品牌图；根 `assets/` 不再被前端引用。
- [ ] AC-02：源码中无 `mgx-backend-cdn` / `metadl.com` 图片 URL。
- [ ] AC-03：构建产物含本地图；首页 img 有宽高与懒加载策略。
- [ ] AC-04：无 blog 预渲染入口；`/logout-callback` 仍无 OIDC 页。
- [ ] AC-05：architecture 写明前端 MVC 对应目录。
- [ ] AC-06：Playwright 首页可见 Logo/主图，截图 S01 起。

## 6. 影响面

| 维度 | 影响 |
|------|------|
| 页面 | 首页、页头、登录卡片 Logo |
| 接口 | 无 |
| 数据结构 | 无 |
