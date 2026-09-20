#!/usr/bin/env bash
# =============================================================================
# ATS-NEW dev 服务保活 launcher（macOS 兼容版）
# -----------------------------------------------------------------------------
# 与 launchd 等效的保活思路：用 nohup+disown 让保活脚本本身脱离当前会话，
# 拉起的子服务进程独立成组，WorkBuddy 会话窗口关闭不会带走它们。
# 崩溃后由本脚本循环自动重启（含 5s 节流）。
#
# 用法：
#   启动：  bash scripts/dev_keepalive.sh >/dev/null 2>&1 & disown
#   停止：  bash scripts/dev_keepalive.sh --stop
#   日志：  .run-logs/{vite,django}-{stdout,stderr}.log
#   保活自身日志：.run-logs/keepalive.log
#
# 2026-09-05 修订：
#   - 旧版用 setsid，macOS 无此命令 → 脚本在 macOS 上无法启动（=无保活）
#   - 改用 nohup + setsid 等价：直接 & 后台 + disown + 用 trap 屏蔽 HUP，
#     macOS Bash 内置已能等价 setsid 的"脱离进程组"效果
#   - keepalive 自身日志独立写到 .run-logs/keepalive.log
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
KA_PID="$PID_DIR/keepalive.pid"

# 屏蔽 HUP，让 shell 退出不杀子进程（macOS 等价 setsid 关键）
trap '' HUP

# 写自己的 pid，便于 --stop 时一并清理
echo $$ > "$KA_PID"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] keepalive started pid=$$" >> "$LOG_DIR/keepalive.log"

stop_svc() {
  echo "[stop] killing dev services..."
  for p in "$FE_PID" "$BE_PID" "$KA_PID"; do
    [[ -f "$p" ]] && kill "$(cat "$p")" 2>/dev/null && rm -f "$p"
  done
  pkill -f "vite --port 5212" 2>/dev/null
  pkill -f "runserver 0.0.0.0:8000" 2>/dev/null
  pkill -f "scripts/dev_keepalive.sh" 2>/dev/null
  exit 0
}
[[ "${1:-}" == "--stop" ]] && stop_svc

run_fe() {
  while true; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] start vite (5212)" >> "$LOG_DIR/keepalive.log"
    PATH="$NODE_BIN:/usr/local/bin:/usr/bin:/bin" \
    NODE_ENV=development \
    nohup "$VITE_BIN" --port 5212 --host 0.0.0.0 --strictPort \
      >>"$LOG_DIR/vite-stdout.log" 2>>"$LOG_DIR/vite-stderr.log" </dev/null &
    echo $! > "$FE_PID"
    wait
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] vite exited, restart in 5s" >> "$LOG_DIR/keepalive.log"
    sleep 5
  done
}

run_be() {
  while true; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] start django (8000)" >> "$LOG_DIR/keepalive.log"
    PATH="$PROJECT_DIR/apps/django/.venv/bin:/usr/local/bin:/usr/bin:/bin" \
    DJANGO_SETTINGS_MODULE=config.settings.dev \
    PYTHONUNBUFFERED=1 \
    nohup "$PY_BIN" "$PROJECT_DIR/apps/django/manage.py" runserver 0.0.0.0:8000 \
      >>"$LOG_DIR/django-stdout.log" 2>>"$LOG_DIR/django-stderr.log" </dev/null &
    echo $! > "$BE_PID"
    wait
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] django exited, restart in 5s" >> "$LOG_DIR/keepalive.log"
    sleep 5
  done
}

# 后台分别拉起两个保活循环；disown 让 shell 退出不影响
run_fe &
disown
run_be &
disown

echo "[ok] dev keepalive started (fe pid guard $(cat "$FE_PID" 2>/dev/null), be pid guard $(cat "$BE_PID" 2>/dev/null))"
echo "logs: tail -f $LOG_DIR/vite-stdout.log $LOG_DIR/django-stdout.log"
echo "ka log: tail -f $LOG_DIR/keepalive.log"
wait
