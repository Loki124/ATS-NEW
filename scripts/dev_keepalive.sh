#!/usr/bin/env bash
# =============================================================================
# ATS-NEW dev 服务保活 launcher（setsid 脱离会话版）
# -----------------------------------------------------------------------------
# 与 launchd 等效的保活思路：用 setsid 让进程完全脱离终端/agent 会话，
# 即使 WorkBuddy 会话窗口关闭，前后端仍存活。
# 崩溃后由本脚本循环自动重启（含 5s 节流）。
#
# 用法：
#   启动：  setsid bash scripts/dev_keepalive.sh  >/dev/null 2>&1 &
#   停止：  bash scripts/dev_keepalive.sh --stop
#   日志：  .run-logs/{vite,django}-{stdout,stderr}.log
# =============================================================================
set -u
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_DIR/.run-logs"
mkdir -p "$LOG_DIR"

NODE_BIN="$(ls -d "$HOME/.workbuddy/binaries/node/versions"/*/bin 2>/dev/null | head -1)"
PY_BIN="$PROJECT_DIR/apps/django/.venv/bin/python"
VITE_BIN="$PROJECT_DIR/web/app/node_modules/.bin/vite"
PID_DIR="$PROJECT_DIR/.run-pids"
mkdir -p "$PID_DIR"
FE_PID="$PID_DIR/fe.pid"
BE_PID="$PID_DIR/be.pid"

stop_svc() {
  echo "[stop] killing dev services..."
  for p in "$FE_PID" "$BE_PID"; do
    [[ -f "$p" ]] && kill "$(cat "$p")" 2>/dev/null && rm -f "$p"
  done
  pkill -f "vite --port 5212" 2>/dev/null
  pkill -f "runserver 0.0.0.0:8000" 2>/dev/null
  exit 0
}
[[ "${1:-}" == "--stop" ]] && stop_svc

run_fe() {
  while true; do
    echo "[$(date +%H:%M:%S)] start vite (5212)"
    PATH="$NODE_BIN:/usr/local/bin:/usr/bin:/bin" \
    NODE_ENV=development \
    setsid "$VITE_BIN" --port 5212 --host 0.0.0.0 \
      >>"$LOG_DIR/vite-stdout.log" 2>>"$LOG_DIR/vite-stderr.log" &
    echo $! > "$FE_PID"
    wait
    echo "[$(date +%H:%M:%S)] vite exited, restart in 5s"
    sleep 5
  done
}

run_be() {
  while true; do
    echo "[$(date +%H:%M:%S)] start django (8000)"
    PATH="$PROJECT_DIR/apps/django/.venv/bin:/usr/local/bin:/usr/bin:/bin" \
    DJANGO_SETTINGS_MODULE=config.settings.dev \
    PYTHONUNBUFFERED=1 \
    setsid "$PY_BIN" "$PROJECT_DIR/apps/django/manage.py" runserver 0.0.0.0:8000 \
      >>"$LOG_DIR/django-stdout.log" 2>>"$LOG_DIR/django-stderr.log" &
    echo $! > "$BE_PID"
    wait
    echo "[$(date +%H:%M:%S)] django exited, restart in 5s"
    sleep 5
  done
}

# 后台分别拉起两个保活循环
run_fe &
run_be &

echo "[ok] dev keepalive started (fe pid guard $(cat "$FE_PID" 2>/dev/null), be pid guard $(cat "$BE_PID" 2>/dev/null))"
echo "logs: tail -f $LOG_DIR/vite-stdout.log $LOG_DIR/django-stdout.log"
wait
