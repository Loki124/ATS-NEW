"""R2 运行时验证：真发 HTTP 请求，看字段脱敏是否真的生效。

只读脚本，不修改业务代码。用 Django test client + 内存 SQLite。
"""
import os
import sys

import django

BASE = os.path.abspath(os.path.dirname(__file__) + '/../../apps/django')
sys.path.insert(0, BASE)
os.chdir(BASE)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.test')
django.setup()

# 绕开 DiscoverRunner 的 serialize_db_to_string（它会遍历 Permission 模型
# → 触发本审计发现的 "no such table: permissions" 漂移 bug）
os.environ['DJANGO_DB_NAME'] = '/tmp/aud_acl.sqlite3'
from django.core.management import call_command  # noqa
if os.path.exists('/tmp/aud_acl.sqlite3'):
    os.remove('/tmp/aud_acl.sqlite3')
call_command('migrate', verbosity=0, run_syncdb=True)

from django.contrib.auth import get_user_model  # noqa
from rest_framework.test import APIClient  # noqa
from rest_framework_simplejwt.tokens import RefreshToken  # noqa

User = get_user_model()
from apps.candidate.models import Candidate  # noqa

PHONE = '13800001234'
EMAIL = 'victim@example.com'

# 造一个"面试官"角色用户：非 superuser、非 HR
u = User.objects.create_user(username='interviewer_audit', password='pw12345678')
c = Candidate.objects.create(
    name='审计探针候选人', phone=PHONE, email=EMAIL,
    gender='M',
)

client = APIClient()
token = RefreshToken.for_user(u)
client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')

r = client.get(f'/api/v1/candidates/{c.pk}/')
print(f'HTTP {r.status_code}')
body = r.json()
data = body.get('data', body)
print('返回字段:', {k: data.get(k) for k in ('id', 'name', 'phone', 'email')})

print('\n=== 判定 ===')
if r.status_code in (401, 403):
    print('结论: 该用户无权访问候选人详情 (权限层已拦截) — 脱敏层无需介入')
else:
    ph = str(data.get('phone', ''))
    em = str(data.get('email', ''))
    print(f'phone 原值={PHONE} 返回={ph}  → {"已脱敏 ✅" if PHONE not in ph else "❌ 明文泄露"}')
    print(f'email 原值={EMAIL} 返回={em}  → {"已脱敏 ✅" if EMAIL not in em else "❌ 明文泄露"}')

# 列表接口同样验证
r2 = client.get('/api/v1/candidates/')
b2 = r2.json()
items = b2.get('data', {}).get('results', b2.get('data', []))
if isinstance(items, dict):
    items = items.get('results', [])
print(f'\n列表 HTTP {r2.status_code}, 条目数 {len(items) if isinstance(items, list) else "?"}')
for it in (items or [])[:3]:
    if isinstance(it, dict) and it.get('id') == c.pk:
        print('  列表中该候选人:', {k: it.get(k) for k in ('id', 'name', 'phone', 'email')})

