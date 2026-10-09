"""Batch C: core / core-v2 用户权限域信封契约测试.

锁定目标 (经逐类直读 + 路由优先级 + FE 消费方复验):
- UserViewSet (/api/v1/users/)  : list/active 已由 StandardResultsSetPagination 包信封;
                                  retrieve/create/update 原 DRF 裸返回 -> 本批套 EnvelopeWriteMixin.
- UserRoleViewSet (/api/v1/user-roles/) : list/suggest_scope 已手动信封;
                                          retrieve/create/update 原 DRF 裸返回 -> 本批套 EnvelopeWriteMixin.

排除 (不可作为收口目标):
- DepartmentViewSet           : 已手动信封 (_envelope), 勿动.
- core RoleViewSet            : 被 v2 同名类遮蔽为死代码, 勿动.
- v2 RoleViewSet              : 已手动信封, 勿动.

FE 安全性 (零改动依据):
- UserDirectory.vue 创建走 `res.data?.id || res.data?.data?.id` 回退, 编辑仅查 `res.ok`;
- UserRoleViewSet 无活动 FE 消费方 (PermissionManagement.vue 仅注释引用).
故本批 envelope 化对 FE 无破坏, 无需前端改动.

core/tests 是真实 package (__init__.py 存在), 本文件名不会触发跨 app 同名 test_envelope 收集冲突.
"""
from apps.common.tests.envelope_contract import assert_envelope
import uuid

import pytest
from django.contrib.auth import get_user_model

from apps.core.models_permission_v2 import RoleV2, UserRoleV2

User = get_user_model()

USERS_BASE = '/api/v1/users'
USER_ROLES_BASE = '/api/v1/user-roles'

# Batch L: core/v2 权限域信封契约新增端点
PERM_RESOURCES_BASE = '/api/v1/permissions/resources'
PERM_TEMPLATES_BASE = '/api/v1/permissions/templates'
ROLES_BASE = '/api/v1/roles'
MGMT_UNITS_BASE = '/api/v1/management-units'
USER_APP_DATA_SCOPES_BASE = '/api/v1/user-app-data-scopes'


@pytest.mark.django_db
def test_user_list_envelope(auth_client):
    """list 经 StandardResultsSetPagination 包 {success,data,pagination}."""
    resp = auth_client.get(USERS_BASE + '/')
    assert resp.status_code == 200, resp.content
    body = resp.json()
    assert_envelope(body)
    assert isinstance(body['data'], list)
    assert 'pagination' in body


@pytest.mark.django_db
def test_user_retrieve_envelope(auth_client, super_user):
    """retrieve 现返回 {success,data}, data.id == 用户 id."""
    resp = auth_client.get(f'{USERS_BASE}/{super_user.id}/')
    assert resp.status_code == 200, resp.content
    body = resp.json()
    assert_envelope(body)
    assert body['data']['id'] == super_user.id
    assert 'username' in body['data']


@pytest.mark.django_db
def test_user_create_envelope(auth_client):
    """create 现返回 201 + {success,data}, data.id 存在且已落库."""
    username = f'env_user_{uuid.uuid4().hex[:8]}'
    payload = {
        'username': username,
        'first_name': 'Env',
        'last_name': 'Create',
        'email': f'{username}@example.com',
        'is_active': True,
    }
    resp = auth_client.post(USERS_BASE + '/', data=payload, format='json')
    assert resp.status_code == 201, resp.content
    body = resp.json()
    assert_envelope(body)
    new_id = body['data']['id']
    assert new_id
    assert User.objects.filter(pk=new_id, username=username).exists()


@pytest.mark.django_db
def test_user_update_envelope(auth_client, super_user):
    """update (PUT) 现返回 {success,data}, 驼峰 firstName 回填."""
    resp = auth_client.put(
        f'{USERS_BASE}/{super_user.id}/',
        data={'first_name': 'EnvUpd'},
        format='json',
    )
    assert resp.status_code == 200, resp.content
    body = resp.json()
    assert_envelope(body)
    assert body['data']['firstName'] == 'EnvUpd'


