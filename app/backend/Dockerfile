# ==============================================================================
# LexHubPro 后端镜像
# ------------------------------------------------------------------------------
# 启动命令走 entrypoint.py 而非直接 uvicorn：自托管形态必须先完成
# 配置自检与幂等建表，配置错误要在启动阶段暴露，而不是等第一个用户请求失败。
# ==============================================================================

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 编译 asyncpg / argon2 等依赖需要 gcc；装完即删，避免留在运行镜像里增大体积与攻击面
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 依赖单独成层：源码变更时不必重新安装依赖
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove gcc

COPY . .

# 日志目录需提前建好：应用启动时若目录缺失会直接报错
RUN mkdir -p /app/logs

EXPOSE 8000

CMD ["python", "entrypoint.py"]