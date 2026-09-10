#!/bin/bash
# ATS-NEW Docker 版自动部署脚本（由 webhook_receiver.py 触发）
#
# 流程: git pull → docker compose build(全部本地服务) → docker compose up -d --force-recreate
# 与旧的 venv+systemd 版 (ops/scripts/deploy.sh / scripts/webhook-deploy.sh) 无关, 本脚本只服务于
# 1Panel + docker compose 生产栈。
#
# 用法:
#   bash ops/scripts/webhook-deploy.sh            # 完整部署
#   WEBHOOK_BRANCH=dev bash ops/scripts/webhook-deploy.sh
#
# 可覆盖的环境变量:
#   DEPLOY_DIR   仓库根 (含 ops/ apps/ web/), 默认 /opt/data/ATS-new
#   WEBHOOK_BRANCH 触发部署的分支, 默认 main
#   LOG_FILE     部署日志, 默认 /var/log/ats-deploy.log

set -o pipefail

# ===== 配置 =====
DEPLOY_DIR="${DEPLOY_DIR:-/opt/data/ATS-new}"
OPS_DIR="${OPS_DIR:-$DEPLOY_DIR/ops}"
BRANCH="${WEBHOOK_BRANCH:-main}"
LOG_FILE="${LOG_FILE:-/var/log/ats-deploy.log}"
LOCK_FILE="${LOCK_FILE:-/var/run/ats-deploy.lock}"

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(ts)] $*" | tee -a "$LOG_FILE"; }

mkdir -p "$(dirname "$LOG_FILE")" "$(dirname "$LOCK_FILE")" 2>/dev/null || true
touch "$LOG_FILE" 2>/dev/null || true

# ===== 并发锁 (避免 Gitee 重复事件/快速连续 push 叠加部署) =====
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  log "⚠ 已有部署在跑 (lock 被占), 本次跳过"
  exit 0
fi

log "================================================"
log " ATS-NEW Docker 部署开始 (branch=$BRANCH)"
log " repo=$DEPLOY_DIR  ops=$OPS_DIR"
log "================================================"

# ---------- 0. 前置检查 ----------
if [ ! -d "$DEPLOY_DIR/.git" ]; then
  log "❌ $DEPLOY_DIR 不是 git 仓库"
  exit 1
fi
if [ ! -f "$OPS_DIR/docker-compose.yml" ]; then
  log "❌ $OPS_DIR/docker-compose.yml 不存在"
  exit 1
fi

# ---------- 1. git pull ----------
log ""
log "[1/4] git fetch + reset to origin/$BRANCH"
cd "$DEPLOY_DIR"
git fetch origin "$BRANCH"
git reset --hard "origin/$BRANCH"
HEAD=$(git log --oneline -1)
log "  head: $HEAD"

# ---------- 2. 构建全部本地镜像 ----------
log ""
log "[2/4] docker compose build (backend/asgi/celery-worker/celery-beat/nginx)"
cd "$OPS_DIR"
# --no-cache 确保把磁盘上的最新代码/依赖全部打进镜像, 避免旧缓存层导致"代码改了但镜像没变"
docker compose build --no-cache
BUILD_RC=$?
if [ "$BUILD_RC" -ne 0 ]; then
  log "❌ docker compose build 失败 (rc=$BUILD_RC)"
  exit 1
fi
log "  build OK"

# ---------- 3. 重建并启动容器 ----------
log ""
log "[3/4] docker compose up -d --force-recreate"
docker compose up -d --force-recreate
UP_RC=$?
if [ "$UP_RC" -ne 0 ]; then
  log "❌ docker compose up 失败 (rc=$UP_RC)"
  exit 1
fi
log "  up OK"

# ---------- 4. 健康检查 ----------
log ""
log "[4/4] 健康检查 (等待后端 /health/)"
# 给后端留启动时间 (migrate + gunicorn 起进程)
for i in $(seq 1 30); do
  if curl -fsS --noproxy '*' http://127.0.0.1:9908/health/ > /dev/null 2>&1; then
    log "  ✓ 后端 /health/ OK (第 $i 次)"
    break
  fi
  if [ "$i" -eq 30 ]; then
    log "  ⚠ 30 次仍未拿到 /health/, 但容器已启动, 稍后请 tail 日志确认"
  fi
  sleep 3
done

log ""
log "================================================"
log " 🎉 部署完成"
log "   head: $HEAD"
log "   log:  $LOG_FILE"
log "================================================"