@pytest.mark.django_db
def test_user_role_list_envelope(auth_client):
    """list 已手动信封 {success,data}."""
    resp = auth_client.get(USER_ROLES_BASE + '/')
    assert resp.status_code == 200, resp.content
    body = resp.json()
    assert_envelope(body)
    assert isinstance(body['data'], list)


@pytest.mark.django_db
def test_user_role_retrieve_envelope(auth_client, super_user):
    """retrieve 现返回 {success,data}, 驼峰 userId 回填."""
    ur = UserRoleV2.objects.create(
        user_id=super_user.id,
        role_code=f'envrole_{uuid.uuid4().hex[:8]}',
        system_code='recruit',
    )
    resp = auth_client.get(f'{USER_ROLES_BASE}/{ur.id}/')
    assert resp.status_code == 200, resp.content
    body = resp.json()
    assert_envelope(body)
    assert body['data']['id'] == ur.id
    assert body['data']['userId'] == super_user.id


@pytest.mark.django_db
def test_user_role_create_envelope(auth_client, super_user):
    """create 现返回 201 + {success,data}, 驼峰 roleCode 回填."""
    role_code = f'envrole_{uuid.uuid4().hex[:8]}'
    payload = {
        'user_id': super_user.id,
        'role_code': role_code,
        'system_code': 'recruit',
    }
    resp = auth_client.post(USER_ROLES_BASE + '/', data=payload, format='json')
    assert resp.status_code == 201, resp.content
    body = resp.json()
    assert_envelope(body)
    new_id = body['data']['id']
    assert new_id
    assert body['data']['roleCode'] == role_code
    assert UserRoleV2.objects.filter(pk=new_id, role_code=role_code).exists()


@pytest.mark.django_db
def test_user_role_update_envelope(auth_client, super_user):
    """update (PATCH) 现返回 {success,data}, 驼峰 managementUnitIds 回填."""
    ur = UserRoleV2.objects.create(
        user_id=super_user.id,
        role_code=f'envrole_{uuid.uuid4().hex[:8]}',
        system_code='recruit',
    )
    resp = auth_client.patch(
        f'{USER_ROLES_BASE}/{ur.id}/',
        data={'management_unit_ids': [7]},
        format='json',
    )
    assert resp.status_code == 200, resp.content
    body = resp.json()
    assert_envelope(body)
    assert body['data']['managementUnitIds'] == [7]


# ===========================================================================
# Batch L: core / v2 权限域信封契约 (permissions/resources, permissions/templates,
#          roles, management-units, user-app-data-scopes)
#
# 锁定目标 (经逐类直读 + 路由 include('apps.core.urls_permission_v2') 确认线上):
# - PermissionResourceViewSet.list      : 原 {success,data} 半信封 -> success_response (补 code)
# - PermissionTemplateViewSet.list      : 同上
# - RoleViewSet(v2).list/retrieve/create/update : 同上四方法
# - ManagementUnitViewSet.list          : 同上 (本地 EnvelopeWriteMixin 不覆盖 list)
# - UserAppDataScopeViewSet.list/create/destroy: 同上 (destroy 经本地混入)
#
# 排除 (保留不收口, SOP 坑①: @action 自定义端点含 success:False 分支 / 非标准 C-U-R):
# - RoleViewSet.clone_from_template / data_permissions / data_permissions_options
# - ManagementUnitViewSet.tree / members / member_detail / resolved_persons
# - UserRoleViewSet.suggest_scope
# ===========================================================================


@pytest.mark.django_db
def test_v2_permission_resource_list_envelope(auth_client):
    """permissions/resources/ list 现返回 {success,data,code}."""
    resp = auth_client.get(PERM_RESOURCES_BASE + '/')
    assert resp.status_code == 200, resp.content
    body = resp.json()
    assert_envelope(body)
    assert isinstance(body['data'], list)


