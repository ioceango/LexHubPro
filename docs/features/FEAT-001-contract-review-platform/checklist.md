# FEAT-001 完成度与验证清单

## 功能验收

- [x] 首页展示平台介绍、核心能力、使用流程与上传入口
- [x] 上传页支持 PDF 上传、合同类型与立场选择
- [x] 上传前校验格式与大小，超限不发起 AI 调用
- [x] 审查过程展示分阶段进度
- [x] 报告页展示整体评分、风险条款、缺失条款、合规检查、关键条款
- [x] 风险条款带风险等级与修改建议
- [x] 报告页支持复制、导出、下载原件
- [x] 历史页展示统计概览与报告列表，支持查看与删除
- [x] 报告页展示免责声明文案

## 分层与设计规范

- [x] 审查接口只做计算，不在事务中执行 AI 调用
- [x] 路由层只做入参校验与异常映射，业务逻辑在服务层
- [x] 报告解析逻辑集中在 `lib/review.ts`，页面不重复实现
- [x] 未修改平台托管文件（`core/**`、`models/**`、`main.py`、`lambda_handler.py`、`AuthCallback.tsx`、`index.html`、`.mgx/config.yaml`）

## 数据与隔离

- [x] 新建 `contracts` 与 `review_reports` 数据表
- [x] 新建私有桶 `contracts`，仅持久化对象键
- [x] 落库经 entities 完成，用户数据自动隔离
- [x] 前端未使用 fetch / axios 直连后端

## 前端体验

- [x] 深色专业法务风格设计系统落地
- [x] 认证三态（loading / authenticated / anonymous）避免误判未登录
- [x] 移动端与桌面端布局可正常阅读操作

## 自动化验证

- [x] 后端 `python -m py_compile` 通过
- [x] 前端 `pnpm run lint` 通过
- [x] 前端 `pnpm run build` 通过
- [x] 页面渲染校验通过

## 文档同步

- [x] `.atoms/PROGRESS.md` 已记录交付内容
- [x] `.atoms/ATOMS.md` 已记录关键技术决策
- [x] 本迭代已登记到 `docs/features/README.md`