"""Regression: 验证 4 层 scope 堆栈各 layer 单独工作.
T24: L1 user / L2 role / L3 tenant / L4 SELF.
"""
import pytest


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_l4_self_fallback_when_no_data():
    """无任何 V2 配置 → 兜底 SELF (返回空 management_unit_ids)."""
    from apps.core.scope_resolver import resolve_scope
    from django.contrib.auth import get_user_model

    User = get_user_model()
    u = User.objects.create_user(username='u1', password='x')
    result = resolve_scope(u, 'recruit:candidate:list')
    assert result == {'management_unit_ids': []}


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_anonymous_returns_empty():
    from apps.core.scope_resolver import resolve_scope
    result = resolve_scope(None, 'recruit:candidate:list')
    assert result == {'management_unit_ids': []}


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_has_perm_anonymous_false():
    from apps.core.permission_check import has_perm
    assert has_perm(None, 'recruit:candidate:list') is False


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_has_perm_v2_schema_guard():
    """V2 schema 未应用 → has_perm 保守 False, 不 crash."""
    from apps.core.permission_check import has_perm
    from django.contrib.auth import get_user_model

    User = get_user_model()
    u = User.objects.create_user(username='u2', password='x', is_staff=False)
    # 无任何 V2 grants
    assert has_perm(u, 'recruit:candidate:list') is False


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_has_perm_superuser_bypass():
    from apps.core.permission_check import has_perm
    from django.contrib.auth import get_user_model

    User = get_user_model()
    u = User.objects.create_user(username='su', password='x', is_superuser=True)
    assert has_perm(u, 'recruit:candidate:list') is True


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_has_perm_super_admin_role_bypass():
    """#1 清理: 持有 SUPER_ADMIN 角色的非超管用户也走通同一评估路径.

    is_super_admin 是 is_superuser 的超集 —— 替换绝不收窄现有超管权限,
    仅额外让显式持有 SUPER_ADMIN 角色的用户也全放行 (与 is_superuser 等价).
    锁定: 即便没有任何 RolePermissionV2 显式授权, SUPER_ADMIN 角色仍 has_perm=True.
    """
    from apps.core.permission_check import has_perm
    from apps.core.role_v2_query import is_super_admin
    from apps.core.models_permission_v2 import UserRoleV2
    from django.contrib.auth import get_user_model

    User = get_user_model()
    u = User.objects.create_user(username='sar', password='x', is_superuser=False)
    UserRoleV2.objects.create(user_id=u.pk, role_code='SUPER_ADMIN', system_code='recruit')
    assert is_super_admin(u) is True
    assert has_perm(u, 'recruit:candidate:list') is True
    assert has_perm(u, 'recruit:offer:export') is True


# ===== P0-3 fail-open 回归锁定 (CODE_QUALITY_AUDIT P0-3) =====
from unittest.mock import patch
from django.db.utils import OperationalError


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_l1_db_error_fail_closed_to_self():
    """P0-3: L1 user_roles 查询抛 OperationalError → fail-closed SELF, 不落到 L3 的 ALL."""
    from apps.core.scope_resolver import resolve_scope
    from django.contrib.auth import get_user_model

    User = get_user_model()
    u = User.objects.create_user(username='l1fail', password='x')
    with patch(
        'apps.core.scope_resolver.UserRoleV2.objects.filter',
        side_effect=OperationalError('simulated L1 failure'),
    ):
        result = resolve_scope(u, 'recruit:candidate:list')
    assert result == {'management_unit_ids': []}


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_l2_db_error_fail_closed_to_self():
    """P0-3: L2 roles 查询抛 OperationalError → fail-closed SELF, 不落 L3 的 ALL."""
    from apps.core.scope_resolver import resolve_scope
    from apps.core.models_permission_v2 import UserRoleV2
    from django.contrib.auth import get_user_model

    User = get_user_model()
    u = User.objects.create_user(username='l2fail', password='x')
    UserRoleV2.objects.create(user_id=u.pk, role_code='SOME_ROLE', system_code='recruit')
    with patch(
        'apps.core.scope_resolver.RoleV2.objects.filter',
        side_effect=OperationalError('simulated L2 failure'),
    ):
        result = resolve_scope(u, 'recruit:candidate:list')
    assert result == {'management_unit_ids': []}


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_l3_tenant_all_still_grants_when_no_error():
    """回归保护: 无异常时 L3 租户 GLOBAL_DEFAULT_DATA_SCOPE='ALL' 仍正常放行 (修复未误伤 happy path)."""
    from apps.core.scope_resolver import resolve_scope
    from apps.core.models_permission_v2 import TenantConfig
    from django.contrib.auth import get_user_model

    User = get_user_model()
    u = User.objects.create_user(username='tenantall', password='x')
    TenantConfig.objects.create(
        config_key='GLOBAL_DEFAULT_DATA_SCOPE', system_code='recruit',
        config_value='ALL', description='test',
    )
    result = resolve_scope(u, 'recruit:candidate:list')
    assert result == {'all': True}
