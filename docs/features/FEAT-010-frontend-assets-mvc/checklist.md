# Checklist：FEAT-010

| 项 | 内容 |
|----|------|
| 迭代号 | FEAT-010-frontend-assets-mvc |
| 最后更新 | 2026-08-28 |

| 编号 | 验证项 | 状态 | 证据 |
|------|--------|------|------|
| AC-01 | 资源在前端目录 | ✅ | `src/assets/images/*.webp` |
| AC-02 | 无 CDN 图 URL | ✅ | grep 源码为空；e2e |
| AC-03 | 懒加载与体积 | ✅ | hero 57KB；lazy 属性 |
| AC-04 | 无 blog 脚手架 | ✅ | 已删 prerender/blog |
| AC-05 | 架构 MVC 映射 | ✅ | architecture §4.1 |
| AC-06 | Playwright | ✅ | S01–S02 |
