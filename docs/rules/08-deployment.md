# 08 部署规范

> 主流程：**Docker Compose 自托管**。产品名 LexHubPro。认证为自建 JWT，对象存储为 MinIO。

## 1. Docker Compose

```bash
cp .env.example .env      # 填写 JWT_SECRET_KEY 与 MinIO 凭据
docker compose build
docker compose up -d
```

| 服务 | 说明 |
|------|------|
| `db` | PostgreSQL，卷 `lexhubpro_pgdata` |
| `minio` | S3 兼容对象存储 |
| `minio-init` | 创建私有桶 `contracts` |
| `backend` | FastAPI |
| `frontend` | 静态站点，`/api` 反代后端 |

- JWT 只配 `JWT_SECRET_KEY`（≥32 字符）。
- MinIO 预签名用 `MINIO_PUBLIC_ENDPOINT`。
- 已有 `legalguard_*` 数据卷需手工改名为 `lexhubpro_*` 或在 compose 中覆盖卷名，否则会看到空库。
- 平台内建 AI 网关不可用时，审查需另行提供模型凭据。

## 2. 回滚

回退镜像 tag 后 `docker compose up -d`。数据库回滚依赖备份。含结构变更的发布必须在 `plan.md` 写回滚方案。
