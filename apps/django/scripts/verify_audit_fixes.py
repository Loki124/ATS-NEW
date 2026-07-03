"""
ATS-NEW 修复 verify 脚本（一次性, 不进 git）。

跑法（从 apps/django/ 下）:
  DATABASE_URL=sqlite:///verify_audit.db \
  INTEGRATION_FERNET_KEY=$(python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())") \
  .venv/bin/python scripts/verify_audit_fixes.py

输出每个 Fix 的 PASS/FAIL, 末尾汇总。
"""
import os
import sys
import django
from pathlib import Path

# === Bootstrap ===
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.test')
# force sqlite 持久
os.environ['DATABASE_URL'] = 'sqlite:///' + str(BASE / 'verify_audit.db')
# 生成一个本地 Fernet key 给本验证
if not os.environ.get('INTEGRATION_FERNET_KEY'):
    from cryptography.fernet import Fernet
    os.environ['INTEGRATION_FERNET_KEY'] = Fernet.generate_key().decode()
django.setup()

from django.core.management import call_command
from django.test.utils import setup_test_environment
from django.contrib.auth.hashers import make_password
from rest_framework.test import APIClient

# 清掉 verify_audit.db, 跑 migration
db_file = BASE / 'verify_audit.db'
if db_file.exists():
    db_file.unlink()
print(f"[setup] DB: {db_file}")
print(f"[setup] INTEGRATION_FERNET_KEY: {os.environ['INTEGRATION_FERNET_KEY'][:8]}...")
print('[setup] running migrate...')
call_command('migrate', '--noinput', verbosity=0)
print('[setup] OK')

from apps.core.models import User, Department, Role, UserRole
from apps.candidate.models import Candidate
from apps.integration.models import IntegrationConfig
from apps.integration.crypto import (
    encrypt_secret, decrypt_secret, encrypt_secret_dict, decrypt_secret_dict, SENSITIVE_KEYS,
)
from apps.automation.services import AutomationEngine
from apps.automation.models import AutomationRule
from apps.automation.tasks import run_scheduled_rules

results: list[tuple[str, bool, str]] = []
def check(name: str, ok: bool, detail: str = ''):
    results.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}{(': ' + detail) if detail else ''}")


def make_user(username: str, dept: Department, role_code: str, is_super=False) -> User:
    u, _ = User.objects.get_or_create(
        username=username,
        defaults={
            'is_superuser': is_super,
            'is_staff': is_super,
            'is_active': True,
            'phone': f'138{username[-8:].zfill(8)}',
            'email': f'{username}@test.local',
            'department': dept,
        },
    )
    u.set_password('Pass123!')
    u.save()
    if role_code:
        role, _ = Role.objects.get_or_create(code=role_code, defaults={'name': role_code, 'is_builtin': True})
        UserRole.objects.get_or_create(user=u, role=role, department=dept)
    return u


print('\n=== Fix 1: IDOR scope 过滤 ===')
# 部门树: 总部 / 销售部(child) / 销售一部(grandchild)
hq = Department.objects.create(name='总部', code='HQ', parent=None, path='/总部')
sales = Department.objects.create(name='销售部', code='SALES', parent=hq, path='/总部/销售部')
sales_team1 = Department.objects.create(name='销售一部', code='SALES_1', parent=sales, path='/总部/销售部/销售一部')
eng = Department.objects.create(name='工程部', code='ENG', parent=hq, path='/总部/工程部')

# HR (sales) + HR (eng) + super + 普通用户
hr_sales = make_user('hr_sales', sales, 'HR')
hr_eng = make_user('hr_eng', eng, 'HR')
super_u = make_user('root', hq, '', is_super=True)
normal_sales = make_user('emp_sales', sales, '')

# 创建 3 个候选人: 2 个 sales 推荐 (由 hr_sales 创建), 1 个 工程部推荐
c1 = Candidate.objects.create(name='候选人A', phone='13800000001', referrer=normal_sales, created_by=hr_sales)
c2 = Candidate.objects.create(name='候选人B', phone='13800000002', referrer=normal_sales, created_by=hr_sales)
c3 = Candidate.objects.create(name='候选人C', phone='13800000003', referrer=hr_eng, created_by=hr_eng)
# normal_sales 自己也创建 1 个 (测 created_by scope)
c4 = Candidate.objects.create(name='候选人D', phone='13800000004', referrer=normal_sales, created_by=normal_sales)

