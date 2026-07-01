#!/bin/bash
# 2026-07-01 花无缺: 一键 build fe + collectstatic + restart ats-django + celery
# 适用: 改 FE 代码后跑一次, 自动让浏览器看到新版本
# 用法: bash /opt/ats/ATS-New/ops/scripts/deploy.sh [skip-build|skip-restart]
set -e

cd /opt/ats/ATS-New

# chmod 644 hermes 写的 (避免 gunicorn 600 PermissionError)
chmod -R a+rX apps/django/apps/data apps/django/apps/duplicate_check apps/django/apps/external_sync apps/django/apps/scraped_resume apps/django/apps/library 2>/dev/null || true

# 1. build FE (if not skip-build)
if [[ "${1:-}" != "skip-build" ]]; then
  echo ""
  echo "=== 1/4 build FE ==="
  if [[ -d web/app ]]; then
    cd web/app
    if [[ -f pnpm-lock.yaml ]]; then
      pnpm install --frozen-lockfile
    else
      pnpm install
    fi
    pnpm run build 2>&1 | tail -20
    cd ../..
    echo "  FE built"
  else
    echo "  WARN: web/app 不存在, 跳过"
  fi
fi

# 2. collectstatic
echo ""
echo "=== 2/4 collectstatic ==="
cd apps/django
sudo -u loki .venv/bin/python manage.py collectstatic --noinput 2>&1 | tail -5
cd ../..

# 3. fix ownership
echo ""
echo "=== 3/4 fix staticfiles ownership ==="
sudo chown -R loki:devs apps/django/staticfiles/

# 4. restart services
if [[ "${1:-}" != "skip-restart" && "${2:-}" != "skip-restart" ]]; then
  echo ""
  echo "=== 4/4 restart ats-django + celery ==="
  sudo systemctl restart ats-django
  echo "  ats-django restarted"
  sudo systemctl restart ats-celery ats-celery-beat 2>/dev/null || true
  echo "  celery restarted"
  sleep 5
  echo ""
  echo "=== health check ==="
  for url in /api/v1/health/ /static/index.html /static/assets/index-Bmejsi-I.js; do
    R=$(curl -sL -o /dev/null -w "%{http_code} %{size_download}" --max-time 5 "http://127.0.0.1:8000${url}")
    printf "  %-20s  %s\n" "$R" "$url"
  done
fi

echo ""
echo "✅ deploy done"
