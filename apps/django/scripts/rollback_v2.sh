#!/bin/bash
# rollback_v2.sh — V2 cutover 回滚脚本
# 用法: bash rollback_v2.sh /var/backups/ats_pre_v2_TIMESTAMP.sql
set -e

BACKUP_FILE="${1:-/var/backups/ats_default.sql}"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Backup file not found: $BACKUP_FILE"
    echo "用法: bash rollback_v2.sh <backup.sql>"
    exit 1
fi

echo "=== V2 Rollback ==="
echo "Backup: $BACKUP_FILE"

# 1. 停服
if command -v systemctl >/dev/null 2>&1; then
    sudo systemctl stop ats-django || echo "⚠️  service stop failed (continue)"
fi

# 2. 还原 DB
echo "Restoring DB from backup..."
mysql -u "${MYSQL_USER:-root}" -p"${MYSQL_ROOT_PASSWORD}" "${MYSQL_DB:-ats_db}" < "$BACKUP_FILE"

# 3. 回滚代码 (用 git checkout 到 V2 commit 之前)
cd "$(dirname "$0")/.."
echo "Reverting code..."
git fetch origin 2>/dev/null || true
git checkout main 2>/dev/null || echo "⚠️  manual git checkout needed"

# 4. 重启
if command -v systemctl >/dev/null 2>&1; then
    sudo systemctl start ats-django
fi

echo "✅ Rollback done. Verify in browser."
