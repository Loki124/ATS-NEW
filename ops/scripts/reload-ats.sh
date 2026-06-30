#!/bin/bash
# Stage B/C 验证 v3 - 修 hermes 写的 600 + reload + 测 5 个 stub
set -e

# 1. hermes 自己写的 4 个 apps.py 是 600 (其他用户读不到)
chmod 644 /opt/ats/ATS-New/apps/django/apps/data/apps.py
chmod 644 /opt/ats/ATS-New/apps/django/apps/duplicate_check/apps.py
chmod 644 /opt/ats/ATS-New/apps/django/apps/external_sync/apps.py
chmod 644 /opt/ats/ATS-New/apps/django/apps/scraped_resume/apps.py
echo "OK chmod 644 修了 4 个 apps.py"

# 2. truncate log
: > /var/log/ats/gunicorn-error.log
: > /var/log/ats/gunicorn-access.log
echo "OK log truncated"

# 3. restart
sudo systemctl restart ats-django
echo "OK ats-django restarted"
sudo systemctl restart ats-celery ats-celery-beat
echo "OK celery restarted"

# 4. wait for gunicorn boot
sleep 6

echo ""
echo "=== status ==="
systemctl status ats-django --no-pager | head -12

# 5. 验证 (admin token)
echo ""
echo "=== 验证 5 个新 stub app + 双层 fix ==="
TOKEN=$(sudo -u loki /opt/ats/ATS-New/apps/django/.venv/bin/python -c "
import sys
sys.path.insert(0, '/opt/ats/ATS-New/apps/django')
import django
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.prod'
django.setup()
from apps.core.models import User
from rest_framework_simplejwt.tokens import RefreshToken
u = User.objects.get(username='admin')
print(RefreshToken.for_user(u).access_token)
" 2>/dev/null)

if [ -z "$TOKEN" ]; then
  echo "ERROR: token gen failed (gunicorn 还没起来, 看 gunicorn-error.log)"
  exit 1
fi

echo "token: ${TOKEN:0:30}..."
echo ""

for url in \
  "/api/v1/library/schools" \
  "/api/v1/scraped-resumes" \
  "/api/v1/external-sync/syncs" \
  "/api/v1/duplicate-check/check" \
  "/api/v1/data/kpi/" \
  "/api/v1/candidates" \
  "/api/v1/invitations" \
  "/api/v1/health/"; do
  R=$(curl -sL -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $TOKEN" \
    -H 'Content-Type: application/json' \
    -X GET --max-time 5 "http://127.0.0.1:8000${url}")
  printf "  %-3s  %s\n" "$R" "$url"
done

echo ""
echo "=== 期望 ==="
echo "  /api/v1/library/*         200 (stub 返空 data)"
echo "  /api/v1/scraped-resumes  200 (空 list)"
echo "  /api/v1/external-sync/*   200 (空 list)"
echo "  /api/v1/duplicate-check/* 405 (POST-only, GET 405 路由 OK)"
echo "  /api/v1/data/kpi/         200 (KPI stub)"
echo "  /api/v1/candidates        200 (双层 fix 生效)"
echo "  /api/v1/invitations       200"
echo "  /api/v1/health/           200"
