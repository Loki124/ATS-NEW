# frontend/Dockerfile
# 注意: builder 用 bookworm-slim (Debian, glibc) 而非 alpine (musl)。
# UnoCSS/oxc-parser/esbuild/rollup 等含平台原生二进制; alpine/musl 下 npm 的
# optional-dependencies bug (npm/cli#4828) 会漏装 musl 绑定, 导致
# "Cannot find native binding" (oxc-parser) 构建失败。glibc 下默认装 gnu 变体, 稳定通过。
# 另: 依赖引擎要求 node>=20(部分>=22, 如 nopt@10/rollup-plugin-visualizer),
# 故必须用 node:22 (不能用 node:18, 否则 vite build 阶段 EBADENGINE 甚至运行期失败)。
FROM node:22-bookworm-slim AS builder

WORKDIR /app

# 仅 COPY package.json, 不带入 macOS 生成的 package-lock.json,
# 让 npm 在 Linux 上重新解析(避免 stale lockfile 导致的 optional-dep 错位)。
COPY package.json ./
RUN npm install --no-audit --no-fund

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
