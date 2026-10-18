"""登录接口安全回归测试 —— Fix 1 (审计 P3): 统一登录 401 + 消除 N+1.

证明:
- 账号不存在 / 密码错误 / 未激活但密码错误 → 同一通用 401 invalid_credentials,
  攻击者无密码时无法借 403/401 区分账号是否存在 (消除"账号存在性枚举"信号)。
- 仅当密码正确后, 才对非已激活账号返回 403 (account_pending / account_disabled),
  合法用户(掌握密码者)可见, 不泄露账号存在性。
- 单条 ORM 查询定位账号 (无 4 次串行 User.objects.get + check_password 的 N+1)。

2026-10-18 兵哥：用户状态改三态（PENDING/ACTIVE/DISABLED），原「注册申请
PENDING/REJECTED」语义已随自助注册下线而移除 —— 待激活账号现在可走
「邮箱验证码登录」激活，故 account_rejected 分支不再存在，改由 account_disabled 承担。
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

BASE = '/api/v1/auth'
# 合规强密码 (长度≥12 + 大小写+数字+符号)
STRONG_PASSWORD = 'Str0ng!Pass#2026v2'


@pytest.mark.django_db
class TestLoginEnumerationUnified401:
    def _make_inactive_user(self, username, status='PENDING'):
        User = get_user_model()
        user = User(username=username, email=f'{username}@corp.com')
        user.set_password(STRONG_PASSWORD)
        user.set_activation_status(status)
        user.save()
        return user

    def test_nonexistent_account_returns_401(self):
        """不存在的账号 → 401 (与密码错误无法区分, 不泄露账号存在性)."""
        c = APIClient()
        r = c.post(f'{BASE}/login/',
                   {'username': 'ghost@corp.com', 'password': 'whatever-wrong'},
                   format='json')
        assert r.status_code == 401, r.content
        assert r.json()['code'] == 'invalid_credentials'

    def test_active_account_wrong_password_returns_401(self):
        User = get_user_model()
        User.objects.create_user(username='active_ok', email='active_ok@corp.com',
                                 password=STRONG_PASSWORD, is_active=True)
        c = APIClient()
        r = c.post(f'{BASE}/login/',
                   {'username': 'active_ok', 'password': 'WrongPass#9999'},
                   format='json')
        assert r.status_code == 401, r.content
        assert r.json()['code'] == 'invalid_credentials'

    def test_inactive_pending_wrong_password_returns_401_not_403(self):
        """枚举修复核心: 未激活 + 错误密码必须 401, 不得暴露 403 (账号存在信号)."""
        self._make_inactive_user('pending_wrong', status='PENDING')
        c = APIClient()
        r = c.post(f'{BASE}/login/',
                   {'username': 'pending_wrong', 'password': 'WrongPass#9999'},
                   format='json')
        assert r.status_code == 401, r.content
        assert r.json()['code'] == 'invalid_credentials'

    def test_inactive_rejected_wrong_password_returns_401_not_403(self):
        """枚举修复核心: 已停用 + 错误密码必须 401, 不得暴露 403 (账号存在信号)."""
        self._make_inactive_user('rejected_wrong', status='DISABLED')
        c = APIClient()
        r = c.post(f'{BASE}/login/',
                   {'username': 'rejected_wrong', 'password': 'WrongPass#9999'},
                   format='json')
        assert r.status_code == 401, r.content
        assert r.json()['code'] == 'invalid_credentials'

    def test_inactive_pending_correct_password_returns_403_account_pending(self):
        """合法用户(掌握密码)可见状态: 待激活 + 正确密码 → 403 account_pending."""
        self._make_inactive_user('pending_right', status='PENDING')
        c = APIClient()
        r = c.post(f'{BASE}/login/',
                   {'username': 'pending_right', 'password': STRONG_PASSWORD},
                   format='json')
        assert r.status_code == 403, r.content
        assert r.json()['code'] == 'account_pending'

    def test_disabled_correct_password_returns_403_account_disabled(self):
        """已停用 + 正确密码 → 403 account_disabled（原 account_rejected 语义已下线）."""
        self._make_inactive_user('rejected_right', status='DISABLED')
        c = APIClient()
        r = c.post(f'{BASE}/login/',
                   {'username': 'rejected_right', 'password': STRONG_PASSWORD},
                   format='json')
        assert r.status_code == 403, r.content
        assert r.json()['code'] == 'account_disabled'

    def test_active_correct_password_logs_in(self):
        User = get_user_model()
        User.objects.create_user(username='active_login', email='active_login@corp.com',
                                 password=STRONG_PASSWORD, is_active=True)
        c = APIClient()
        r = c.post(f'{BASE}/login/',
                   {'username': 'active_login', 'password': STRONG_PASSWORD},
                   format='json')
        assert r.status_code == 200, r.content
        assert 'access' in r.json()['data']
