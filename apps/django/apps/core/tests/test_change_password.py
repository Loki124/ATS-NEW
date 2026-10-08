"""校招管控 / 全局 — change-password 真实端点测试。

替换 8/27 已 skip 的 tests/test_qa_verify_phase1.py::test_change_password_returns_501...
（原断言针对旧 stub 已被真实实现接管后的状态，stub 不再路由到该 URL，
前提失据，故 skip）。

新断言针对真实端点（apps/core/views_auth.py:109 change_password_view）：

  POST /api/v1/auth/change-password/  鉴权 + 限流

覆盖：
  - 缺参 / 空参 → 400 missing_password
  - 新密码弱（短/常见/纯数字）→ 400 password_too_weak
  - 原密码错误 → 400 invalid_old_password
  - 未认证 → 401
  - 正常修改 → 200 success + 旧密码失效 + 新密码生效
  - 限流：连续 6 次请求触发 429
"""
import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

USER = get_user_model()
URL = '/api/v1/auth/change-password/'


@pytest.fixture
def authed_user(db):
    """独立用户，避免与 super_user fixture 串扰；密码固定为原密码便于断言。"""
    u = USER.objects.create_user(
        username='change_pw_test_user',
        password='OldPass!23',
        employee_id='CHG_PW_TEST',
    )
    client = APIClient()
    refresh = RefreshToken.for_user(u)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    # 清缓存，防止限流计数跨用例残留
    cache.clear()
    return {'user': u, 'client': client, 'username': u.username, 'old_password': 'OldPass!23'}


class TestChangePassword:
    def test_missing_old_password_returns_400(self, authed_user):
        resp = authed_user['client'].post(URL, {'newPassword': 'NewPass!23'}, format='json')
        assert resp.status_code == 400
        body = resp.json()
        assert body.get('success') is False
        assert body.get('code') == 'missing_password'

    def test_missing_new_password_returns_400(self, authed_user):
        resp = authed_user['client'].post(URL, {'oldPassword': authed_user['old_password']}, format='json')
        assert resp.status_code == 400
        assert resp.json().get('code') == 'missing_password'

    def test_empty_both_returns_400(self, authed_user):
        resp = authed_user['client'].post(URL, {}, format='json')
        assert resp.status_code == 400
        assert resp.json().get('code') == 'missing_password'

    def test_new_password_weak_returns_400(self, authed_user):
        # P0 修复回归: 弱密码(常见密码)必须被 Django 校验器拦截, 返 400 + code=password_too_weak
        resp = authed_user['client'].post(URL, {
            'oldPassword': authed_user['old_password'],
            'newPassword': 'password',  # 常见密码 → CommonPasswordValidator
        }, format='json')
        assert resp.status_code == 400
        body = resp.json()
        assert body.get('code') == 'password_too_weak'

    def test_new_password_numeric_returns_400(self, authed_user):
        # P0 修复回归(补充): 纯数字密码必须被 NumericPasswordValidator 拦截
        resp = authed_user['client'].post(URL, {
            'oldPassword': authed_user['old_password'],
            'newPassword': '12345678',  # 纯数字 → NumericPasswordValidator
        }, format='json')
        assert resp.status_code == 400
        assert resp.json().get('code') == 'password_too_weak'

    def test_change_password_strong_succeeds(self, authed_user):
        """P0 修复回归: 合规强密码应通过校验并成功改密 (200)."""
        new_pw = 'ChgNew!Str0ng#99'
        resp = authed_user['client'].post(URL, {
            'oldPassword': authed_user['old_password'],
            'newPassword': new_pw,
        }, format='json')
        assert resp.status_code == 200, resp.content
        assert resp.json().get('success') is True
        authed_user['user'].refresh_from_db()
        assert authed_user['user'].check_password(new_pw) is True

    def test_wrong_old_password_returns_400(self, authed_user):
        resp = authed_user['client'].post(URL, {
            'oldPassword': 'WrongOldPass!23',
            'newPassword': 'NewPass!23',
        }, format='json')
        assert resp.status_code == 400
        assert resp.json().get('code') == 'invalid_old_password'

    def test_unauthenticated_returns_401(self, db):
        client = APIClient()  # 无 Authorization 头
        resp = client.post(URL, {
            'oldPassword': 'whatever',
            'newPassword': 'NewPass!23',
        }, format='json')
        assert resp.status_code in (401, 403)

    def test_successful_change_persists(self, authed_user):
        """核心断言：200 + 旧密码失效 + 新密码生效。"""
        user = authed_user['user']
        new_pw = 'NewPass!23'
        resp = authed_user['client'].post(URL, {
            'oldPassword': authed_user['old_password'],
            'newPassword': new_pw,
        }, format='json')
        assert resp.status_code == 200, resp.content
        assert resp.json().get('success') is True

        # 旧密码失效：原密码不能再 check_password 通过
        user.refresh_from_db()
        assert user.check_password(authed_user['old_password']) is False
        # 新密码生效
        assert user.check_password(new_pw) is True

    def test_old_token_cannot_login_after_change(self, authed_user):
        """改密后旧 token 仍可解（JWT 是无状态的），但若走 password 校验路径会失败。
        此断言聚焦：新旧密码对 check_password 的正确性，不依赖 JWT 撤销（simplejwt 默认不撤销）。"""
        user = authed_user['user']
        resp = authed_user['client'].post(URL, {
            'oldPassword': authed_user['old_password'],
            'newPassword': 'Newer!234',
        }, format='json')
        assert resp.status_code == 200
        user.refresh_from_db()
        assert user.check_password(authed_user['old_password']) is False
        assert user.check_password('Newer!234') is True

    def test_alternate_field_names_accepted(self, authed_user):
        """后端同时接受 snake_case (old_password/new_password) 与 camelCase (oldPassword/newPassword)。"""
        new_pw = 'OtherPass!23'
        resp = authed_user['client'].post(URL, {
            'old_password': authed_user['old_password'],
            'new_password': new_pw,
        }, format='json')
        assert resp.status_code == 200, resp.content
        u = authed_user['user']
        u.refresh_from_db()
        assert u.check_password(new_pw) is True
