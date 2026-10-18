"""邮箱验证码免密登录 + 用户三态激活状态 全链路测试。

2026-10-18 兵哥（替代原「自助注册 → 管理员审核」链路）：
- 自助注册整体下线，账号只能由管理员在「用户管理」开通，默认「待激活」；
- 用户输入邮箱 → 发验证码（**先校验账号有效性**）→ 输码登录；
- 待激活账号首次验证登录后**自动激活**为已激活；
- 已停用账号发码即被拒，且不签发令牌。

证明（而非假设）:
- 发码前账号有效性校验：不存在的邮箱 404、已停用 403，均不发邮件；
- 验证码邮件真实发出（locmem outbox 提取 6 位码）；
- 待激活账号 verify 后自动激活（activation_status PENDING → ACTIVE，is_active 同步）；
- 错误验证码拒绝且不激活；复用已用验证码失败；
- 已激活账号 verify 后仍是 ACTIVE（幂等）；
- 自助注册端点已下线（/auth/register 不再 201）。
"""
import re

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from rest_framework.test import APIClient

BASE = '/api/v1/auth'
User = get_user_model()


def _extract_code():
    """从 locmem 邮件 outbox 最后一封取 6 位验证码."""
    assert mail.outbox, '没有发出任何邮件'
    body = mail.outbox[-1].body
    m = re.search(r'(\d{6})', body)
    assert m, f'邮件正文未找到 6 位验证码: {body!r}'
    return m.group(1)


def _make_user(username, status='PENDING', email=None):
    """按三态创建用户（is_active 由 set_activation_status 同步）。"""
    u = User(username=username, email=email or f'{username}@corp.com')
    u.set_password('Str0ng!Pass#2026v2')
    u.set_activation_status(status)
    u.save()
    return u


@pytest.mark.django_db
class TestSendLoginCodeAccountValidity:
    """发码前必须先校验账号有效性（兵哥 2026-10-18 明确要求）。"""

    def test_nonexistent_email_rejected_and_no_email_sent(self):
        mail.outbox.clear()
        r = APIClient().post(
            f'{BASE}/email-login/send-code', {'email': 'ghost@corp.com'}, format='json')
        assert r.status_code == 404, r.content
        assert r.json()['code'] == 'account_not_found'
        assert not mail.outbox, '账号不存在时不得发出任何邮件'

    def test_disabled_account_rejected_and_no_email_sent(self):
        _make_user('disabled_u', status='DISABLED')
        mail.outbox.clear()
        r = APIClient().post(
            f'{BASE}/email-login/send-code', {'email': 'disabled_u@corp.com'}, format='json')
        assert r.status_code == 403, r.content
        assert r.json()['code'] == 'account_disabled'
        assert not mail.outbox, '已停用账号不得发出验证码'

    def test_pending_and_active_both_can_request_code(self):
        _make_user('pending_u', status='PENDING')
        _make_user('active_u', status='ACTIVE')
        mail.outbox.clear()
        c = APIClient()
        for name in ('pending_u', 'active_u'):
            r = c.post(f'{BASE}/email-login/send-code', {'email': f'{name}@corp.com'}, format='json')
            assert r.status_code == 200, r.content
            assert r.json()['success'] is True
        assert len(mail.outbox) == 2


