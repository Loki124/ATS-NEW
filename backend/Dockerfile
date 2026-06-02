# backend/Dockerfile
FROM node:18-bullseye-slim

WORKDIR /app

# 安装 Prisma engine 所需的运行时依赖 (libssl 1.1 + 基础工具 + MySQL 客户端)
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssl \
    ca-certificates \
    curl \
    default-mysql-client \
    && rm -rf /var/lib/apt/lists/*

# 先复制 package.json 安装依赖
COPY package*.json ./
RUN npm install --production

# 复制 Prisma schema 并生成 client
COPY prisma ./prisma
RUN npx prisma generate

# 最后复制剩余的应用代码（node_modules 已在 .dockerignore 中排除）
COPY . .

# 复制并设置启动脚本（避开 node 基础镜像自带的 /usr/local/bin/docker-entrypoint.sh）
COPY ats-entrypoint.sh /usr/local/bin/ats-entrypoint.sh
RUN chmod +x /usr/local/bin/ats-entrypoint.sh

# 在容器内对 prisma client 做最后兜底生成（避免缓存层错位）
RUN npx prisma generate || true

EXPOSE 5125

# 启动时自动同步 schema + 跑种子
ENTRYPOINT ["/usr/local/bin/ats-entrypoint.sh"]
CMD ["node", "src/app.js"]