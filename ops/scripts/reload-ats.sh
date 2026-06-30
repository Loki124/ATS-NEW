#!/bin/bash
# v4 修 Django 嵌套 include regex search bug (commit d8ee6df2)
set -e

chmod 644 /opt/ats/ATS-New/apps/django/apps/data/apps.py
chmod 644 /opt/ats/ATS-New/apps/django/apps/duplicate_check/apps.py
chmod 644 /opt/ats/ATS-New/apps/django/apps/external_sync/apps.py
chmod 644 /opt/ats/ATS-New/apps/django/apps/scraped_resume/apps.py

: > /var/log/ats/gunicorn-error.log
: > /var/log/ats/gunicorn-access.log

sudo systemctl restart ats-django
sudo systemctl restart ats-celery ats-celery-beat

sleep 6

systemctl status ats-django --no-pager | head -12

echo ""
echo "=== 验证 8 个 endpoint (期望 200/405) ==="
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

for url in   "/api/v1/candidates"   "/api/v1/invitations"   "/api/v1/interviews"   "/api/v1/library/schools"   "/api/v1/scraped-resumes"   "/api/v1/external-sync/syncs"   "/api/v1/data/kpi/"   "/api/v1/users"; do
  R=$(curl -sL -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $TOKEN" \
    -H 'Content-Type: application/json' \
    -X GET --max-time 5 "http://127.0.0.1:8000${url}")
  printf "  %-3s  %s\n" "$R" "$url"
done
