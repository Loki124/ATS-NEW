#!/bin/bash
# v5 强制 reload - 之前 reload 没杀掉老 master
set -e

# chmod 644 hermes 写的
chmod 644 /opt/ats/ATS-New/apps/django/apps/data/apps.py 2>/dev/null || true
chmod 644 /opt/ats/ATS-New/apps/django/apps/duplicate_check/apps.py 2>/dev/null || true
chmod 644 /opt/ats/ATS-New/apps/django/apps/external_sync/apps.py 2>/dev/null || true
chmod 644 /opt/ats/ATS-New/apps/django/apps/scraped_resume/apps.py 2>/dev/null || true

: > /var/log/ats/gunicorn-error.log
: > /var/log/ats/gunicorn-access.log

# systemctl restart 实际是 stop + start
sudo systemctl restart ats-django
echo "ats-django restarted"
sudo systemctl restart ats-celery ats-celery-beat
echo "celery restarted"

sleep 6

systemctl status ats-django --no-pager | head -12

echo ""
echo "=== 验证 9 个 endpoint ==="
TOKEN=$(sudo -u loki /opt/ats/ATS-New/apps/django/.venv/bin/python -c "
import sys
sys.path.insert(0, '/opt/ats/ATS-New/apps/django')
import django, os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.prod'
django.setup()
from apps.core.models import User
from rest_framework_simplejwt.tokens import RefreshToken
u = User.objects.get(username='admin')
print(RefreshToken.for_user(u).access_token)
" 2>/dev/null)

if [ -z "$TOKEN" ]; then
  echo "ERROR: token gen failed"
  exit 1
fi

for url in \
  "/api/v1/candidates/" \
  "/api/v1/invitations/" \
  "/api/v1/users/" \
  "/api/v1/library/schools/" \
  "/api/v1/data/kpi/" \
  "/api/v1/scraped-resumes" \
  "/api/v1/external-sync/syncs" \
  "/api/v1/duplicate-check/check" \
  "/api/v1/invitations/transition"; do
  R=$(curl -sL -o /dev/null -w "%{http_code}" \\
    -H "Authorization: Bearer $TOKEN" \\
    -H 'Content-Type: application/json' \\
    -X GET --max-time 5 "http://127.0.0.1:8000${url}")
  printf "  %-3s  %s\\n" "$R" "$url"
done
