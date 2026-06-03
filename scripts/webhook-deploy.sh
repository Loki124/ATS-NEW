#!/bin/bash
# ATS-New 自动部署脚本
# 由 scripts/webhook.js 触发（push 后）
# 也可手动跑：bash scripts/webhook-deploy.sh

set -e
set -o pipefail

# ===== 配置 =====
DEPLOY_DIR="${DEPLOY_DIR:-/opt/ats/ATS-New}"
REPO_URL="${REPO_URL:-https://gitee.com/loki126/ATS-NEW.git}"
BRANCH="${WEBHOOK_BRANCH:-main}"
APP_PORT="${APP_PORT:-9908}"
LOG_FILE="${LOG_FILE:-/tmp/ats-deploy.log}"
APP_LOG="${APP_LOG:-/home/loki/ats-backend.log}"
APP_PID_FILE="${APP_PID_FILE:-/tmp/ats.pid}"
# =================

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(ts)] $*" | tee -a "$LOG_FILE"; }

mkdir -p "$(dirname "$LOG_FILE")"
mkdir -p "$(dirname "$APP_LOG")"
mkdir -p "$(dirname "$APP_PID_FILE")"

log "================================================"
log " ATS-New 部署开始 (branch=$BRANCH)"
log "================================================"

# ---------- 0. 前置检查 ----------
if [ ! -d "$DEPLOY_DIR" ]; then
  log "❌ $DEPLOY_DIR 不存在，clone 一次"
  mkdir -p "$(dirname "$DEPLOY_DIR")"
  git clone "$REPO_URL" "$DEPLOY_DIR"
fi
cd "$DEPLOY_DIR"

# ---------- 1. git pull ----------
log ""
log "[1/5] git fetch + reset"
git fetch origin "$BRANCH"
git reset --hard "origin/$BRANCH"
HEAD=$(git log --oneline -1)
log "  head: $HEAD"

# ---------- 2. backend deps + prisma ----------
log ""
log "[2/5] backend: npm install + prisma"
cd "$DEPLOY_DIR/backend"
npm install --omit=dev 2>&1 | tail -3 | sed 's/^/  /' | tee -a "$LOG_FILE"
npx prisma generate 2>&1 | tail -3 | sed 's/^/  /' | tee -a "$LOG_FILE"
npx prisma db push --skip-generate --accept-data-loss 2>&1 | tail -3 | sed 's/^/  /' | tee -a "$LOG_FILE"
log "  ✓ backend deps + prisma OK"

# ---------- 3. frontend build ----------
log ""
log "[3/5] frontend: npm install + build"
cd "$DEPLOY_DIR/frontend"
npm install 2>&1 | tail -3 | sed 's/^/  /' | tee -a "$LOG_FILE"
npm run build 2>&1 | tail -3 | sed 's/^/  /' | tee -a "$LOG_FILE"
log "  ✓ frontend build OK"

# ---------- 4. restart Express ----------
log ""
log "[4/5] restart Express on :$APP_PORT"

# 杀老的
OLD_PID=$(cat "$APP_PID_FILE" 2>/dev/null || echo "")
if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
  log "  停老 PID=$OLD_PID (SIGTERM)"
  kill -TERM "$OLD_PID" 2>/dev/null || true
  for i in 1 2 3 4 5; do
    sleep 1
    kill -0 "$OLD_PID" 2>/dev/null || break
  done
  kill -0 "$OLD_PID" 2>/dev/null && {
    log "  老进程不响应，SIGKILL"
    kill -9 "$OLD_PID" 2>/dev/null || true
  }
fi

# 兜底：谁占 APP_PORT 杀谁
PORT_PIDS=$(lsof -ti:$APP_PORT 2>/dev/null || true)
if [ -n "$PORT_PIDS" ]; then
  log "  端口 $APP_PORT 还被占: $PORT_PIDS，kill -9"
  kill -9 $PORT_PIDS 2>/dev/null || true
  sleep 1
fi

# 启动新的
cd "$DEPLOY_DIR/backend"
( nohup node src/app.js > "$APP_LOG" 2>&1 & echo $! > "$APP_PID_FILE" )
sleep 4
NEW_PID=$(cat "$APP_PID_FILE")
log "  新 PID=$NEW_PID"
if ! kill -0 "$NEW_PID" 2>/dev/null; then
  log "  ❌ 新进程没起来，看 log："
  tail -50 "$APP_LOG" | tee -a "$LOG_FILE"
  exit 1
fi

# ---------- 5. verify ----------
log ""
log "[5/5] verify"
if curl -fsS "http://localhost:$APP_PORT/api/health" > /dev/null 2>&1; then
  log "  ✓ /api/health OK"
  curl -fsS "http://localhost:$APP_PORT/api/health" 2>&1 | head -1 | tee -a "$LOG_FILE"
else
  log "  ❌ /api/health 失败"
  tail -50 "$APP_LOG" | tee -a "$LOG_FILE"
  exit 1
fi

if curl -fsSI "http://localhost:$APP_PORT/" 2>/dev/null | head -1 | grep -q "200"; then
  log "  ✓ 静态首页 200"
else
  log "  ⚠ 静态首页没起（可能没 build）"
fi

log ""
log "================================================"
log " 🎉 部署完成"
log "   公网: https://ats.lokisong.cloud"
log "   PID:  $NEW_PID"
log "   log:  $APP_LOG"
log "================================================"
