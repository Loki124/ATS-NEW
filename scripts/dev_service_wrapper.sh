#!/usr/bin/env bash
# =============================================================================
# ATS-NEW dev 服务 自愈包装器（供 launchd plist 调用）
# -----------------------------------------------------------------------------
# 解决"进程活着但不健康"的假活问题：
#   1. 拉起服务后探活（启动期最多 START_TIMEOUT 秒），且必须确认【自己拉的子进程】
#      仍存活（避免被端口上的僵尸进程欺骗误判健康）
#   2. 运行期每 HEALTH_INTERVAL 秒看门狗探活，不健康立即杀掉重启
#   3. 启动/运行失败若发现端口被【非本子进程】的孤儿占用，主动杀掉孤儿再重启
#   4. 连续失败达 MAX_RESTARTS 视为不可恢复 → macOS 通知（osascript）并干净退出
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
    PORT=5212
    PATH_PREFIX="${NODE_BIN:-/usr/local/bin}:/usr/local/bin:/usr/bin:/bin"
    ;;
  be)
    BIN="$PROJECT_DIR/apps/django/.venv/bin/python"
    ARGS=("$PROJECT_DIR/apps/django/manage.py" runserver 0.0.0.0:8000)
    WD="$PROJECT_DIR/apps/django"
    EXTRA_ENV=(DJANGO_SETTINGS_MODULE=config.settings.dev PYTHONUNBUFFERED=1)
    PORT=8000
    PATH_PREFIX="$PROJECT_DIR/apps/django/.venv/bin:/usr/local/bin:/usr/bin:/bin"
    ;;
  celery)
    BIN="$PROJECT_DIR/apps/django/.venv/bin/python"
    # -P solo: 单进程，避免 dev 环境 prefork fork 问题；消费默认 celery 队列 + scoring 队列
    ARGS=(-m celery -A celery_app worker --loglevel=info -Q celery,scoring -P solo)
    WD="$PROJECT_DIR/apps/django"
    EXTRA_ENV=(DJANGO_SETTINGS_MODULE=config.settings.dev PYTHONUNBUFFERED=1)
    PORT=""   # celery worker 无监听端口，free_port 对健康检查均跳过
    PATH_PREFIX="$PROJECT_DIR/apps/django/.venv/bin:/usr/local/bin:/usr/bin:/bin"
    ;;
  *)
    echo "usage: $0 <fe|be|celery>" >&2
    exit 2
    ;;
esac

# 探活：仅 200 视为健康。
fe_healthy() { [[ "$(curl --noproxy '*' -s -o /dev/null -w '%{http_code}' --max-time 3 "http://localhost:5212/" 2>/dev/null)" == "200" ]]; }
# 探活：200/503/500 均视为“进程存活”（503/500=底座未就绪但服务在跑）；
# 仅连接失败（无响应）才视为真正死亡，避免把“降级”误判为“假活”而反复杀掉重启。
be_healthy() {
  local code
  code="$(curl --noproxy '*' -s -o /dev/null -w '%{http_code}' --max-time 3 "http://127.0.0.1:8000/health/" 2>/dev/null)"
  [[ "$code" == "200" || "$code" == "503" || "$code" == "500" ]]
}
# celery worker 无 HTTP 端口：健康=子进程仍存活（崩溃由 launchd/包装器重启兜底）
celery_healthy() { kill -0 "$PID" 2>/dev/null; }

# 杀掉占用目标端口、但【不是本子进程】的全部孤儿，确保本包装器独占端口
# （旧逻辑只 kill head -1，多孤儿并发时会残留 → 新进程 “port already in use”）
free_port() {
  local holders h
  holders="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | grep -v -x "$PID")"
  if [[ -n "$holders" ]]; then
    for h in $holders; do
      echo "[$(date '+%Y-%m-%d %H:%M:%S')] killing orphan pid $h holding :$PORT" >> "$LOG_DIR/$SERVICE-wrapper.log"
      kill -9 "$h" 2>/dev/null || true
    done
    sleep 1
  fi
}

# 退出时清理本包装器拉起的子进程，避免 wrapper 被 launchd 强杀后留下孤儿
cleanup() { [[ -n "${PID:-}" ]] && kill -9 "$PID" 2>/dev/null; }
trap cleanup EXIT

echo "[$(date '+%Y-%m-%d %H:%M:%S')] wrapper for $SERVICE starting (max_restarts=$MAX_RESTARTS)" >> "$LOG_DIR/$SERVICE-wrapper.log"

restart_count=0
while true; do
  # 启动前先清场：杀掉占用端口的孤儿（若有），避免新进程因端口冲突启动即崩
  # celery 无监听端口（PORT 为空），跳过端口清理
  [[ -n "${PORT:-}" ]] && free_port

  echo "[$(date '+%Y-%m-%d %H:%M:%S')] launching $SERVICE (attempt $((restart_count+1)))" >> "$LOG_DIR/$SERVICE-wrapper.log"
  (
    cd "$WD" || exit 3
    exec env PATH="$PATH_PREFIX" "${EXTRA_ENV[@]}" "$BIN" "${ARGS[@]}" \
      >> "$LOG_DIR/$SERVICE-stdout.log" 2>> "$LOG_DIR/$SERVICE-stderr.log"
  ) &
  PID=$!

  # —— 启动期探活：必须【子进程存活】且【端口响应】才算健康（不被僵尸欺骗）——
  healthy=0
  for ((i = 0; i < START_TIMEOUT / 2; i++)); do
    if kill -0 "$PID" 2>/dev/null && "$SERVICE"_healthy; then healthy=1; break; fi
    if ! kill -0 "$PID" 2>/dev/null; then break; fi   # 子进程已退出（启动即崩）
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
