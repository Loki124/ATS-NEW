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
# stale-lock 自愈: 写 PID + 记录锁龄; 若锁超过 LOCK_STALE_SECONDS 未释放(上一次部署
# 进程挂死/子进程继承了 fd 9 未释放), 视为僵死锁强制接管。否则跳过本次。
LOCK_STALE_SECONDS="${LOCK_STALE_SECONDS:-1800}"  # 默认 30 分钟, 一次完整 --no-cache 部署不会超此值

_lock_age() {
  # 锁文件 mtime 距现在的秒数 (Linux GNU stat / macOS BSD stat 双兼容)
  local mtime
  mtime=$(stat -c %Y "$LOCK_FILE" 2>/dev/null || stat -f %m "$LOCK_FILE" 2>/dev/null || echo "$(date +%s)")
  echo $(( $(date +%s) - mtime ))
}

# 递归杀整棵进程树: 子进程可能继承了 fd 9 上的 flock, 只杀父 PID 清不掉锁
_kill_tree() {
  local _pid="$1"
  [ -z "$_pid" ] && return 0
  local _c
  for _c in $(pgrep -P "$_pid" 2>/dev/null); do
    _kill_tree "$_c"
  done
  kill -9 "$_pid" 2>/dev/null || true
}

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  _age=$(_lock_age)
  if [ "$_age" -gt "$LOCK_STALE_SECONDS" ]; then
    log "⚠ 检测到僵死锁 (已 ${_age}s > ${LOCK_STALE_SECONDS}s), 强制接管"
    # 根因: 旧版只 kill 父 PID, 但持锁的 docker compose 子进程继承了 fd 9 上的 flock,
    #        父进程死后子进程仍占着旧 inode 的锁 → 重新抢锁必败。改为递归杀整棵进程树。
    _holder=$(awk '{print $1}' "$LOCK_FILE" 2>/dev/null || true)
    if [ -n "$_holder" ]; then
      log "   强制结束持锁进程树 PID=$_holder (含 docker 子进程)"
      _kill_tree "$_holder"
    fi
    # 双保险: 反查所有仍持有该锁文件的进程(排除自身), 一并清理
    for _pid in $(fuser "$LOCK_FILE" 2>/dev/null | tr ' ' '\n' | grep -E '^[0-9]+$'); do
      [ "$_pid" != "$$" ] && _kill_tree "$_pid"
    done
    sleep 2
    rm -f "$LOCK_FILE"
    exec 9>"$LOCK_FILE"
    if ! flock -n 9; then
      log "❌ 强制抢锁仍失败, 本次跳过"
      exit 0
    fi
    log "   ✅ 已接管锁"
  else
    log "⚠ 已有部署在跑 (lock 被占, 已 ${_age}s), 本次跳过"
    exit 0
  fi
fi
echo "$$" > "$LOCK_FILE"
# 部署结束(正常/异常)都清掉 PID, 避免残留; 同时让下一个部署能正常抢锁
trap 'rm -f "$LOCK_FILE"' EXIT

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

# ---------- 0.5 前置检查: compose 必填变量齐备 ----------
# 从 docker-compose.yml 抽取所有 ${VAR:?...} 必填变量, 缺一就在 build 前一次性报清,
# 避免 build 到一半才报 "required variable X is missing" (compose 插值遇到第一个缺失就停)。
log ""
log "[0/4] 检查 compose 必填变量 ($OPS_DIR/.env)"
_REQUIRED_VARS=$(grep -oE '\$\{[A-Z_][A-Z0-9_]*:?\?' "$OPS_DIR/docker-compose.yml" | sed -E 's/\$\{([A-Z_][A-Z0-9_]*):?.*/\1/' | sort -u)
_MISSING=""
for _v in $_REQUIRED_VARS; do
  if env | grep -qE "^${_v}=" || grep -qE "^${_v}=" "$OPS_DIR/.env" 2>/dev/null; then
    :
  else
    _MISSING="$_MISSING $_v"
  fi
done
if [ -n "$_MISSING" ]; then
  log "❌ 缺以下必填变量, 请在 $OPS_DIR/.env 补齐:$_MISSING"
  log "   参考模板: $OPS_DIR/.env.example"
  exit 1
fi
log "  ✓ 必填变量齐备 ($(echo "$_REQUIRED_VARS" | wc -w | tr -d ' ') 项)"

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
