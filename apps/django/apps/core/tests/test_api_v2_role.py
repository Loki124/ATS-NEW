"""Tests for V2 Role ViewSet + clone-from-template."""
import pytest

# RoleV2 db_table='roles' 是 V2-deferred (DDL 在 T17), INSERT 会 'no such column: roles.role_code'
# RolePermissionV2 同理. 等 T17 schema 落地后取消 skip.


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_clone_from_template_creates_role_with_permissions(auth_client):
    from apps.core.models_permission_v2 import PermissionTemplate, RolePermissionV2, RoleV2

    PermissionTemplate.objects.create(
        system_code='recruit',
        template_code='TMPL_TEST',
        template_name='Test',
        is_system=1,
        permission_codes=['recruit:candidate:list', 'recruit:candidate:edit'],
    )
    resp = auth_client.post(
        '/api/v1/roles/clone-from-template/',
        data={'template_code': 'TMPL_TEST', 'role_code': 'recruit:east_test',
              'role_name': '测试'},
        format='json',
    )
    assert resp.status_code == 201, resp.content
    assert RoleV2.objects.filter(role_code='recruit:east_test').exists()
    rps = list(RolePermissionV2.objects.filter(role_code='recruit:east_test').values_list(
        'resource_code', flat=True,
    ))
    assert set(rps) == {'recruit:candidate:list', 'recruit:candidate:edit'}


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_template_edit_does_not_affect_cloned_role(auth_client):
    """修改模板, 已 clone 的角色不受影响 (lock 决策)"""
    from apps.core.models_permission_v2 import PermissionTemplate, RolePermissionV2

    PermissionTemplate.objects.create(
        system_code='recruit', template_code='TMPL_TEST',
        template_name='Test', is_system=1,
        permission_codes=['recruit:candidate:list'],
    )
    auth_client.post(
        '/api/v1/roles/clone-from-template/',
        data={'template_code': 'TMPL_TEST', 'role_code': 'recruit:lock_test',
              'role_name': 'Lock Test'},
        format='json',
    )
    # 改模板
    tpl = PermissionTemplate.objects.get(template_code='TMPL_TEST')
    tpl.permission_codes = ['recruit:candidate:list', 'recruit:new:menu:view']
    tpl.save()
    # 已 clone 的角色应该只有 list, 没有 new
    rps = list(RolePermissionV2.objects.filter(role_code='recruit:lock_test').values_list(
        'resource_code', flat=True,
    ))
    assert rps == ['recruit:candidate:list']