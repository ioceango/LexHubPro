# BUG-003 启动 COMMENT ON 绑定参数导致进程崩溃

## 1. 基本信息

| 项 | 内容 |
|----|------|
| 编号 | BUG-003 |
| 类型 | Bug |
| 严重级别 | 阻塞 |
| 日期 | 2026-08-27 |
| 状态 | 修复中 |
| 确认 | 用户要求排查修复并做部署健康检查 |

## 2. 复现

`docker compose up -d` 后 `lexhubpro-backend` 持续 Restarting，frontend 停在 Created。

日志：`syntax error at or near "$1"`，SQL 为 `COMMENT ON TABLE tb_auth_audit IS $1`。

## 3. 根因

`schema_bootstrap._apply_comments` 用 SQLAlchemy 绑定参数写 `COMMENT ON ... IS :c`。PostgreSQL 的 `COMMENT ON` 不接受参数占位符，必须是字符串字面量。进程在建表引导阶段退出，compose 的 backend healthcheck（`/health`）永远达不到 healthy，frontend `depends_on: service_healthy` 无法启动。

## 4. 期望

- 启动能完成 COMMENT ON，进程保持运行。
- 各长期服务有健康检查；backend 就绪后再起 frontend。
- 回归用例锁住「COMMENT SQL 不得含绑定占位符」。
