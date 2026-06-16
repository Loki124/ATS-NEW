#!/bin/bash
# ATS-New 自动部署脚本 (P1-6 同步: 适配 Django 5.x + Vite 新结构)
#
# 由 scripts/webhook.js 触发（push 后）
# 也可手动跑：bash scripts/webhook-deploy.sh
#
# 新目录结构（2026-06 重构后）:
#   ATS-New/apps/django/   <- Python 后端 (Django 5.x + DRF + Celery + Channels)
#   ATS-New/web/app/       <- 前端 (Vite + Vue 3)
#   ATS-New/ops/           <- docker-compose / nginx 配置
#
# 兼容: 若 DEPLOY_DIR/backend 目录存在（Node.js 时代），自动回退到旧流程

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

# 新结构路径
DJANGO_DIR="$DEPLOY_DIR/apps/django"
WEB_DIR="$DEPLOY_DIR/web/app"

# systemd 服务名 (新)
SERVICE_NAME="${SERVICE_NAME:-ats-django}"
# =================

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(ts)] $*" | tee -a "$LOG_FILE"; }

mkdir -p "$(dirname "$LOG_FILE")" "$(dirname "$APP_LOG")" "$(dirname "$APP_PID_FILE")"

log "================================================"
log " ATS-New 部署开始 (branch=$BRANCH, port=$APP_PORT)"
log "================================================"

# ---------- 0. 前置检查 ----------
if [ ! -d "$DEPLOY_DIR" ]; then
  log "❌ $DEPLOY_DIR 不存在，clone 一次"
  mkdir -p "$(dirname "$DEPLOY_DIR")"
  git clone "$REPO_URL" "$DEPLOY_DIR"
fi
cd "$DEPLOY_DIR"

# 检测新旧结构: 优先 Django (apps/django),否则回退 Node.js (backend)
HAS_DJANGO=0
HAS_NODEJS=0
[ -d "$DJANGO_DIR" ] && HAS_DJANGO=1
[ -d "$DEPLOY_DIR/backend" ] && HAS_NODEJS=1

if [ "$HAS_DJANGO" -eq 0 ] && [ "$HAS_NODEJS" -eq 0 ]; then
  log "❌ 找不到 Django 或 Node.js 后端目录"
  exit 1
fi
if [ "$HAS_DJANGO" -eq 1 ] && [ "$HAS_NODEJS" -eq 1 ]; then
  log "  ⚠ 同时存在 apps/django/ 和 backend/,优先用 Django"
fi

# ---------- 1. git pull ----------
log ""
log "[1/5] git fetch + reset"
git fetch origin "$BRANCH"
git reset --hard "origin/$BRANCH"
HEAD=$(git log --oneline -1)
log "  head: $HEAD"

# ---------- 2. 后端 deps + 迁移 ----------
log ""
if [ "$HAS_DJANGO" -eq 1 ]; then
  log "[2/5] django: pip install + migrate"
  cd "$DJANGO_DIR"
  [ -d ".venv" ] || python3 -m venv .venv
  # shellcheck disable=SC1091
  . .venv/bin/activate
  pip install --upgrade pip >/dev/null 2>&1
  pip install -r requirements.txt 2>&1 | tail -3 | sed 's/^/  /' | tee -a "$LOG_FILE" >/dev/null
  log "  pip install OK"
  # 注意: 不要用 --accept-data-loss,会让列被静默删除
  python manage.py migrate --noinput 2>&1 | tail -3 | sed 's/^/  /' | tee -a "$LOG_FILE" >/dev/null
  log "  migrate OK"
  python manage.py collectstatic --noinput 2>&1 | tail -3 | sed 's/^/  /' | tee -a "$LOG_FILE" >/dev/null
  log "  collectstatic OK"
  log "  ✓ django deps + migrate OK"
else
  log "[2/5] backend (legacy Node.js): npm install + prisma"
  cd "$DEPLOY_DIR/backend"
  npm install --omit=dev 2>&1 | tail -3 | sed 's/^/  /' | tee -a "$LOG_FILE" >/dev/null
  npx prisma generate 2>&1 | tail -3 | sed 's/^/  /' | tee -a "$LOG_FILE" >/dev/null
  npx prisma db push --skip-generate --accept-data-loss 2>&1 | tail -3 | sed 's/^/  /' | tee -a "$LOG_FILE" >/dev/null
  log "  ✓ legacy backend deps OK"
fi

# ---------- 3. 前端 build ----------
log ""
if [ -d "$WEB_DIR" ]; then
  log "[3/5] frontend: npm install + build (新 Vite)"
  cd "$WEB_DIR"
  npm install --omit=dev 2>&1 | tail -3 | sed 's/^/  /' | tee -a "$LOG_FILE" >/dev/null
  npm run build 2>&1 | tail -3 | sed 's/^/  /' | tee -a "$LOG_FILE" >/dev/null
