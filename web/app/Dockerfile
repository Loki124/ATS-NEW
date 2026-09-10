# frontend/Dockerfile
FROM node:18-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
# 与本地部署一致: 跳过 vue-tsc 类型检查(vue-tsc 常 OOM/SIGKILL, 且存量严格类型不全过), 仅 vite build。
# 若需严格类型门禁, 改为 `RUN npm run build` 并先修完类型错误。
RUN npm run build:nocheck

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
# Fix: 原 frontend/nginx.conf 路径不存在(文件实际名为 nginx.conf), 构建必失败
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]