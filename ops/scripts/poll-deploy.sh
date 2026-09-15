#!/bin/bash
# ATS-NEW 轮询式自动部署 — 不依赖 Gitee webhook 的兜底触发
#
# 背景: Gitee 的 Java webhook 客户端与 Cloudflare 边缘的 TLS 1.3/ChaCha20 协商偶发失败,
#       导致 push 后自动部署静默失效。本脚本由 systemd timer 每 5 分钟调用一次,
#       主动 git fetch 对比 origin/main 与本地 HEAD, 有新增提交才触发部署。
#       服务端主动 pull, 与 Gitee→Cloudflare 的 webhook 投递完全解耦, 更稳。
#
# 逻辑:
#   1. git fetch origin $BRANCH
#   2. 对比本地 HEAD 与 origin/$BRANCH
#   3. 相同 → 静默退出(不写日志, 避免每 5 分钟刷屏)
#      不同 → 调用 webhook-deploy.sh(自带 flock 锁 + 必填变量前置检查 + 健康检查)
#
# 可覆盖的环境变量:
#   DEPLOY_DIR     仓库根, 默认 /opt/data/ATS-new
#   WEBHOOK_BRANCH 部署分支, 默认 main
#   LOG_FILE       本脚本日志, 默认 /var/log/ats-poll-deploy.log
#   DEPLOY_SCRIPT  被调用的部署脚本, 默认同目录 webhook-deploy.sh

set -o pipefail

DEPLOY_DIR="${DEPLOY_DIR:-/opt/data/ATS-new}"
BRANCH="${WEBHOOK_BRANCH:-main}"
LOG_FILE="${LOG_FILE:-/var/log/ats-poll-deploy.log}"
DEPLOY_SCRIPT="${DEPLOY_SCRIPT:-$DEPLOY_DIR/ops/scripts/webhook-deploy.sh}"

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(ts)] $*" >> "$LOG_FILE"; }

mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true

cd "$DEPLOY_DIR" || { log "❌ 无法进入 $DEPLOY_DIR"; exit 1; }
[ -f "$DEPLOY_SCRIPT" ] || { log "❌ 找不到部署脚本 $DEPLOY_SCRIPT"; exit 1; }

# 1) 拉取最新
if ! git fetch origin "$BRANCH" >/dev/null 2>&1; then
  log "❌ git fetch 失败"
  exit 1
fi

# 2) 对比本地 HEAD 与 origin/BRANCH
LOCAL=$(git rev-parse HEAD 2>/dev/null)
REMOTE=$(git rev-parse "origin/$BRANCH" 2>/dev/null)
[ -n "$LOCAL" ] && [ -n "$REMOTE" ] || { log "❌ 无法解析 commit"; exit 1; }

if [ "$LOCAL" = "$REMOTE" ]; then
  exit 0   # 无新增提交, 静默退出
fi

log "检测到新提交 $LOCAL → $REMOTE, 触发部署"
# 调用部署脚本: 自带 flock 锁(防重叠)+ 必填变量前置检查 + build/up/健康检查;
# 其详细日志进 /var/log/ats-deploy.log, 这里只留触发记录。
WEBHOOK_BRANCH="$BRANCH" bash "$DEPLOY_SCRIPT" >> "$LOG_FILE" 2>&1
_RC=$?
if [ "$_RC" -eq 0 ]; then
  log "部署完成 (rc=0)"
else
  log "部署失败 (rc=$_RC), 修复后 push 新提交即可由下轮自动重试"
fi
exit "$_RC"
