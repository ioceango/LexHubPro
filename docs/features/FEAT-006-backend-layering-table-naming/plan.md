# 实现方案：FEAT-006 后端四层与表命名规约

## 1. 技术方案

规约落地后立刻做存量重构：

1. ORM 全部进 `models/`，表名 `tb_*`，表与字段补 comment。
2. 启动时幂等 `ALTER TABLE ... RENAME` 旧名到 `tb_*`，再 `create_all`。
3. 仓储进 `repositories/`，HTTP 进 `api/`，删除 `local_auth/`、`local_data/` 与 `routers/` 业务模块。
4. OIDC 用户表与自建邮箱用户表保持两张（主键类型不同）。

## 2. 改动文件

- 新增：`app/backend/api/__init__.py`、`app/backend/repositories/__init__.py`、本目录四文档
- 修改：`.agent/{constraints,rules,architecture,README}.md`、指针三份、`docs/rules/01/04/06/07`、`docs/README.md`、模板、`.atoms/*`、`main.py`

禁改仍保留：`core/**`、`lambda_handler.py`、`AuthCallback.tsx`、`index.html`、`.mgx/config.yaml`。

## 3. 验证

`bash scripts/verify.sh --docs-only`。本迭代不要求 pytest 覆盖表重命名。

## 4. 回滚

还原上述规约文件与 `main.py` 多出来的一行 include。