@pytest.mark.django_db
class TestEmailLoginActivatesPending:
    """待激活账号首次邮箱验证登录后自动激活。"""

    def test_pending_account_auto_activates_on_first_login(self):
        user = _make_user('newbie', status='PENDING')
        assert user.activation_status == 'PENDING'
        assert user.is_active is False

        c = APIClient()
        r = c.post(f'{BASE}/email-login/send-code', {'email': 'newbie@corp.com'}, format='json')
        assert r.status_code == 200, r.content
        code = _extract_code()

        r = c.post(f'{BASE}/email-login/verify',
                   {'email': 'newbie@corp.com', 'code': code}, format='json')
        assert r.status_code == 200, r.content
        body = r.json()
        assert body['success'] is True
        assert 'access' in body['data']

        user.refresh_from_db()
        assert user.activation_status == 'ACTIVE', '待激活账号验证登录后应自动激活'
        assert user.is_active is True, 'is_active 必须与 activation_status 同步'

    def test_active_account_stays_active_and_relogin_works(self):
        _make_user('veteran', status='ACTIVE')
        c = APIClient()
        c.post(f'{BASE}/email-login/send-code', {'email': 'veteran@corp.com'}, format='json')
        code = _extract_code()
        r = c.post(f'{BASE}/email-login/verify',
                   {'email': 'veteran@corp.com', 'code': code}, format='json')
        assert r.status_code == 200, r.content
        u = User.objects.get(username='veteran')
        assert u.activation_status == 'ACTIVE'

    def test_wrong_code_rejected_and_not_activated(self):
        user = _make_user('typo_u', status='PENDING')
        c = APIClient()
        c.post(f'{BASE}/email-login/send-code', {'email': 'typo_u@corp.com'}, format='json')
        r = c.post(f'{BASE}/email-login/verify',
                   {'email': 'typo_u@corp.com', 'code': '000000'}, format='json')
        assert r.status_code == 400, r.content
        assert r.json()['code'] in ('WRONG', 'NO_CODE', 'EXPIRED', 'LOCKED')
        user.refresh_from_db()
        assert user.activation_status == 'PENDING', '验证码错误不得激活账号'
        assert user.is_active is False

    def test_used_code_cannot_be_replayed(self):
        _make_user('replay_u', status='PENDING')
        c = APIClient()
        c.post(f'{BASE}/email-login/send-code', {'email': 'replay_u@corp.com'}, format='json')
        code = _extract_code()
        r = c.post(f'{BASE}/email-login/verify',
                   {'email': 'replay_u@corp.com', 'code': code}, format='json')
        assert r.status_code == 200, r.content
        # 复用已用验证码 → 失败
        r = c.post(f'{BASE}/email-login/verify',
                   {'email': 'replay_u@corp.com', 'code': code}, format='json')
        assert r.status_code == 400, r.content

    def test_disabled_account_cannot_login_even_with_valid_code(self):
        """已停用账号即便拿到有效验证码也不得签发令牌。"""
        _make_user('stopped_u', status='DISABLED')
        c = APIClient()
        # 直接插一条有效验证码（绕过发码接口的停用拦截），模拟"手上有码"的情形
        from apps.accounts.services import CODE_PURPOSE, hash_code
        from apps.accounts.models import EmailVerificationCode
        from django.utils import timezone
        from datetime import timedelta
        EmailVerificationCode.objects.create(
            email='stopped_u@corp.com', code_hash=hash_code('123456'),
            purpose=CODE_PURPOSE, expires_at=timezone.now() + timedelta(minutes=15),
        )
        r = c.post(f'{BASE}/email-login/verify',
                   {'email': 'stopped_u@corp.com', 'code': '123456'}, format='json')
        assert r.status_code == 403, r.content
        assert r.json()['code'] == 'account_disabled'
        assert 'access' not in (r.json().get('data') or {})


@pytest.mark.django_db
class TestSelfRegistrationRemoved:
    """自助注册已下线：旧端点不再可用。"""

    def test_register_endpoint_gone(self):
        r = APIClient().post(
            f'{BASE}/register', {'email': 'x@corp.com', 'password': 'Str0ng!Pass#2026v2'},
            format='json')
        assert r.status_code == 404, r.content

    def test_verify_register_code_endpoint_gone(self):
        r = APIClient().post(
            f'{BASE}/verify-register-code', {'email': 'x@corp.com', 'code': '123456'},
            format='json')
        assert r.status_code == 404, r.content

    def test_registration_list_endpoint_gone(self):
        su = User.objects.create_superuser(username='su_reg', email='su_reg@corp.com',
                                           password='Su123456')
        c = APIClient()
        c.force_authenticate(user=su)
        r = c.get(f'{BASE}/registrations/', {}, format='json')
        assert r.status_code == 404, r.content
