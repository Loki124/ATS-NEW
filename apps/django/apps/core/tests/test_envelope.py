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
import uuid

import pytest
from django.contrib.auth import get_user_model

from apps.core.models_permission_v2 import UserRoleV2

User = get_user_model()

USERS_BASE = '/api/v1/users'
USER_ROLES_BASE = '/api/v1/user-roles'


def _assert_envelope(body, *, code=0):
    """统一信封契约: success=True / 含 data / code==0."""
    assert isinstance(body, dict), f'响应非 dict: {body!r}'
    assert body.get('success') is True, f"success 非 True: {body!r}"
    assert 'data' in body, f'缺 data 键: {body!r}'
    assert body.get('code') == code, f"code 非 {code}: {body!r}"


@pytest.mark.django_db
def test_user_list_envelope(auth_client):
    """list 经 StandardResultsSetPagination 包 {success,data,pagination}."""
    resp = auth_client.get(USERS_BASE + '/')
    assert resp.status_code == 200, resp.content
    body = resp.json()
    _assert_envelope(body)
    assert isinstance(body['data'], list)
    assert 'pagination' in body


@pytest.mark.django_db
def test_user_retrieve_envelope(auth_client, super_user):
    """retrieve 现返回 {success,data}, data.id == 用户 id."""
    resp = auth_client.get(f'{USERS_BASE}/{super_user.id}/')
    assert resp.status_code == 200, resp.content
    body = resp.json()
    _assert_envelope(body)
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
    _assert_envelope(body)
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
    _assert_envelope(body)
    assert body['data']['firstName'] == 'EnvUpd'


@pytest.mark.django_db
def test_user_role_list_envelope(auth_client):
    """list 已手动信封 {success,data}."""
    resp = auth_client.get(USER_ROLES_BASE + '/')
    assert resp.status_code == 200, resp.content
    body = resp.json()
    _assert_envelope(body)
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
    _assert_envelope(body)
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
    _assert_envelope(body)
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
    _assert_envelope(body)
    assert body['data']['managementUnitIds'] == [7]
