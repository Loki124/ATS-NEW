#!/usr/bin/env bash
# =============================================================================
# ATS-NEW dev 服务 launchd 开机保活 安装脚本
# -----------------------------------------------------------------------------
# 作用：登录 Mac 时自动拉起 vite(5212) + django(8000)，不依赖 WorkBuddy 会话，
#       关窗/登出照常存活；崩溃或"活着但不健康"均自动重启；连续失败不可恢复时
#       弹 macOS 通知并停止重启（交还人工介入）。
# 安装：bash scripts/install_dev_launchd.sh
# 卸载：bash scripts/install_dev_launchd.sh --uninstall
# 日志：.run-logs/{vite,django}-{stdout,stderr}.log 及 .run-logs/{fe,be}-wrapper.log
# -----------------------------------------------------------------------------
# 工作原理：
#   - 写两个 plist 到 ~/Library/LaunchAgents/，由 launchd 托管（非会话任务）
#   - plist 的 ProgramArguments 调用 scripts/dev_service_wrapper.sh <fe|be>
#     （自愈包装器：探活 + 运行期看门狗 + 不可恢复通知，详见该脚本头注释）
#   - RunAtLoad=true 登录即拉起；KeepAlive.Crashed=true 包装器崩了自启；
#     KeepAlive.SuccessfulExit=false 包装器干净退出(=放弃)则不再重启
#   - WorkingDirectory 设绝对路径；包装器内部自行设置 PATH/ENV
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
CELERY="$LAUNCH_DIR/com.ats.dev.celery.plist"

uninstall() {
  for label in com.ats.dev.fe com.ats.dev.be com.ats.dev.celery; do
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
    <string>PROJECT_DIR_PLACEHOLDER/scripts/dev_service_wrapper.sh</string>
    <string>fe</string>
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
    <string>PROJECT_DIR_PLACEHOLDER/scripts/dev_service_wrapper.sh</string>
    <string>be</string>
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

cat > "$CELERY" <<'PLIST_EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.ats.dev.celery</string>
  <key>ProgramArguments</key>
  <array>
    <string>PROJECT_DIR_PLACEHOLDER/scripts/dev_service_wrapper.sh</string>
    <string>celery</string>
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
  <string>PROJECT_DIR_PLACEHOLDER/.run-logs/celery-stdout.log</string>
  <key>StandardErrorPath</key>
  <string>PROJECT_DIR_PLACEHOLDER/.run-logs/celery-stderr.log</string>
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

# 注意：macOS BSD sed 的 -i 必须带扩展名（-i.bak 形式最稳）；toybox/GNU sed 也兼容。
# 之前 "-i''" 紧贴写法在部分 macOS sed 上会把 plist 路径误判为脚本命令而报
# "extra characters at the end of l command"，故改用 -i.bak 并随后清理 .bak。
sed -i.bak "s|PROJECT_DIR_PLACEHOLDER|$PROJECT_DIR|g" "$FE" "$BE" "$CELERY"
sed -i.bak "s|NODE_BIN_PLACEHOLDER|$NODE_BIN|g" "$FE"
rm -f "$FE.bak" "$BE.bak"

plutil -lint "$FE" "$BE"

# 自愈包装器需可执行
chmod +x "$SCRIPT_DIR/dev_service_wrapper.sh"

for f in "$FE" "$BE" "$CELERY"; do
  launchctl bootout "gui/$UID_NUM/$(basename "$f" .plist)" 2>/dev/null || true
done

launchctl bootstrap "gui/$UID_NUM" "$FE" || { echo "[fail] bootstrap $FE"; exit 1; }
launchctl bootstrap "gui/$UID_NUM" "$BE" || { echo "[fail] bootstrap $BE"; exit 1; }
launchctl bootstrap "gui/$UID_NUM" "$CELERY" || { echo "[fail] bootstrap $CELERY"; exit 1; }

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