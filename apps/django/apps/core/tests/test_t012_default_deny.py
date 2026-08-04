"""T01.2 默认 deny-by-default 回归测试 (2026-08-04 寇豆码)

5 个回归测试锁死 Phase 2 T01.2 引入的默认 deny 行为:
- IsAuthenticatedDenyByDefault 在 view 未声明 permission_classes 时拒绝所有非超管
- superuser bypass
- ATSSEC_DRY_RUN=True 时打 warning 日志但放行
- ResourceScoped 缺少 resource_code 必 deny
- ResourceScoped + resource_code 走 scope_resolver (superuser 直接通过)

设计: 临时把 module 自己作为 ROOT_URLCONF 用 override_settings 注入 3 个 stub view,
绕过真实 URL 路由污染. 测完用 `with override_settings(...)` 自动还原.

为什么不用 pytest.urls / module-level pytestmark:
- 整个 apps/core/tests/ 下 8 个兄弟文件都依赖默认 ROOT_URLCONF, 用全局 marker 会
  改其他文件的 URL 解析行为, 引发连锁失败.
- override_settings 范围仅限单 test, 退出时 Django 自动还原, 零副作用.

为什么不直接用 APIView.as_view()(request) 不挂 URL:
- T01.2 的核心断言是 DRF 的 URL 路由 → permission_classes 兜底链路, 跳过 URL 等于
  跳过最常被踩坑的那一截. 必须端到端走 HTTP.
"""
import logging
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import path
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.test import APIClient
from rest_framework.views import APIView

from apps.core.permissions import IsAuthenticatedDenyByDefault, ResourceScoped

User = get_user_model()


# ============================================================
# Test fixture: 普通用户 + superuser
# ============================================================
@pytest.fixture
def regular_user(db):
    return User.objects.create_user(
        username='t012_regular',
        password='x',
        is_staff=False,
        is_superuser=False,
    )


@pytest.fixture
def super_user(db):
    return User.objects.create_user(
        username='t012_super',
        password='x',
        is_staff=True,
        is_superuser=True,
    )


# ============================================================
# Stub views: 每个 view 单独测一种 deny 行为
# ============================================================
class _UnconfiguredView(APIView):
    """不声明 permission_classes → 走全局 DEFAULT_PERMISSION_CLASSES = IsAuthenticatedDenyByDefault.

    注释里绝不写 permission_classes = [...], 这是这条用例要锁死的"漏声明"行为.
    """
    def get(self, request):
        return Response({'ok': True})


class _ScopedNoCodeView(APIView):
    """声明 ResourceScoped 但没声明 resource_code → 必须 deny (因为 ResourceScoped 把 resource_code 作为输入)."""
    permission_classes = [ResourceScoped]
    def get(self, request):
        return Response({'ok': True})


class _ScopedWithCodeView(APIView):
    """声明 ResourceScoped + resource_code → superuser bypass, 普通用户走 scope_resolver."""
    permission_classes = [ResourceScoped]
    resource_code = 'recruit:candidate:list'
    def get(self, request):
        return Response({'ok': True})


# ============================================================
# Test-only URLConf: 3 个 view 挂到 /api/v1/t012/* 路径
# ============================================================
urlpatterns = [
    path('api/v1/t012/unconfigured/', _UnconfiguredView.as_view(), name='t012-unconfigured'),
    path('api/v1/t012/scoped-no-code/', _ScopedNoCodeView.as_view(), name='t012-scoped-no-code'),
    path('api/v1/t012/scoped/', _ScopedWithCodeView.as_view(), name='t012-scoped'),
]


# ============================================================
# Test 1: 未声明 permission_classes 的 view, 普通登录用户 → 403
# ============================================================
@pytest.mark.django_db
def test_default_deny_blocks_unconfigured_view(regular_user):
    """核心断言: 任何 view 漏声明 permission_classes, 普通登录用户都被 403.

    背景 (T01.2): base.py DEFAULT_PERMISSION_CLASSES 已改成 IsAuthenticatedDenyByDefault,
    任何漏声明的 view 都会被这个全局默认拒绝. 这条用例防止后续有人手滑把
    DEFAULT 改回 IsAuthenticated.
    """
    client = APIClient()
    client.force_authenticate(user=regular_user)
    with override_settings(ROOT_URLCONF=__name__):
        response = client.get('/api/v1/t012/unconfigured/')
    assert response.status_code == 403, (
        f'默认 deny 应拒 403, 实际 {response.status_code}; body={response.content[:200]!r}'
    )


