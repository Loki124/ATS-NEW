"""Tests for has_perm + scope_resolver. INSERT-heavy tests skipped until T17 v2 schema."""
import pytest
from django.contrib.auth import get_user_model
from apps.core.permission_check import has_perm
from apps.core.scope_resolver import resolve_scope
from apps.core.models_permission_v2 import (
    PermissionResource, RolePermissionV2, UserRoleV2, TenantConfig,
)


User = get_user_model()


# V2 schema is applied by migrations; tests execute against real tables.


@pytest.fixture
def resource(db):
    return PermissionResource.objects.create(
        system_code='recruit',
        resource_code='recruit:test:menu:view',
        resource_name='T',
        resource_type='MENU',
        module='test',
    )


@pytest.fixture
def user(db):
    return User.objects.create(username='u', is_active=True)


@pytest.fixture
def admin_user(db):
    """Plain active user; test sets is_superuser=True explicitly."""
    return User.objects.create(username='admin_test', is_active=True)


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_has_perm_no_role_returns_false(user, resource):
    """user 无 role_codes → False (filter 不抛错, 只是空 queryset)."""
    assert has_perm(user, 'recruit:test:menu:view') is False


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_has_perm_with_single_role(user, resource):
    """1 个 role 有 resource → True; 其它 resource → False."""
    RolePermissionV2.objects.create(
        role_code='R_TEST',
        resource_code=resource.resource_code,
        system_code='recruit',
    )
    UserRoleV2.objects.create(
        user_id=user.pk, role_code='R_TEST', system_code='recruit',
    )
    assert has_perm(user, 'recruit:test:menu:view') is True
    assert has_perm(user, 'recruit:other:menu:view') is False


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_has_perm_multi_roles_union(user, resource):
    """多 role union: 任一 role 有 resource → True."""
    RolePermissionV2.objects.create(
        role_code='R_A', resource_code=resource.resource_code, system_code='recruit',
    )
    RolePermissionV2.objects.create(
        role_code='R_B', resource_code='recruit:other:button:create', system_code='recruit',
    )
    UserRoleV2.objects.create(user_id=user.pk, role_code='R_A', system_code='recruit')
    UserRoleV2.objects.create(user_id=user.pk, role_code='R_B', system_code='recruit')
    assert has_perm(user, 'recruit:test:menu:view') is True
    assert has_perm(user, 'recruit:other:button:create') is True


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_has_perm_superuser_bypass(admin_user):
    """superuser 不查 DB, 直接 True. 不需要 INSERT 任何数据."""
    assert admin_user.is_authenticated
    admin_user.is_superuser = True
    admin_user.save()
    assert has_perm(admin_user, 'recruit:anything:menu:view') is True


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_has_perm_anonymous_user_returns_false(resource):
    """未登录 user → False (不查 DB)."""
    from django.contrib.auth.models import AnonymousUser
    anon = AnonymousUser()
    assert has_perm(anon, 'recruit:test:menu:view') is False


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_scope_l1_user_explicit_priority(user, resource):
    """L1 > L2: user.management_unit_ids=[5] 覆盖 role.default=ALL."""
    from apps.core.models_permission_v2 import RoleV2
    RoleV2.objects.create(
        role_code='R_ALL', role_name='A', system_code='recruit',
        default_data_scope_type='ALL',
    )
    UserRoleV2.objects.create(
        user_id=user.pk, role_code='R_ALL', system_code='recruit',
        management_unit_ids=[5],
    )
    scope = resolve_scope(user)
    assert scope == {'management_unit_ids': [5]}, scope


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_scope_l2_role_default_all(user):
    """L2: role.default=ALL + 无 L1 → 返回 {'all': True}."""
    from apps.core.models_permission_v2 import RoleV2
    RoleV2.objects.create(
        role_code='R_ALL', role_name='A', system_code='recruit',
        default_data_scope_type='ALL',
    )
    UserRoleV2.objects.create(user_id=user.pk, role_code='R_ALL', system_code='recruit')
    scope = resolve_scope(user)
    assert scope == {'all': True}, scope


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_scope_l3_tenant_default_all(user):
    """L3: tenant_config.GLOBAL_DEFAULT_DATA_SCOPE=ALL → {'all': True}.
    TenantConfig 是正常 CreateModel 表, 不需要 T17."""
    TenantConfig.objects.create(
        system_code='recruit',
        config_key='GLOBAL_DEFAULT_DATA_SCOPE',
        config_value='ALL',
    )
    scope = resolve_scope(user)
    assert scope == {'all': True}, scope


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_scope_l4_fallback_self(user):
    """L4: 没有任何配置 → {'management_unit_ids': []} (SELF 兜底)."""
    scope = resolve_scope(user)
    assert scope == {'management_unit_ids': []}, scope


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_scope_anonymous_user():
    """未登录 → 空 list."""
    from django.contrib.auth.models import AnonymousUser
    scope = resolve_scope(AnonymousUser())
    assert scope == {'management_unit_ids': []}, scope