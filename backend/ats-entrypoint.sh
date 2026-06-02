#!/bin/sh
# backend/docker-entrypoint.sh
# 启动时自动同步 Prisma schema 并跑种子数据（幂等），然后启动 Node 应用

set -e

echo "🔄 [entrypoint] 同步 Prisma schema 到数据库..."
npx prisma db push --skip-generate --accept-data-loss 2>&1 || {
  echo "❌ Prisma db push 失败"
  exit 1
}

# 仅在 users 表为空时执行种子（首次启动）
USER_COUNT=$(node -e "
const { PrismaClient } = require('@prisma/client');
const p = new PrismaClient();
p.user.count().then(c => { console.log(c); p.\$disconnect(); }).catch(e => { console.log(-1); p.\$disconnect(); });
" 2>/dev/null || echo -1)

if [ "$USER_COUNT" = "0" ]; then
  echo "🌱 [entrypoint] users 表为空，执行种子..."
  if [ -f prisma/seed/user.seed.cjs ]; then
    node prisma/seed/user.seed.cjs 2>&1 || echo "⚠️  user.seed 失败"
  fi
  if [ -f prisma/seed/permission.seed.cjs ]; then
    node prisma/seed/permission.seed.cjs 2>&1 || echo "⚠️  permission.seed 失败"
  fi
else
  echo "✅ [entrypoint] users 已有 $USER_COUNT 条记录，跳过种子"
fi

echo "🚀 [entrypoint] 启动 Node 应用..."
exec "$@"
