"""#19: JWT token_version 撤销机制 (改密使旧 refresh 失效) + access 有效期上限。

simplejwt 默认不撤销已签发 refresh token (无状态), 故改密/禁用后旧 refresh 仍能换新
access。本测试守护: 登录签发带 token_version 的 token; 改密后旧 refresh 刷新被拒 (401,
code=token_revoked); 未改密时刷新正常。
"""
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()
API = '/api/v1/auth'
OLD = 'Str0ng!Pass#123'
NEW = 'New@Str0ng#2026'


@pytest.fixture
def user(db):
    return User.objects.create_user(username='jwtver', password=OLD, is_active=True)


def _login(username, password):
    return APIClient().post(f'{API}/login/', {'username': username, 'password': password}, format='json')


def test_access_lifetime_capped():
    # #19: access 有效期缩至 ≤15 分钟, 压缩被盗用窗口
    assert settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds() <= 15 * 60


def test_refresh_works_after_login(user):
    r = _login('jwtver', OLD)
    assert r.status_code == 200
    refresh = r.json()['data']['refresh']
    r2 = APIClient().post(f'{API}/refresh/', {'refresh': refresh}, format='json')
    assert r2.status_code == 200
    # 刷新端点返回 simplejwt 原生响应 (无 data 信封)
    assert 'access' in r2.json()


def test_password_change_revokes_old_refresh(user):
    r = _login('jwtver', OLD)
    refresh = r.json()['data']['refresh']

    ac = APIClient()
    ac.force_authenticate(user=user)
    cp = ac.post(f'{API}/change-password/', {'oldPassword': OLD, 'newPassword': NEW}, format='json')
    assert cp.status_code == 200

    # 改密后旧 refresh 应被拒 (token_version 不匹配)。注意: 此处不要先调一次 /refresh/,
    # 否则 ROTATE_REFRESH_TOKENS 会把旧 token 进黑名单, 返回的是 unauthenticated 而非 token_revoked。
    r3 = APIClient().post(f'{API}/refresh/', {'refresh': refresh}, format='json')
    assert r3.status_code == 401
    assert r3.json()['code'] == 'token_revoked'