elif [ -d "$DEPLOY_DIR/frontend" ]; then
  log "[3/5] frontend: npm install + build (legacy)"
  cd "$DEPLOY_DIR/frontend"
  npm install 2>&1 | tail -3 | sed 's/^/  /' | tee -a "$LOG_FILE" >/dev/null
  npm run build 2>&1 | tail -3 | sed 's/^/  /' | tee -a "$LOG_FILE" >/dev/null
fi
log "  ✓ frontend build OK"

# ---------- 4. 重启后端 ----------
log ""
log "[4/5] restart backend on :$APP_PORT"

# 优先用 systemd 守护
if [ "$HAS_DJANGO" -eq 1 ] && systemctl list-unit-files 2>/dev/null | grep -q "^${SERVICE_NAME}.service"; then
  log "  systemctl restart $SERVICE_NAME"
  systemctl restart "$SERVICE_NAME"
elif systemctl list-unit-files 2>/dev/null | grep -q "^ats-backend.service"; then
  log "  systemctl restart ats-backend (legacy)"
  systemctl restart ats-backend
else
  log "  ⚠ 未找到 systemd unit,回退到手工拉起"

  # 杀老的 PID
  OLD_PID=$(cat "$APP_PID_FILE" 2>/dev/null || echo "")
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    log "  停老 PID=$OLD_PID (SIGTERM)"
    kill -TERM "$OLD_PID" 2>/dev/null || true
    for _i in 1 2 3 4 5; do
      sleep 1
      kill -0 "$OLD_PID" 2>/dev/null || break
    done
    kill -0 "$OLD_PID" 2>/dev/null && {
      log "  老进程不响应,SIGKILL"
      kill -9 "$OLD_PID" 2>/dev/null || true
    }
  fi

  # 端口兜底
  PORT_PIDS=$(lsof -ti:"$APP_PORT" 2>/dev/null || true)
  if [ -n "$PORT_PIDS" ]; then
    log "  端口 $APP_PORT 还被占: $PORT_PIDS,kill -9"
    # shellcheck disable=SC2086
    kill -9 $PORT_PIDS 2>/dev/null || true
    sleep 1
  fi

  # 拉起新的
  if [ "$HAS_DJANGO" -eq 1 ]; then
    cd "$DJANGO_DIR"
    # Daphne 是 ASGI 服务器, 支持 WebSocket (Channels)
    # shellcheck disable=SC1091
    ( . .venv/bin/activate && nohup daphne -b 0.0.0.0 -p "$APP_PORT" config.asgi:application > "$APP_LOG" 2>&1 & echo $! > "$APP_PID_FILE" )
  else
    cd "$DEPLOY_DIR/backend"
    ( nohup node --env-file=.env src/app.js > "$APP_LOG" 2>&1 & echo $! > "$APP_PID_FILE" )
  fi
  sleep 4
  NEW_PID=$(cat "$APP_PID_FILE")
  log "  新 PID=$NEW_PID"
  if ! kill -0 "$NEW_PID" 2>/dev/null; then
    log "  ❌ 新进程没起来,看 log:"
    tail -50 "$APP_LOG" | tee -a "$LOG_FILE"
    exit 1
  fi
fi

# ---------- 5. verify ----------
log ""
log "[5/5] verify"

# 健康检查路径 (Django 带 trailing slash, Node.js 不带)
HEALTH_URLS=()
if [ "$HAS_DJANGO" -eq 1 ]; then
  HEALTH_URLS=("http://localhost:$APP_PORT/api/health/")
else
  HEALTH_URLS=("http://localhost:$APP_PORT/api/health")
fi

HEALTH_OK=0
for HEALTH_URL in "${HEALTH_URLS[@]}"; do
  if curl -fsS "$HEALTH_URL" > /dev/null 2>&1; then
    log "  ✓ $HEALTH_URL OK"
    curl -fsS "$HEALTH_URL" 2>&1 | head -3 | tee -a "$LOG_FILE"
    HEALTH_OK=1
    break
  else
    log "  ⚠ $HEALTH_URL 失败"
  fi
done
if [ "$HEALTH_OK" -eq 0 ]; then
  log "  ❌ 所有 health URL 都失败"
  tail -50 "$APP_LOG" | tee -a "$LOG_FILE"
  exit 1
fi

if curl -fsSI "http://localhost:$APP_PORT/" 2>/dev/null | head -1 | grep -q "200"; then
  log "  ✓ 首页 200"
else
  log "  ⚠ 首页没起（可能前端未 build）"
fi

log ""
log "================================================"
log " 🎉 部署完成"
log "   公网: https://ats.lokisong.cloud"
log "   log:  $APP_LOG"
log "================================================"
