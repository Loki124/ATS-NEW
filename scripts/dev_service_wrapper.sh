#!/usr/bin/env bash
# =============================================================================
# ATS-NEW dev 服务 自愈包装器（供 launchd plist 调用）
# -----------------------------------------------------------------------------
# 解决"进程活着但不健康"的假活问题：
#   1. 拉起服务后探活（启动期最多 START_TIMEOUT 秒）
#   2. 运行期每 HEALTH_INTERVAL 秒看门狗探活一次，不健康立即杀掉重启
#   3. 连续失败达 MAX_RESTARTS 视为不可恢复 → macOS 通知用户并干净退出
#      （plist 设 KeepAlive.SuccessfulExit=false，干净退出即不再被 launchd 重启，
#       避免无限重启刷屏；用户介入修复后重新 bootstrap 即可）
#
# 注意：本包装器本身被 launchd 托管（RunAtLoad + KeepAlive.Crashed），
#       完全不依赖 WorkBuddy 会话，关窗/登出后照常存活。
# =============================================================================
set -u
SERVICE="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_DIR/.run-logs"
mkdir -p "$LOG_DIR"

MAX_RESTARTS=10        # 连续失败达此数 → 视为不可恢复，通知并退出
HEALTH_INTERVAL=15     # 运行期看门狗间隔（秒）
START_TIMEOUT=90       # 启动后最长探活等待（秒）
RESTART_DELAY=3        # 每次重启前冷却（秒）
NODE_BIN="$(ls -d "$HOME/.workbuddy/binaries/node/versions"/*/bin 2>/dev/null | head -1)"

notify() {
  local title="$1" msg="$2"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] NOTIFY($title): $msg" >> "$LOG_DIR/$SERVICE-wrapper.log"
  if command -v osascript >/dev/null 2>&1; then
    osascript -e "display notification \"$msg\" with title \"ATS-NEW Dev\" subtitle \"$title\"" 2>/dev/null || true
  fi
}

case "$SERVICE" in
  fe)
    BIN="$PROJECT_DIR/web/app/node_modules/.bin/vite"
    ARGS=(--port 5212 --host 0.0.0.0 --strictPort)
    WD="$PROJECT_DIR/web/app"
    EXTRA_ENV=(NODE_ENV=development)
    PATH_PREFIX="${NODE_BIN:-/usr/local/bin}:/usr/local/bin:/usr/bin:/bin"
    ;;
  be)
    BIN="$PROJECT_DIR/apps/django/.venv/bin/python"
    ARGS=("$PROJECT_DIR/apps/django/manage.py" runserver 0.0.0.0:8000)
    WD="$PROJECT_DIR/apps/django"
    EXTRA_ENV=(DJANGO_SETTINGS_MODULE=config.settings.dev PYTHONUNBUFFERED=1)
    PATH_PREFIX="$PROJECT_DIR/apps/django/.venv/bin:/usr/local/bin:/usr/bin:/bin"
    ;;
  *)
    echo "usage: $0 <fe|be>" >&2
    exit 2
    ;;
esac

fe_healthy() { curl --noproxy '*' -s -o /dev/null "http://localhost:5212/" 2>/dev/null; }
be_healthy() { [[ "$(curl --noproxy '*' -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:8000/health/" 2>/dev/null)" == "200" ]]; }

echo "[$(date '+%Y-%m-%d %H:%M:%S')] wrapper for $SERVICE starting (max_restarts=$MAX_RESTARTS)" >> "$LOG_DIR/$SERVICE-wrapper.log"

restart_count=0
while true; do
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] launching $SERVICE (attempt $((restart_count+1)))" >> "$LOG_DIR/$SERVICE-wrapper.log"
  (
    cd "$WD" || exit 3
    exec env PATH="$PATH_PREFIX" "${EXTRA_ENV[@]}" "$BIN" "${ARGS[@]}" \
      >> "$LOG_DIR/$SERVICE-stdout.log" 2>> "$LOG_DIR/$SERVICE-stderr.log"
  ) &
  PID=$!

  # —— 启动期探活 ——
  healthy=0
  for ((i = 0; i < START_TIMEOUT / 2; i++)); do
    if "$SERVICE"_healthy; then healthy=1; break; fi
    if ! kill -0 "$PID" 2>/dev/null; then break; fi   # 进程已退出（启动即崩）
    sleep 2
  done

  if [[ $healthy -eq 1 ]]; then
    restart_count=0
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $SERVICE healthy (pid $PID)" >> "$LOG_DIR/$SERVICE-wrapper.log"
    # —— 运行期看门狗 ——
    while kill -0 "$PID" 2>/dev/null; do
      sleep "$HEALTH_INTERVAL"
      if ! "$SERVICE"_healthy; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] $SERVICE unhealthy, killing pid $PID" >> "$LOG_DIR/$SERVICE-wrapper.log"
        kill -9 "$PID" 2>/dev/null || true
        break
      fi
    done
    wait "$PID" 2>/dev/null || true
    restart_count=$((restart_count + 1))
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $SERVICE exited (restart #$restart_count)" >> "$LOG_DIR/$SERVICE-wrapper.log"
  else
    kill -9 "$PID" 2>/dev/null || true
    wait "$PID" 2>/dev/null || true
    restart_count=$((restart_count + 1))
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $SERVICE failed to become healthy (restart #$restart_count)" >> "$LOG_DIR/$SERVICE-wrapper.log"
  fi

  if [[ $restart_count -ge $MAX_RESTARTS ]]; then
    notify "$SERVICE 无法恢复" "连续 $MAX_RESTARTS 次启动失败，已停止自动重启。请检查 $LOG_DIR/$SERVICE-stderr.log"
    # 干净退出：plist KeepAlive.SuccessfulExit=false → launchd 不再重启本包装器
    exit 0
  fi
  sleep "$RESTART_DELAY"
done
