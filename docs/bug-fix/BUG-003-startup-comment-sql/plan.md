# Plan：BUG-003

## 1. 方案

把 COMMENT 文案做 SQL 字面量转义（`'` → `''`）后拼进语句，禁止 `:c` / `$1`。标识符仅允许 `tb_*` 与列名 `[a-z0-9_]+`。

compose：backend 健康检查改为 `/api/v1/health`（含数据库探测）；frontend 增加对本机 80 端口的 healthcheck。

## 2. 改动

- `app/backend/services/schema_bootstrap.py`
- `app/backend/api/health.py`
- `docker-compose.yml`
- `app/backend/tests/test_schema_bootstrap.py`（新增，BUG-003 回归）

## 3. 回滚

还原上述文件并重建 backend 镜像。
