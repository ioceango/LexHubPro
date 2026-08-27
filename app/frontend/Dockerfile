# ==============================================================================
# LexHubPro 前端镜像
# ------------------------------------------------------------------------------
# VITE_ 变量是构建期注入，必须以 build args 形式在此声明并转成环境变量，
# 运行期再改这些变量不会生效（值已被打进产物）。
# ==============================================================================

FROM node:22-alpine AS builder

WORKDIR /app

ARG VITE_APP_NAME
ARG VITE_REVIEW_API_TIMEOUT_MS
ARG VITE_MAX_CONTRACT_FILE_MB
ARG VITE_HISTORY_PAGE_SIZE

ENV VITE_APP_NAME=$VITE_APP_NAME \
    VITE_REVIEW_API_TIMEOUT_MS=$VITE_REVIEW_API_TIMEOUT_MS \
    VITE_MAX_CONTRACT_FILE_MB=$VITE_MAX_CONTRACT_FILE_MB \
    VITE_HISTORY_PAGE_SIZE=$VITE_HISTORY_PAGE_SIZE

ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
# 钉死 pnpm 9：corepack 默认最新版需要 Node 内置 sqlite，在部分镜像上会直接崩
RUN corepack enable && corepack prepare pnpm@9.15.9 --activate

# 锁文件单独成层，源码改动不触发依赖重装
COPY package.json pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile || pnpm install

COPY . .
RUN pnpm run build

# 运行阶段只保留静态产物，不带 node_modules 与源码
FROM nginx:1.27-alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]