# ============================================================
# Test 2: 未声明 permission_classes 的 view, superuser → 200
# ============================================================
@pytest.mark.django_db
def test_default_deny_allows_superuser(super_user):
    """核心断言: superuser 永远 bypass IsAuthenticatedDenyByDefault.

    背景: IsAuthenticatedDenyByDefault 第 24-25 行显式 return True 当
    user.is_superuser=True, 这条用例锁死 bypass 行为.
    """
    client = APIClient()
    client.force_authenticate(user=super_user)
    with override_settings(ROOT_URLCONF=__name__):
        response = client.get('/api/v1/t012/unconfigured/')
    assert response.status_code == 200, (
        f'superuser 应 bypass, 实际 {response.status_code}; body={response.content[:200]!r}'
    )
    assert response.json() == {'ok': True}


# ============================================================
# Test 3: ATSSEC_DRY_RUN=True 时, 普通用户能过 + WARNING 日志
# ============================================================
@pytest.mark.django_db
def test_dry_run_mode_logs_only(regular_user, caplog):
    """核心断言: DRY_RUN=True 时默认 deny 退化为 WARNING 日志 + 放行.

    背景: IsAuthenticatedDenyByDefault 第 27-33 行检测 settings.ATSSEC_DRY_RUN,
    True 时返 True 但写 atssec WARNING 日志. 这条用例锁死"灰度发布"开关.
    """
    client = APIClient()
    client.force_authenticate(user=regular_user)
    with caplog.at_level(logging.WARNING, logger='atssec'), \
         override_settings(ROOT_URLCONF=__name__, ATSSEC_DRY_RUN=True):
        response = client.get('/api/v1/t012/unconfigured/')

    assert response.status_code == 200, (
        f'DRY_RUN=True 应放行, 实际 {response.status_code}'
    )
    # 至少应有 1 条 DRY-RUN deny warning
    deny_warnings = [r for r in caplog.records if 'DRY-RUN deny' in r.getMessage()]
    assert len(deny_warnings) >= 1, (
        f'期望 DRY-RUN deny warning, 实际 logs: {[r.getMessage() for r in caplog.records]}'
    )
    # user 标识写的是 user.pk (int), 不是 username. 校验用 id 比对更稳.
    assert f'user={regular_user.pk}' in deny_warnings[0].getMessage(), (
        f'warning 应包含 user id, 实际: {deny_warnings[0].getMessage()!r}'
    )


# ============================================================
# Test 4: ResourceScoped 缺 resource_code → 403
# ============================================================
@pytest.mark.django_db
def test_resource_scoped_requires_resource_code(regular_user):
    """核心断言: ResourceScoped 自身不假设 resource_code, 缺则 deny (fail-closed).

    背景: ResourceScoped 第 48-50 行 view.resource_code 为空时返 False, 这条
    用例锁死"显式声明" 行为, 防止有人手滑改成缺省 ALL.
    """
    client = APIClient()
    client.force_authenticate(user=regular_user)
    with override_settings(ROOT_URLCONF=__name__):
        response = client.get('/api/v1/t012/scoped-no-code/')
    assert response.status_code == 403, (
        f'ResourceScoped 缺 resource_code 应 403, 实际 {response.status_code}'
    )


# ============================================================
# Test 5: ResourceScoped + resource_code 声明正确 → superuser 通过
# ============================================================
@pytest.mark.django_db
def test_resource_scoped_passes_with_code(super_user):
    """核心断言: 正确声明 ResourceScoped + resource_code 后, superuser 走 bypass.

    背景: ResourceScoped 第 46-47 行 is_superuser 直接 True. 这条用例验证
    "A 业务端点" 模式 (recruit:candidate:list) 在超管视角下能通.
    """
    client = APIClient()
    client.force_authenticate(user=super_user)
    with override_settings(ROOT_URLCONF=__name__):
        response = client.get('/api/v1/t012/scoped/')
    assert response.status_code == 200, (
        f'超管应 bypass ResourceScoped, 实际 {response.status_code}; body={response.content[:200]!r}'
    )
    assert response.json() == {'ok': True}
