"""权限提升链路回归测试.

被防住的攻击链 (2026-10-08 审查发现):
    1. 攻击者持有 recruit:user_role:list (招聘总经理模板自带)
    2. POST /api/v1/user-roles/  {"user_id": <自己>, "role_code": "SUPER_ADMIN"}
    3. role_v2_query.is_super_admin() 对 SUPER_ADMIN 角色持有者返回 True
    4. → 在所有 V2Permission / ScopeQuerysetMixin 处 bypass, 接管全量 RBAC 与业务数据

两道防线:
    防线 A (permissions_v2): create 必须持 :create 码, 而不是 :list
    防线 B (serializers_permission_v2): SUPER_ADMIN 只能由 Django is_superuser 授予
"""
import pytest
from rest_framework.test import APIRequestFactory

from apps.core import permissions_v2 as pv2
from apps.core.serializers_permission_v2 import UserRoleSerializer

# ---------------------------------------------------------------- 防线 B

class _Req:
    def __init__(self, user):
        self.user = user


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_super_admin_cannot_be_granted_by_role_holder(db):
    """持 SUPER_ADMIN **角色**的人不得再授 SUPER_ADMIN 出去 (防特权扩散)。"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    actor = User.objects.create(username='actor_role_admin', is_active=True)
    # actor 只通过 V2 角色持 SUPER_ADMIN, 不是 Django is_superuser
    assert actor.is_superuser is False

    ser = UserRoleSerializer(
        data={'user_id': actor.id, 'role_code': 'SUPER_ADMIN', 'system_code': 'recruit'},
        context={'request': _Req(actor)},
    )
    assert ser.is_valid() is False
    assert 'role_code' in ser.errors
    assert 'SUPER_ADMIN' in str(ser.errors['role_code'])


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_super_admin_can_be_granted_by_django_superuser(db):
    """真正的 Django 超级管理员可以授予 SUPER_ADMIN。"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    su = User.objects.create(
        username='true_su', is_active=True, is_superuser=True,
    )
    ser = UserRoleSerializer(
        data={'user_id': su.id, 'role_code': 'SUPER_ADMIN', 'system_code': 'recruit'},
        context={'request': _Req(su)},
    )
    ser.is_valid()
    assert 'role_code' not in (ser.errors or {})


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_normal_role_unaffected(db):
    """普通角色授权不受影响, 防线 B 不误伤。"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    actor = User.objects.create(username='actor_plain', is_active=True)

    ser = UserRoleSerializer(
        data={'user_id': actor.id, 'role_code': 'HR', 'system_code': 'recruit'},
        context={'request': _Req(actor)},
    )
    ser.is_valid()
    assert 'role_code' not in (ser.errors or {})


# ---------------------------------------------------------------- 防线 A

@pytest.mark.django_db
@pytest.mark.v2_permission
def test_user_role_create_requires_create_code_not_list(db, monkeypatch):
    """只持 user_role:list 时, POST /user-roles/ 必须被拒。"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.create(username='esc_actor', is_active=True)

    monkeypatch.setattr(
        pv2, 'known_resource_codes',
        lambda: {'recruit:user_role:list', 'recruit:user_role:create'},
    )
    asked = []
    monkeypatch.setattr(
        pv2, 'has_perm',
        lambda u, code: (asked.append(code), code == 'recruit:user_role:list')[1],
    )

    class _View:
        permission_classes = []
        action = 'create'
        permission_required = 'recruit:user_role:list'
        permission_required_map = None
        v2_self_service_actions = ()

    req = APIRequestFactory().post('/api/v1/user-roles/')
    req.user = user

    assert pv2.V2Permission().has_permission(req, _View()) is False
    assert asked == ['recruit:user_role:create']


# ---------------------------------------------------------------- 端到端

@pytest.mark.django_db
@pytest.mark.v2_permission
def test_escalation_endpoint_returns_403_for_list_only_user(db, hr_user):
    """端到端: 只有列表权限的用户 POST /api/v1/user-roles/ → 403, 且未落库。"""
    from rest_framework.test import APIClient

    from apps.core.models_permission_v2 import UserRoleV2

    client = APIClient()
    client.force_authenticate(user=hr_user)

    before = UserRoleV2.objects.count()
    resp = client.post('/api/v1/user-roles/', {
        'user_id': hr_user.id,
        'role_code': 'SUPER_ADMIN',
        'system_code': 'recruit',
    }, format='json')

    assert resp.status_code in (400, 403), resp.content
    assert UserRoleV2.objects.count() == before