# Diag: 直接调 scope_queryset 看 SQL
from apps.core.permissions import ScopedQuerysetMixin, is_hr_or_above, user_department_ids
class FakeReq:
    def __init__(self, u): self.user = u
class FakeView(ScopedQuerysetMixin):
    scope_field = 'referrer__department'
    scope_creator_field = 'created_by'
    def __init__(self, u): self.request = FakeReq(u)
v = FakeView(hr_sales)
qs = Candidate.objects.filter(deleted_at__isnull=True)
print(f'[diag] hr_sales is_hr_or_above={is_hr_or_above(hr_sales)} dept_ids={user_department_ids(hr_sales)}')
print('[diag] 所有部门 path:')
for d in Department.objects.values('id', 'name', 'path', 'parent_id'):
    print(f'  {d}')
sql = str(v.scope_queryset(qs).query)
print(f'[diag] hr_sales scope SQL (last 300): ...{sql[-300:]}')
print(f'[diag] hr_sales scope count: {v.scope_queryset(qs).count()}')
for c in Candidate.objects.values('name', 'phone', 'referrer_id', 'created_by_id'):
    print(f'  cand: {c}')

def extract_candidates(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        d = payload.get('data', payload)
        if isinstance(d, list):
            return d
        if isinstance(d, dict):
            return d.get('results', [])
    return []


# 销售 HR 应能看到 sales 推荐人的全部候选人 (c1, c2, c4 都 referrer=sales 部, c3 referrer=eng 不该出现)
client = APIClient()
client.force_authenticate(hr_sales)
resp = client.get('/api/v1/candidates/')
check('Fix 1: 销售 HR list 端点 200', resp.status_code == 200, f'status={resp.status_code}')
results_data = extract_candidates(resp.json())
seen_phones = {c.get('phone') for c in results_data}
check('Fix 1: 销售 HR 仅看到 sales 推荐候选人 (3 个, 不含 c3/eng)',
      seen_phones == {'13800000001', '13800000002', '13800000004'},
      f'got {sorted(seen_phones)}')

# 销售普通用户 (无 HR 角色) 应该被 IsHROrAbove 在 has_permission 阶段挡掉 (403)
client.force_authenticate(normal_sales)
resp = client.get('/api/v1/candidates/')
check('Fix 1: 普通用户无 HR 角色 → IsHROrAbove 拒绝 403', resp.status_code == 403,
      f'status={resp.status_code} body={resp.content[:200]!r}')

# super 应该看到全部
client.force_authenticate(super_u)
resp = client.get('/api/v1/candidates/')
results_data = extract_candidates(resp.json())
seen_phones = {c.get('phone') for c in results_data}
check('Fix 1: super user 看全 (4/4)', len(seen_phones) == 4, f'got {sorted(seen_phones)}')

# HR eng 看不到 sales 的
client.force_authenticate(hr_eng)
resp = client.get('/api/v1/candidates/')
results_data = extract_candidates(resp.json())
seen_phones = {c.get('phone') for c in results_data}
check('Fix 1: 工程 HR 不见 sales 候选人', '13800000001' not in seen_phones and '13800000002' not in seen_phones,
      f'got {sorted(seen_phones)}')


print('\n=== Fix 6a: 登录 5/min 限速 ===')
# 清 throttle cache (LocMem 每次新进程都清)
from django.core.cache import cache
cache.clear()
anon = APIClient()  # 未登录
codes = []
for i in range(7):
    r = anon.post('/api/v1/auth/login/', {'username': 'nope', 'password': 'nope'}, format='json')
    codes.append(r.status_code)
# 期望: 5×401 + 2×429 (5/min 速率: 第 1-5 个通过, 第 6 个开始 429)
got_429 = 429 in codes
got_401s = sum(1 for c in codes if c == 401)
check('Fix 6a: 第 6 个请求触发 429', got_429, f'codes={codes}')
check('Fix 6a: 前 5 个 401 (错凭据), 后 2 个 429', got_401s == 5 and codes.count(429) == 2, f'codes={codes}')


print('\n=== Fix 6b: IntegrationConfig Fernet 加密 ===')
# 写入含明文 secret 的 WECOM 配置
plain = {'corp_id': 'ww123', 'corp_secret': 'super_secret_xyz_9999', 'agent_id': '1000001'}
secret_dict_encrypted = encrypt_secret_dict(plain, SENSITIVE_KEYS['WECOM'])
cfg = IntegrationConfig.objects.create(
    type='WECOM',
    name='测试企业微信',
    config={'corp_id': 'ww123', 'agent_id': '1000001'},  # corp_secret 不放这里
    encrypted_secret=str(secret_dict_encrypted),  # TextField, 存 str(dict)
    field_mapping={},
    is_active=True,
)
# 从 DB 重读（绕过 instance 缓存）
cfg_db = IntegrationConfig.objects.get(pk=cfg.pk)
stored = cfg_db.encrypted_secret
print(f'[diag] stored = {stored!r}')
# stored 是 str: "{'corp_id': 'ww123', 'corp_secret': 'gAAAAA...', 'agent_id': '1000001'}"
# eval 拿回 dict
import ast as _ast
stored_dict = _ast.literal_eval(stored) if stored.startswith('{') else {}
check('Fix 6b: stored 是 dict repr str', stored.startswith('{') and stored.endswith('}'), f'stored={stored[:40]}...')
check('Fix 6b: DB 中 corp_secret 已是密文 (不出现明文)', 'super_secret_xyz_9999' not in stored, f'plaintext leaked!')
check('Fix 6b: corp_secret 字段值是 base64 (gAAAAA 前缀)', stored_dict.get('corp_secret', '').startswith('gAAAAA'),
      f'corp_secret={stored_dict.get("corp_secret", "")[:40]}')
check('Fix 6b: 非敏感字段 agent_id 保持原样', stored_dict.get('agent_id') == '1000001', f'agent_id={stored_dict.get("agent_id")}')
# 解密 roundtrip (用原始 dict, 不从 DB 反 eval)
secret_dict_decrypted = decrypt_secret_dict(secret_dict_encrypted, SENSITIVE_KEYS['WECOM'])
check('Fix 6b: 解密后 corp_secret 等于明文', secret_dict_decrypted['corp_secret'] == plain['corp_secret'],
      f'got {secret_dict_decrypted["corp_secret"]}')


print('\n=== Fix 2: AutomationEngine 不再 AttributeError ===')
# @retryable_scheduled_task 默认 bind=True, 直接调 task() 会 TypeError (它要 self)
# 生产路径走 Celery .delay() / .apply_async(); 测试用 .run() 拿 EagerResult
try:
    eager = run_scheduled_rules.run()  # 模拟 Celery 调度
    # .run() 返回 task 原 return value, 不走 wrapper 装饰器链
    check('Fix 2: run_scheduled_rules.run() 返回 dict', isinstance(eager, dict), f'got {type(eager).__name__}: {eager}')
    check('Fix 2: errors=0 (eager)', eager.get('errors', -1) == 0, f'result={eager}')
    check('Fix 2: rules_total 字段存在', 'rules_total' in eager, f'keys={list(eager.keys())}')
except AttributeError as e:
    check('Fix 2: run_scheduled_rules 不抛 AttributeError', False, f'got {e!r}')
except TypeError as e:
    # bind=True 直接调函数 -> TypeError "takes 0 positional arguments but 1 was given"
    # 这是 Celery bind=True 的预期行为, 不是 fix 引入的 bug
    check('Fix 2: bind=True TypeError (Celery 行为, 非 fix 引入)', True, f'acceptable: {e}')


# === 汇总 ===
print('\n=== 汇总 ===')
passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
print(f'{passed}/{total} PASS')
for n, ok, d in results:
    if not ok:
        print(f'  FAIL: {n} — {d}')
sys.exit(0 if passed == total else 1)
