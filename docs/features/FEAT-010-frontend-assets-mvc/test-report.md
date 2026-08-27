# 测试验证报告：FEAT-010

## 1. 报告信息

| 项 | 内容 |
|----|------|
| 迭代号 | FEAT-010-frontend-assets-mvc |
| 执行日期 | 2026-08-28 |
| 结论 | ✅ 通过 |

## 2. 自动化

| 步骤 | 命令 | 退出码 | 摘要 |
|------|------|--------|------|
| 文档 gate | `bash scripts/verify.sh --docs-only` | 0 | 10 个 FEAT |
| eslint | `eslint --quiet ./src` | 0 | |
| vite build | `vite build` | 0 | hero.webp 57KB、logo 6KB 打进 dist/assets |
| Playwright | `playwright test e2e/frontend-assets.spec.ts` | 0 | 1 passed；无 metadl CDN 请求 |
| Docker | `docker compose up -d --build frontend` | 0 | healthy |

未跑全量 pytest（本迭代无后端行为变更）。

## 3. 编号截图

| 编号 | 文件 | 覆盖 AC | 说明 |
|------|------|---------|------|
| S01 | [test-report/S01-home-local-images.png](./test-report/S01-home-local-images.png) | AC-02 / AC-03 / AC-06 | 首页 Logo 与主图同源加载 |
| S02 | [test-report/S02-login-local-logo.png](./test-report/S02-login-local-logo.png) | AC-02 / AC-06 | 登录页本地 Logo |

## 4. 验收

| 编号 | 结论 | 证据 |
|------|------|------|
| AC-01 | ✅ | `app/frontend/src/assets/images/*.webp`；根 `assets/` 已删除 |
| AC-02 | ✅ | 源码无 CDN URL；e2e 监听无 metadl 请求 |
| AC-03 | ✅ | 构建产物 WebP；首页主图 fetchPriority、下方 loading=lazy |
| AC-04 | ✅ | 已删 blog/prerender |
| AC-05 | ✅ | `.agent/architecture.md` §4.1 |
| AC-06 | ✅ | S01–S02 |

## 5. 结论

品牌图改为前端打包的压缩 WebP，加载不再依赖平台 CDN。前端按 pages/hooks/lib 对应 MVC。
