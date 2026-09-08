#!/usr/bin/env bash
# =============================================================================
# devstack.sh — 为每个 git worktree 开一套独立的 ATS 前后端预览服务 (launchd 托管)
# -----------------------------------------------------------------------------
# 设计: 主服务(主分支)跑在 8000/5212; 各 worktree 用偏移端口开独立预览栈,
#       互不干扰, 可在浏览器并排对比多个分支效果, 用完即关。
#       用 launchd (与 install_dev_launchd.sh 同机制) 托管, 命令结束后仍存活、
#       进程崩溃自动重启。
#
# 用法:
#   bash scripts/devstack.sh start <worktree绝对路径> [offset]   # offset 默认 1
#   bash scripts/devstack.sh stop  [offset]
#   bash scripts/devstack.sh ls
#   bash scripts/devstack.sh help
#
# 端口规则 (offset = N):
#   后端 Django : 8000 + N      (例 N=1 → 8001)
#   前端 Vite   : 5212 + 2N     (例 N=1 → 5214, 代理 → 8000+N)
#
# 依赖:
#   - 后端复用任意 worktree 的 .venv(实际代码由 <worktree>/apps/django 决定)
#   - 前端需 <worktree>/web/app/node_modules; 缺失且 package.json 与参考
#     worktree 一致时, 自动软链复用, 免去 npm install
#   - 后端需 <worktree>/apps/django/.env(含 DATABASE_URL 等)
# =============================================================================

set -euo pipefail

# ---- 参考路径(软链 node_modules / 复用 venv 的来源) ----
REF_WT="/Users/loki/WorkBuddy/招聘助手/ATS-NEW"
REF_NM="$REF_WT/web/app/node_modules"
VENV="$REF_WT/apps/django/.venv/bin/python"
NODE_BIN="$(ls -d "$HOME/.workbuddy/binaries/node/versions"/*/bin 2>/dev/null | head -1)"
[[ -z "$NODE_BIN" ]] && NODE_BIN="/usr/local/bin"
LAUNCH_DIR="$HOME/Library/LaunchAgents"
RUN_DIR="$HOME/.cache/ats-devstack"
UID_NUM="$(id -u)"
mkdir -p "$RUN_DIR" "$LAUNCH_DIR"

setup() {
  local off="${1:-1}"
  OFFSET="$off"
  BE_PORT=$((8000 + off))
  FE_PORT=$((5212 + 2 * off))
  BE_LABEL="com.ats.devstack.be.$off"
  FE_LABEL="com.ats.devstack.fe.$off"
  BE_PLIST="$LAUNCH_DIR/$BE_LABEL.plist"
  FE_PLIST="$LAUNCH_DIR/$FE_LABEL.plist"
  be_log="$RUN_DIR/be-$off.log"
  fe_log="$RUN_DIR/fe-$off.log"
}

