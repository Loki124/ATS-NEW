"""用户管理 · 管理单元授权配置（2026-10-21）

覆盖用户管理页新增的「管理单元授权」能力：

- 落库字段 ``UserRoleV2.management_unit_ids`` —— 执行面 ``scope_resolver.resolve_scope``
  L1 的唯一真相源（多身份取并集）。本特性按**用户级统一**口径：同一份范围写到
  该用户的全部身份行。
- 端点 ``POST /api/v1/permissions/users/{id}/roles/`` 同时保存「身份 + 授权范围」。

重点锁住三条曾经会静默丢数据的路径：

1. 重存身份（不带 managementUnitIds）不再抹掉已有的管理单元授权 —— 旧实现是
   「删光 UserRoleV2 再重建」，授权范围随行一起消失，前端毫无提示。
2. 未知管理单元 id 响亮 400，而不是静默丢弃（否则「配了却没生效」无从察觉）。
3. 用户列表「管理单元范围」列由批量派生，不引入 N+1。
"""
import uuid

import pytest

from apps.core.models_permission_v2 import ManagementUnit, RoleV2, UserRoleV2

pytestmark = pytest.mark.django_db


ROLE_URL = '/api/v1/permissions/users/{uid}/roles/'


def _new_user():
    """建一个**用户名唯一**的用户.

    刻意不用 UserFactory: 它的 username 是进程内 Sequence + django_get_or_create,
    跨测试文件会撞名并返回别人的用户 —— 本文件断言的是「某个用户的授权范围」,
    撞名就会把别的测试留下的 UserRoleV2 行算进来, 造成随机失败。
    """
    from django.contrib.auth import get_user_model
    return get_user_model().objects.create_user(
        username=f'mgmt_unit_user_{uuid.uuid4().hex[:12]}',
        email=f'mgmt_unit_{uuid.uuid4().hex[:12]}@example.com',
        password='Test@1234',
    )


@pytest.fixture
def units():
    """两个启用的管理单元 + 一个停用的。"""
    a = ManagementUnit.objects.create(
        system_code='recruit', unit_name='华东大区', unit_type='org',
        org_scope=[{'deptId': 'D1', 'includeChildren': True}], include_children=1, status=1,
    )
    b = ManagementUnit.objects.create(
        system_code='recruit', unit_name='华南大区', unit_type='org',
        org_scope=[{'deptId': 'D2', 'includeChildren': False}], include_children=1, status=1,
    )
    off = ManagementUnit.objects.create(
        system_code='recruit', unit_name='已停用单元', unit_type='org',
        org_scope=[], include_children=1, status=0,
    )
    return a, b, off


@pytest.fixture
def role():
    r, _ = RoleV2.objects.get_or_create(
        system_code='recruit', role_code='recruit:mgmt_test',
        defaults={'role_name': '管理单元授权测试身份'},
    )
    return r


def _post(client, uid, payload):
    return client.post(ROLE_URL.format(uid=uid), data=payload, format='json')


def test_post_saves_management_unit_scope(auth_client, units, role):
    """带 managementUnitIds 保存身份 → 落库到 UserRoleV2.management_unit_ids"""
    uid = _new_user().id
    a, b, _ = units

    resp = _post(auth_client, uid, {
        'roleIds': [role.id],
        'managementUnitIds': [a.id, b.id],
    })

    assert resp.status_code == 200, resp.content
    ur = UserRoleV2.objects.get(user_id=uid, role_code=role.role_code)
    assert ur.management_unit_ids == [a.id, b.id]


def test_scope_applies_to_every_identity(auth_client, units):
    """用户级统一口径：多个身份共用同一份范围（解析时取并集 → 等于该配置）"""
    uid = _new_user().id
    a, _, _ = units
    r1, _ = RoleV2.objects.get_or_create(
        system_code='recruit', role_code='recruit:mgmt_a',
        defaults={'role_name': '身份甲'},
    )
    r2, _ = RoleV2.objects.get_or_create(
        system_code='recruit', role_code='recruit:mgmt_b',
        defaults={'role_name': '身份乙'},
    )

    resp = _post(auth_client, uid, {
        'roleIds': [r1.id, r2.id],
        'managementUnitIds': [a.id],
    })

    assert resp.status_code == 200, resp.content
    scopes = list(
        UserRoleV2.objects.filter(user_id=uid).values_list('management_unit_ids', flat=True)
    )
    assert scopes == [[a.id], [a.id]]


