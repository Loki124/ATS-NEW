# backend/Dockerfile
FROM node:18-bullseye-slim

WORKDIR /app

# 安装 Prisma engine 所需的运行时依赖 (libssl 1.1 + 基础工具)
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssl \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 先复制 package.json 安装依赖
COPY package*.json ./
RUN npm install --production

# 复制 Prisma schema 并生成 client
COPY prisma ./prisma
RUN npx prisma generate

# 最后复制剩余的应用代码（node_modules 已在 .dockerignore 中排除）
COPY . .

# 在容器内对 prisma client 做最后兜底生成（避免缓存层错位）
RUN npx prisma generate || true

EXPOSE 5125

# 启动后端
CMD ["node", "src/app.js"]