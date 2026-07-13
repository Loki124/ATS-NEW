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
