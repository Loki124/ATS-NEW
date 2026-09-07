"""N+1 运行时验证：真发 list 请求，数 SQL 条数。只读脚本。"""
import os
import sys

import django

BASE = os.path.abspath(os.path.dirname(__file__) + '/../../apps/django')
sys.path.insert(0, BASE)
os.chdir(BASE)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.test')
# 直接用已经 migrate 好的临时文件库，绕开 DiscoverRunner 的
# serialize_db_to_string（它会遍历 Permission 模型 → 触发本审计发现的
# "no such table: permissions" 漂移 bug，见 TECHNICAL_AUDIT.md）
os.environ['DJANGO_DB_NAME'] = '/tmp/aud_n1.sqlite3'
django.setup()

from django.core.management import call_command  # noqa

if os.path.exists('/tmp/aud_n1.sqlite3'):
    os.remove('/tmp/aud_n1.sqlite3')
call_command('migrate', verbosity=0, run_syncdb=True)

import contextlib  # noqa
from django.contrib.auth import get_user_model  # noqa
from django.db import connection, reset_queries  # noqa
from django.conf import settings  # noqa
from rest_framework.test import APIClient  # noqa
from rest_framework_simplejwt.tokens import RefreshToken  # noqa

settings.DEBUG = True  # 打开 query log

User = get_user_model()
u = User.objects.create_user(username='n1_probe', password='pw12345678')
u.is_superuser = True
u.is_staff = True
u.save()

client = APIClient()
client.credentials(
    HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(u).access_token}')

# 造点数据
from apps.candidate.models import Candidate  # noqa
for i in range(12):
    Candidate.objects.create(name=f'探针{i}', phone=f'1380000{i:04d}',
                             email=f'p{i}@x.com', gender='M')

PATHS = [
    '/api/v1/candidates/',
    '/api/v1/candidates/?page_size=50',
    '/api/v1/applications/',
    '/api/v1/interviews/',
    '/api/v1/offers/',
    '/api/v1/talent-pool/entries/',
    '/api/v1/campus/dimensions/',
]

print(f"{'端点':45s} {'SQL':>5s} {'重复':>5s}  {'耗时ms':>8s}")
print('-' * 72)
import time  # noqa
for p in PATHS:
    reset_queries()
    t0 = time.time()
    try:
        r = client.get(p)
        status = r.status_code
    except Exception as e:
        print(f'{p:45s}  EXC {type(e).__name__}: {e}')
        continue
    dt = (time.time() - t0) * 1000
    qs = connection.queries
    n = len(qs)
    sqls = [q['sql'] for q in qs]
    dup = n - len(set(sqls))
    print(f'{p:45s} {n:5d} {dup:5d}  {dt:8.1f}  HTTP {status}')
    if n > 25:
        print(f'    ↑ SQL 偏多。前 3 条:')
        for s in sqls[:3]:
            print(f'      {s[:150]}')

settings.DEBUG = False