@pytest.mark.django_db
def test_v2_permission_template_list_envelope(auth_client):
    """permissions/templates/ list 现返回 {success,data,code}."""
    resp = auth_client.get(PERM_TEMPLATES_BASE + '/')
    assert resp.status_code == 200, resp.content
    body = resp.json()
    assert_envelope(body)
    assert isinstance(body['data'], list)


@pytest.mark.django_db
def test_v2_role_list_envelope(auth_client):
    """roles/ list 现返回 {success,data,code}."""
    resp = auth_client.get(ROLES_BASE + '/')
    assert resp.status_code == 200, resp.content
    body = resp.json()
    assert_envelope(body)
    assert isinstance(body['data'], list)


@pytest.mark.django_db
def test_v2_role_create_envelope(auth_client):
    """roles/ create 现返回 201 + {success,data,code}, 驼峰 roleCode 回填."""
    role_code = f'envrole_{uuid.uuid4().hex[:8]}'
    payload = {
        'role_code': role_code,
        'role_name': '信封测试角色',
        'system_code': 'recruit',
    }
    resp = auth_client.post(ROLES_BASE + '/', data=payload, format='json')
    assert resp.status_code == 201, resp.content
    body = resp.json()
    assert_envelope(body)
    new_id = body['data']['id']
    assert new_id
    assert body['data']['roleCode'] == role_code
    assert RoleV2.objects.filter(pk=new_id, role_code=role_code).exists()


@pytest.mark.django_db
def test_v2_role_retrieve_envelope(auth_client):
    """roles/{id}/ retrieve 现返回 {success,data,code}."""
    role = RoleV2.objects.create(
        system_code='recruit',
        role_code=f'envrole_{uuid.uuid4().hex[:8]}',
        role_name='信封测试检索角色',
    )
    resp = auth_client.get(f'{ROLES_BASE}/{role.id}/')
    assert resp.status_code == 200, resp.content
    body = resp.json()
    assert_envelope(body)
    assert body['data']['id'] == role.id
    assert body['data']['roleCode'] == role.role_code


@pytest.mark.django_db
def test_v2_management_unit_list_envelope(auth_client):
    """management-units/ list 现返回 {success,data,code}."""
    resp = auth_client.get(MGMT_UNITS_BASE + '/')
    assert resp.status_code == 200, resp.content
    body = resp.json()
    assert_envelope(body)
    assert isinstance(body['data'], list)


@pytest.mark.django_db
def test_v2_user_app_data_scope_list_envelope(auth_client, super_user):
    """user-app-data-scopes/ list 现返回 {success,data,code}."""
    resp = auth_client.get(USER_APP_DATA_SCOPES_BASE + '/')
    assert resp.status_code == 200, resp.content
    body = resp.json()
    assert_envelope(body)
    assert isinstance(body['data'], list)


@pytest.mark.django_db
def test_v2_user_app_data_scope_create_envelope(auth_client, super_user):
    """user-app-data-scopes/ create 现返回 201 + {success,data,code}."""
    role_code = f'envscope_{uuid.uuid4().hex[:8]}'
    payload = {
        'user_id': super_user.id,
        'role_code': role_code,
        'app_code': 'recruit',
        'management_unit_ids': [1, 2],
    }
    resp = auth_client.post(USER_APP_DATA_SCOPES_BASE + '/', data=payload, format='json')
    assert resp.status_code == 201, resp.content
    body = resp.json()
    assert_envelope(body)
    assert body['data']['appCode'] == 'recruit'
    assert body['data']['userId'] == super_user.id
    # destroy 走本地 EnvelopeWriteMixin.destroy -> 同样带 code
    pk = body['data']['id']
    del_resp = auth_client.delete(f'{USER_APP_DATA_SCOPES_BASE}/{pk}/')
    assert del_resp.status_code == 200, del_resp.content
    del_body = del_resp.json()
    assert_envelope(del_body)
    assert del_body['data'] is None
