# Plan：FEAT-010 前端资源与结构

## 基本信息

| 项 | 内容 |
|----|------|
| 迭代号 | FEAT-010-frontend-assets-mvc |
| 确认状态 | ✅ 已确认（用户指定范围，2026-08-28） |

## 1. 方案

根因：`lib/assets.ts` 指向平台 CDN，本地 PNG 未参与构建。迁到 `app/frontend/src/assets/images/`，用 cwebp 压成 WebP 后由 Vite 导入（带 hash，走 `/assets/` 长期缓存）。首屏 Logo `fetchPriority=high`，下方图 `loading=lazy`。

脚手架：去掉 blog 预渲染、Atoms sitemap、未引用的 shadcn 文件、`src/api/settings.ts`。Vite 只保留 React 插件与精简 chunk。

MVC 映射写入 `.agent/architecture.md`，不新建 `mvc/` 目录。

## 2. 文件

新增：`src/assets/images/*.webp`、`public/favicon.webp`  
修改：`lib/assets.ts`、`Index.tsx`、`SiteHeader`/`AuthCard`、`vite.config.ts`、`index.html`、`main.tsx`、`App.tsx`  
删除：仓库根 `assets/`、blog/prerender、未用 `components/ui/*`、`src/api/settings.ts`

## 3. 无数据库变更
