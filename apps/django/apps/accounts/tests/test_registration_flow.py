"""自助注册 → 邮箱验证码 → 管理员审核 → 激活登录 全链路测试.

证明 (而非假设) :
- 注册真建 User(is_active=False) + RegistrationApplication(PENDING)
- 验证码邮件真实发出 (locmem outbox 提取 6 位码)
- 待审核登录被明确拒绝 (403 account_pending, 而非误报密码错误)
- 邮箱验证后管理员方可通过审核并激活
- 拒绝后登录 403 account_rejected
- 非超管无法审核
"""
import re

import pytest
from django.core import mail
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.accounts.models import RegistrationApplication

BASE = '/api/v1/auth'

# P0 修复合规强密码: 长度≥12 + 大小写+数字+符号, 且不在 Django 常见密码表
# (避免被 CommonPasswordValidator 判"太常见" → 400 连锁失败).
STRONG_PASSWORD = 'Str0ng!Pass#2026v2'


def _extract_code():
    """从 locmem 邮件 outbox 最后一封取 6 位验证码."""
    assert mail.outbox, '没有发出任何邮件'
    body = mail.outbox[-1].body
    m = re.search(r'(\d{6})', body)
    assert m, f'邮件正文未找到 6 位验证码: {body!r}'
    return m.group(1)


@pytest.mark.django_db
class TestRegistrationFlow:
    def test_full_flow_register_verify_approve_login(self):
        c = APIClient()
        email = 'newhire@corp.com'
        # 1) 注册
        r = c.post(f'{BASE}/register',
                   {'email': email, 'password': STRONG_PASSWORD, 'fullName': '新人'}, format='json')
        assert r.status_code == 201, r.content
        assert r.json()['success'] is True
        User = get_user_model()
        user = User.objects.get(email=email)
        assert user.is_active is False, '注册后不应直接激活'
        app = RegistrationApplication.objects.get(email=email)
        assert app.status == 'PENDING'
        assert app.email_verified is False
        assert mail.outbox, '验证码邮件未发出'

        # 2) 待审核登录被明确拒绝
        r = c.post(f'{BASE}/login/', {'username': email, 'password': STRONG_PASSWORD}, format='json')
        assert r.status_code == 403, r.content
        assert r.json()['code'] == 'account_pending'

        # 3) 验证邮箱
        code = _extract_code()
        r = c.post(f'{BASE}/verify-register-code', {'email': email, 'code': code}, format='json')
        assert r.status_code == 200, r.content
        app.refresh_from_db()
        assert app.email_verified is True
        # 复用已用验证码应失败
        r = c.post(f'{BASE}/verify-register-code', {'email': email, 'code': code}, format='json')
        assert r.status_code == 400

        # 4) 管理员通过审核 → 激活
        su = User.objects.create_superuser(username='su1', email='su1@corp.com', password='Su123456')
        c.force_authenticate(user=su)
        r = c.post(f'{BASE}/registrations/{app.id}/approve/', {}, format='json')
        assert r.status_code == 200, r.content
        user.refresh_from_db()
        assert user.is_active is True

        # 5) 激活后登录成功
        c.force_authenticate(user=None)
        r = c.post(f'{BASE}/login/', {'username': email, 'password': STRONG_PASSWORD}, format='json')
        assert r.status_code == 200, r.content
        assert 'access' in r.json()['data']

    def test_verify_wrong_code_rejected(self):
        c = APIClient()
        email = 'wrong@corp.com'
        c.post(f'{BASE}/register', {'email': email, 'password': STRONG_PASSWORD}, format='json')
        r = c.post(f'{BASE}/verify-register-code', {'email': email, 'code': '000000'}, format='json')
        assert r.status_code == 400
        assert r.json()['code'] in ('NO_CODE', 'WRONG', 'EXPIRED', 'LOCKED')
        app = RegistrationApplication.objects.get(email=email)
        assert app.email_verified is False

    def test_approve_requires_email_verified(self):
        c = APIClient()
        email = 'unverified@corp.com'
        c.post(f'{BASE}/register', {'email': email, 'password': STRONG_PASSWORD}, format='json')
        app = RegistrationApplication.objects.get(email=email)
        User = get_user_model()
        su = User.objects.create_superuser(username='su2', email='su2@corp.com', password='Su123456')
        c.force_authenticate(user=su)
        r = c.post(f'{BASE}/registrations/{app.id}/approve/', {}, format='json')
        assert r.status_code == 400
        assert r.json()['code'] == 'EMAIL_NOT_VERIFIED'
        app.user.refresh_from_db()
        assert app.user.is_active is False

    def test_reject_blocks_login(self):
        c = APIClient()
        email = 'reject@corp.com'
        c.post(f'{BASE}/register', {'email': email, 'password': STRONG_PASSWORD}, format='json')
        code = _extract_code()
        c.post(f'{BASE}/verify-register-code', {'email': email, 'code': code}, format='json')
        app = RegistrationApplication.objects.get(email=email)
        User = get_user_model()
        su = User.objects.create_superuser(username='su3', email='su3@corp.com', password='Su123456')
        c.force_authenticate(user=su)
        r = c.post(f'{BASE}/registrations/{app.id}/reject/',
                   {'reject_reason': '不符合要求'}, format='json')
        assert r.status_code == 200, r.content
        app.refresh_from_db()
        assert app.status == 'REJECTED'
        app.user.refresh_from_db()
        assert app.user.is_active is False
        # 拒绝后登录明确 403 account_rejected
        c.force_authenticate(user=None)
        r = c.post(f'{BASE}/login/', {'username': email, 'password': STRONG_PASSWORD}, format='json')
        assert r.status_code == 403
        assert r.json()['code'] == 'account_rejected'

    def test_non_superadmin_cannot_review(self):
        c = APIClient()
        email = 'normal@corp.com'
        c.post(f'{BASE}/register', {'email': email, 'password': STRONG_PASSWORD}, format='json')
        app = RegistrationApplication.objects.get(email=email)
        User = get_user_model()
        normal = User.objects.create_user(username='n1', email='n@corp.com', password='N123456')
        c.force_authenticate(user=normal)
        r = c.post(f'{BASE}/registrations/{app.id}/approve/', {}, format='json')
        assert r.status_code == 403

    def test_register_weak_password_rejected(self):
        """P0 修复回归: 注册弱/常见密码必须被 Django 校验器拦截.

        期望 400 + code=validation_error, 且 errors.password 字段带回中文提示(非空),
        且不应落库任何 RegistrationApplication.
        """
        c = APIClient()
        email = 'weak@corp.com'
        r = c.post(f'{BASE}/register',
                   {'email': email, 'password': 'password', 'fullName': '弱密码'},
                   format='json')
        assert r.status_code == 400, r.content
        body = r.json()
        assert body.get('code') == 'validation_error'
        errors = body.get('errors') or {}
        pw_msgs = errors.get('password') or []
        assert pw_msgs, f'password 字段未返回校验提示: {body!r}'
        # 弱密码不应落库任何注册申请(校验先于落库)
        assert not RegistrationApplication.objects.filter(email=email).exists()

    def test_register_strong_password_accepted(self):
        """P0 修复回归(对照): 合规强密码应通过校验, 落库 PENDING 申请并返回 201."""
        c = APIClient()
        email = 'strong@corp.com'
        r = c.post(f'{BASE}/register',
                   {'email': email, 'password': STRONG_PASSWORD, 'fullName': '强密码'},
                   format='json')
        assert r.status_code == 201, r.content
        assert r.json().get('success') is True
        assert RegistrationApplication.objects.filter(email=email, status='PENDING').exists()