def test_resaving_roles_preserves_existing_scope(auth_client, units, role):
    """回归：重存身份（不带 managementUnitIds）不得抹掉已有授权范围。

    旧实现「删光 UserRoleV2 再重建」会把 management_unit_ids 一并清掉 ——
    管理员在用户管理页改一次身份，授权范围就静默消失。
    """
    uid = _new_user().id
    a, _, _ = units
    _post(auth_client, uid, {'roleIds': [role.id], 'managementUnitIds': [a.id]})

    # 只带 roleIds 重存（老调用方口径）
    resp = _post(auth_client, uid, {'roleIds': [role.id]})

    assert resp.status_code == 200, resp.content
    ur = UserRoleV2.objects.get(user_id=uid, role_code=role.role_code)
    assert ur.management_unit_ids == [a.id], '重存身份不得抹掉管理单元授权范围'


def test_empty_scope_clears_authorization(auth_client, units, role):
    """显式传空数组 = 清空授权范围（与「缺省=保留」区分开）"""
    uid = _new_user().id
    a, _, _ = units
    _post(auth_client, uid, {'roleIds': [role.id], 'managementUnitIds': [a.id]})

    resp = _post(auth_client, uid, {'roleIds': [role.id], 'managementUnitIds': []})

    assert resp.status_code == 200, resp.content
    ur = UserRoleV2.objects.get(user_id=uid, role_code=role.role_code)
    assert not ur.management_unit_ids, '传空数组应清空管理单元授权范围'


def test_unknown_management_unit_rejected(auth_client, units, role):
    """未知管理单元 id → 响亮 400，不静默丢弃（否则「配了却没生效」无从察觉）"""
    uid = _new_user().id
    a, _, _ = units

    resp = _post(auth_client, uid, {
        'roleIds': [role.id],
        'managementUnitIds': [a.id, 999999],
    })

    assert resp.status_code == 400, resp.content
    assert '管理单元不存在' in resp.json().get('message', '')
    assert not UserRoleV2.objects.filter(user_id=uid).exists(), '校验失败不得留下半截写入'


def test_get_returns_effective_scope(auth_client, units, role):
    """GET 回显管理单元授权范围（多条身份取并集 = 实际生效范围）"""
    uid = _new_user().id
    a, b, _ = units
    _post(auth_client, uid, {'roleIds': [role.id], 'managementUnitIds': [a.id, b.id]})

    resp = auth_client.get(ROLE_URL.format(uid=uid))

    assert resp.status_code == 200, resp.content
    items = resp.json()['data']
    assert items, '应返回该用户的身份'
    mine = [i for i in items if i.get('code') == role.role_code]
    assert mine, '应包含本次授权的身份'
    for item in mine:
        assert sorted(item['managementUnitIds']) == sorted([a.id, b.id])


def test_user_list_exposes_management_unit_names(auth_client, units, role):
    """用户列表「管理单元范围」列：批量派生管理单元名称"""
    uid = _new_user().id
    a, b, _ = units
    _post(auth_client, uid, {'roleIds': [role.id], 'managementUnitIds': [a.id, b.id]})

    resp = auth_client.get('/api/v1/users/?page_size=200')

    assert resp.status_code == 200, resp.content
    rows = resp.json()['data']
    target = next(r for r in rows if str(r['id']) == str(uid))
    assert sorted(target['managementUnitNames']) == sorted(['华东大区', '华南大区'])


def test_user_list_without_scope_returns_empty_names(auth_client, role):
    """未授权管理单元的用户 → 空数组（前端直接 .filter(Boolean) 渲染，无需判空）"""
    uid = _new_user().id
    _post(auth_client, uid, {'roleIds': [role.id]})

    resp = auth_client.get('/api/v1/users/?page_size=200')

    assert resp.status_code == 200, resp.content
    rows = resp.json()['data']
    target = next(r for r in rows if str(r['id']) == str(uid))
    assert target['managementUnitNames'] == []
