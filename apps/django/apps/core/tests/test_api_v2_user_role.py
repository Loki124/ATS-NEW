"""Tests for V2 ManagementUnit + UserRole ViewSets."""
import pytest

# UserRoleV2 db_table='user_roles' 是 V2-deferred (DDL 在 T17), INSERT 会 'no such column: user_roles.role_code'
# 等 T17 schema 落地后取消 skip.
NEEDS_T17_SCHEMA = pytest.mark.skip(reason='UserRoleV2 INSERT blocked until T17 v2 schema')


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_management_unit_list(auth_client):
    from apps.core.models_permission_v2 import ManagementUnit
    ManagementUnit.objects.create(
        system_code='recruit', unit_name='East Division', unit_type='org',
        org_scope=[1, 2, 3], include_children=1, status=1,
    )
    resp = auth_client.get('/api/v1/management-units/')
    assert resp.status_code == 200
    data = resp.json()
    items = data['data'] if isinstance(data, dict) and 'data' in data else data
    assert any(u['unitName'] == 'East Division' for u in items)


@NEEDS_T17_SCHEMA
@pytest.mark.django_db
@pytest.mark.v2_permission
def test_user_role_assign_persists_granted_by(auth_client, super_user):
    resp = auth_client.post(
        '/api/v1/user-roles/',
        data={'user_id': super_user.id, 'role_code': 'recruit:test',
              'management_unit_ids': [1, 2]},
        format='json',
    )
    assert resp.status_code == 201, resp.content
    from apps.core.models_permission_v2 import UserRoleV2
    ur = UserRoleV2.objects.get(role_code='recruit:test')
    assert ur.granted_by_id == super_user.id
    assert ur.management_unit_ids == [1, 2]


@NEEDS_T17_SCHEMA
@pytest.mark.django_db
@pytest.mark.v2_permission
def test_user_role_unique_per_user(super_user):
    """重复授权 (user_id, role_code) 应冲突"""
    from apps.core.models_permission_v2 import UserRoleV2
    UserRoleV2.objects.create(user_id=super_user.id, role_code='R1', system_code='recruit')
    with pytest.raises(Exception):  # IntegrityError
        UserRoleV2.objects.create(user_id=super_user.id, role_code='R1', system_code='recruit')