usage() {
  sed -n '3,24p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

write_be_plist() {
  local wt="$1"
  cat > "$BE_PLIST" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$BE_LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$VENV</string>
    <string>$wt/apps/django/manage.py</string>
    <string>runserver</string>
    <string>0.0.0.0:$BE_PORT</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$wt/apps/django</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <dict><key>Crashed</key><true/></dict>
  <key>ThrottleInterval</key>
  <integer>5</integer>
  <key>StandardOutPath</key>
  <string>$be_log</string>
  <key>StandardErrorPath</key>
  <string>$be_log</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>$(dirname "$VENV"):/usr/local/bin:/usr/bin:/bin</string>
    <key>DJANGO_SETTINGS_MODULE</key>
    <string>config.settings.dev</string>
    <key>PYTHONUNBUFFERED</key>
    <string>1</string>
  </dict>
</dict>
</plist>
PLIST_EOF
}

write_fe_plist() {
  local wt="$1"
  cat > "$FE_PLIST" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$FE_LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$wt/web/app/node_modules/.bin/vite</string>
    <string>--port</string>
    <string>$FE_PORT</string>
    <string>--host</string>
    <string>0.0.0.0</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$wt/web/app</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <dict><key>Crashed</key><true/></dict>
  <key>ThrottleInterval</key>
  <integer>5</integer>
  <key>StandardOutPath</key>
  <string>$fe_log</string>
  <key>StandardErrorPath</key>
  <string>$fe_log</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>$NODE_BIN:/usr/local/bin:/usr/bin:/bin</string>
    <key>VITE_BACKEND_URL</key>
    <string>http://localhost:$BE_PORT</string>
    <key>NODE_ENV</key>
    <string>development</string>
  </dict>
</dict>
</plist>
PLIST_EOF
}

# ---- start ----
start() {
  local wt="${1:-}"
  local off="${2:-1}"
  setup "$off"

  [[ -d "$wt" ]] || { echo "[fail] worktree 不存在: $wt"; exit 1; }
  [[ -d "$wt/apps/django" && -d "$wt/web/app" ]] || { echo "[fail] $wt 不是 ATS 前端+后端 worktree"; exit 1; }
  if lsof -nP -iTCP:$BE_PORT -sTCP:LISTEN >/dev/null 2>&1; then echo "[fail] 后端端口 $BE_PORT 已被占用"; exit 1; fi
  if lsof -nP -iTCP:$FE_PORT -sTCP:LISTEN >/dev/null 2>&1; then echo "[fail] 前端端口 $FE_PORT 已被占用"; exit 1; fi
  if [[ ! -f "$wt/apps/django/.env" ]]; then
    echo "[fail] 缺少 $wt/apps/django/.env (含 DATABASE_URL 等)。请先放置 .env 后再启动。"; exit 1
  fi
  if [[ ! -d "$wt/web/app/node_modules" ]]; then
    if [[ -d "$REF_NM" ]] && diff -q "$wt/web/app/package.json" "$REF_WT/web/app/package.json" >/dev/null 2>&1; then
      echo "[info] 软链复用参考 worktree 的 node_modules (package.json 一致)"
      ln -s "$REF_NM" "$wt/web/app/node_modules"
    else
      echo "[fail] $wt/web/app/node_modules 缺失且无法复用, 请先在该 worktree 执行 npm install"; exit 1
    fi
  fi

  echo "=== 启动 worktree 预览栈 (offset=$off) ==="
  echo "  worktree : $wt"
  echo "  后端     : http://localhost:$BE_PORT/api/v1/"
  echo "  前端     : http://localhost:$FE_PORT/"

  write_be_plist "$wt"
  write_fe_plist "$wt"
  plutil -lint "$BE_PLIST" >/dev/null && plutil -lint "$FE_PLIST" >/dev/null || { echo "[fail] plist 校验失败"; exit 1; }

  # 先 bootout 残留, 再 bootstrap (launchd 托管, 命令结束后仍存活)
  launchctl bootout "gui/$UID_NUM/$BE_LABEL" 2>/dev/null || true
  launchctl bootout "gui/$UID_NUM/$FE_LABEL" 2>/dev/null || true
  launchctl bootstrap "gui/$UID_NUM" "$BE_PLIST" || { echo "[fail] bootstrap $BE_LABEL"; exit 1; }
  launchctl bootstrap "gui/$UID_NUM" "$FE_PLIST" || { echo "[fail] bootstrap $FE_LABEL"; exit 1; }

  sleep 7
  if lsof -nP -iTCP:$BE_PORT -sTCP:LISTEN >/dev/null 2>&1; then echo "✅ 后端已监听 :$BE_PORT"; else echo "❌ 后端未起来, 日志: $be_log"; tail -12 "$be_log" | grep -vE "DEBUG|SELECT|INSERT|UPDATE" | tail -6; fi
  if lsof -nP -iTCP:$FE_PORT -sTCP:LISTEN >/dev/null 2>&1; then echo "✅ 前端已监听 :$FE_PORT"; else echo "❌ 前端未起来, 日志: $fe_log"; tail -12 "$fe_log"; fi
  echo ""
  echo "停止: bash $0 stop $off"
}

# ---- stop ----
stop() {
  local off="${1:-1}"
  setup "$off"
  for lbl in "$BE_LABEL" "$FE_LABEL"; do
    launchctl bootout "gui/$UID_NUM/$lbl" 2>/dev/null && echo "[ok] bootout $lbl" || true
  done
  rm -f "$BE_PLIST" "$FE_PLIST"
  echo "[done] offset $off 已停止"
}

# ---- ls ----
list() {
  echo "=== 运行中的 devstack 预览栈 ==="
  shopt -s nullglob
  local any=0
  for f in "$LAUNCH_DIR"/com.ats.devstack.be.*.plist; do
    any=1
    off="$(basename "$f" .plist | sed 's/com.ats.devstack.be.//')"
    bp=$((8000 + off)); fp=$((5212 + 2 * off))
    be="$(lsof -nP -iTCP:$bp -sTCP:LISTEN -t 2>/dev/null | head -1 || echo '-')"
    fe="$(lsof -nP -iTCP:$fp -sTCP:LISTEN -t 2>/dev/null | head -1 || echo '-')"
    echo "offset=$off  be:800$off(PID ${be:-down})  fe:521$fp(PID ${fe:-down})"
  done
  [[ $any -eq 0 ]] && echo "(无运行中的预览栈)"
}

case "${1:-help}" in
  start) shift; start "$@" ;;
  stop)  shift; stop "$@" ;;
  ls)    list ;;
  help|-h|--help) usage 0 ;;
  *)     usage 1 ;;
esac
