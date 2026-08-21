#!/usr/bin/env bash
# =============================================================================
# ATS-NEW dev 服务 launchd 开机保活 安装脚本
# -----------------------------------------------------------------------------
# 作用：登录 Mac 时自动拉起 vite(5212) + django(8000)，崩溃自动重启
# 安装：bash scripts/install_dev_launchd.sh
# 卸载：bash scripts/install_dev_launchd.sh --uninstall
# 日志：.run-logs/{vite,django}-{stdout,stderr}.log
# -----------------------------------------------------------------------------
# 工作原理：
#   - 写两个 plist 到 ~/Library/LaunchAgents/
#   - launchctl bootstrap 装入 gui/<uid> 域（user session，不需 sudo）
#   - RunAtLoad=true 加载即拉起；KeepAlive.crashed=true 崩溃自启
#   - WorkingDirectory 设绝对路径避免 cd 漂移老问题
#   - django 的 .env 由 django-environ 在 config/settings/base.py:50 自动加载
# =============================================================================

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LAUNCH_DIR="$HOME/Library/LaunchAgents"
LOG_DIR="$PROJECT_DIR/.run-logs"
UID_NUM="$(id -u)"

mkdir -p "$LAUNCH_DIR" "$LOG_DIR"

FE="$LAUNCH_DIR/com.ats.dev.fe.plist"
BE="$LAUNCH_DIR/com.ats.dev.be.plist"

uninstall() {
  for label in com.ats.dev.fe com.ats.dev.be; do
    launchctl bootout "gui/$UID_NUM/$label" 2>/dev/null || true
  done
  rm -f "$FE" "$BE"
  echo "[uninstall] 已卸载两个 plist 并 bootout"
  exit 0
}

if [[ "${1:-}" == "--uninstall" ]]; then
  uninstall
fi

cat > "$FE" <<'PLIST_EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.ats.dev.fe</string>
  <key>ProgramArguments</key>
  <array>
    <string>PROJECT_DIR_PLACEHOLDER/web/app/node_modules/.bin/vite</string>
    <string>--port</string>
    <string>5212</string>
    <string>--host</string>
    <string>0.0.0.0</string>
  </array>
  <key>WorkingDirectory</key>
  <string>PROJECT_DIR_PLACEHOLDER/web/app</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <dict>
    <key>SuccessfulExit</key>
    <false/>
    <key>Crashed</key>
    <true/>
  </dict>
  <key>ThrottleInterval</key>
  <integer>5</integer>
  <key>StandardOutPath</key>
  <string>PROJECT_DIR_PLACEHOLDER/.run-logs/vite-stdout.log</string>
  <key>StandardErrorPath</key>
  <string>PROJECT_DIR_PLACEHOLDER/.run-logs/vite-stderr.log</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>NODE_BIN_PLACEHOLDER:/usr/local/bin:/usr/bin:/bin</string>
    <key>NODE_ENV</key>
    <string>development</string>
  </dict>
</dict>
</plist>
PLIST_EOF

cat > "$BE" <<'PLIST_EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.ats.dev.be</string>
  <key>ProgramArguments</key>
  <array>
    <string>PROJECT_DIR_PLACEHOLDER/apps/django/.venv/bin/python</string>
    <string>PROJECT_DIR_PLACEHOLDER/apps/django/manage.py</string>
    <string>runserver</string>
    <string>0.0.0.0:8000</string>
  </array>
  <key>WorkingDirectory</key>
  <string>PROJECT_DIR_PLACEHOLDER/apps/django</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <dict>
    <key>SuccessfulExit</key>
    <false/>
    <key>Crashed</key>
    <true/>
  </dict>
  <key>ThrottleInterval</key>
  <integer>5</integer>
  <key>StandardOutPath</key>
  <string>PROJECT_DIR_PLACEHOLDER/.run-logs/django-stdout.log</string>
  <key>StandardErrorPath</key>
  <string>PROJECT_DIR_PLACEHOLDER/.run-logs/django-stderr.log</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>PROJECT_DIR_PLACEHOLDER/apps/django/.venv/bin:/usr/local/bin:/usr/bin:/bin</string>
    <key>DJANGO_SETTINGS_MODULE</key>
    <string>config.settings.dev</string>
    <key>PYTHONUNBUFFERED</key>
    <string>1</string>
  </dict>
</dict>
</plist>
PLIST_EOF

# 用 sed 把 PROJECT_DIR_PLACEHOLDER / NODE_BIN_PLACEHOLDER 替换为绝对路径
NODE_BIN="$(ls -d "$HOME/.workbuddy/binaries/node/versions"/*/bin 2>/dev/null | head -1)"
[[ -z "$NODE_BIN" ]] && NODE_BIN="/usr/local/bin"

sed -i '' "s|PROJECT_DIR_PLACEHOLDER|$PROJECT_DIR|g" "$FE" "$BE"
sed -i '' "s|NODE_BIN_PLACEHOLDER|$NODE_BIN|g" "$FE"

plutil -lint "$FE" "$BE"

for f in "$FE" "$BE"; do
  launchctl bootout "gui/$UID_NUM/$(basename "$f" .plist)" 2>/dev/null || true
done

launchctl bootstrap "gui/$UID_NUM" "$FE" || { echo "[fail] bootstrap $FE"; exit 1; }
launchctl bootstrap "gui/$UID_NUM" "$BE" || { echo "[fail] bootstrap $BE"; exit 1; }

sleep 4

echo ""
echo "=== launchctl list ==="
launchctl list | grep -E "com\.ats\.dev" || echo "(none yet)"

echo ""
echo "=== listening sockets ==="
lsof -iTCP:5212 -sTCP:LISTEN 2>&1 | head -3
lsof -iTCP:8000 -sTCP:LISTEN 2>&1 | head -3

echo ""
echo "=== probe ==="
curl --noproxy '*' -s -o /dev/null -w "frontend :5212 → %{http_code}\n" http://localhost:5212/
curl --noproxy '*' -s -o /dev/null -w "backend  :8000 → %{http_code}\n" http://127.0.0.1:8000/health/

echo ""
echo "[ok] 已安装 launchd agent。下次登录/重启 Mac 自动拉起 dev 服务。"
echo "卸载：bash $SCRIPT_DIR/install_dev_launchd.sh --uninstall"
echo "日志：tail -f $LOG_DIR/vite-stdout.log 或 $LOG_DIR/django-stdout.log"