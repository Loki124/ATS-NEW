"""S8-02 守卫回归测试：删除需求 / 开启抢单 / 批量变更人员 三处专属权限码。

背景：这三处此前无专属守卫 ——
  - 删除需求：destroy 派生 recruit:demand:delete，但 seed 未定义该码 → 回退
    recruit:demand:list（持列表码即可删，越权面）；
  - 开启抢单：DemandConfig 整页前端漏挂 v-permission，且后端统一派生 :edit，任意能进页者皆可拨动；
  - 批量变更人员：复用通用动态字段值端点（守卫码 dynamic_fields:edit 与需求编辑错配，标准角色两码皆无）。

本测试钉住：每个操作只被其专属码放行，列表码 / 编辑码不再越权；批量端点仅接受人员字段。
"""
from __future__ import annotations

from django.db import connection
from rest_framework.test import APIClient

from tests.fixtures_common import _attach_role, _create_role_v2

CONFIG_URL = '/api/v1/system/config/demand'
BATCH_URL = '/api/v1/demands/batch-update-people/'


def _make_user_with_codes(username, employee_id, department, codes):
    """创建一个用户 + 自定义角色，仅授予给定 resource_code 集合（空集合=无任何权限）。"""
    from django.contrib.auth import get_user_model

    user = get_user_model().objects.create_user(
        username=username, password='Test@1234', employee_id=employee_id, department=department,
    )
    role = _create_role_v2(f'ROLE_{username.upper()}', username)
    _attach_role(user, role)
    if codes:
        from django.utils import timezone

        now = timezone.now()
        with connection.cursor() as c:
            for rc in codes:
                c.execute(
                    "INSERT INTO role_permission (role_code, resource_code, system_code, created_at) "
                    "VALUES (%s, %s, 'recruit', %s)",
                    [role.role_code, rc, now],
                )
    return user


# ---- 开启抢单：DemandConfigView ----
def test_demand_config_get_requires_list_code(department):
    # 仅持 list 的用户可读
    user = _make_user_with_codes('cfg_list', 'EC1', department, ['recruit:settings:demand_config:list'])
    client = APIClient()
    client.force_authenticate(user=user)
    assert client.get(CONFIG_URL).status_code == 200
    # 无角色用户读被拒
    anon = APIClient()
    anon.force_authenticate(user=_make_user_with_codes('cfg_none', 'EC2', department, []))
    assert anon.get(CONFIG_URL).status_code == 403


def test_demand_config_post_requires_edit_or_open_grab(department):
    # 无角色 → 403
    no_role = APIClient()
    no_role.force_authenticate(user=_make_user_with_codes('cfg_nr', 'EC3', department, []))
    assert no_role.post(CONFIG_URL, {'demandMode': 'task'}, format='json').status_code == 403
    # 仅 list → 403（不能写）
    list_only = APIClient()
    list_only.force_authenticate(
        user=_make_user_with_codes('cfg_lo', 'EC4', department, ['recruit:settings:demand_config:list']),
    )
    assert list_only.post(CONFIG_URL, {'demandMode': 'task'}, format='json').status_code == 403
    # 仅 open_grab → 200（S8-02 拆码后独立放行，证明与 edit 隔离）
    grab_only = APIClient()
    grab_only.force_authenticate(
        user=_make_user_with_codes('cfg_go', 'EC5', department, ['recruit:settings:demand_config:open_grab']),
    )
    assert grab_only.post(CONFIG_URL, {'demandMode': 'task'}, format='json').status_code == 200
    # 仅 edit → 200
    edit_only = APIClient()
    edit_only.force_authenticate(
        user=_make_user_with_codes('cfg_eo', 'EC6', department, ['recruit:settings:demand_config:edit']),
    )
    assert edit_only.post(CONFIG_URL, {'demandMode': 'task'}, format='json').status_code == 200


# ---- 删除需求：DemandViewSet.destroy ----
def test_demand_destroy_requires_delete_not_list(department):
    # 仅 list 的用户：删除被拒（钉住「回退 list 即可删」的 bug 已修），但列表可读
    user = _make_user_with_codes('del_list', 'ED1', department, ['recruit:demand:list'])
    client = APIClient()
    client.force_authenticate(user=user)
    # 不存在的 pk：权限先校验 → 403（无 delete 码）；权限通过才会 404
    assert client.delete('/api/v1/demands/999999/').status_code == 403
    assert client.get('/api/v1/demands/').status_code == 200


# ---- 批量变更人员：DemandBatchUpdatePeopleView ----
def test_demand_batch_update_requires_batch_update_code(department):
    body = {'ids': ['d-x'], 'values': {'hrbp': 'u-hrbp'}}
    # 无角色 → 403
    no_role = APIClient()
    no_role.force_authenticate(user=_make_user_with_codes('b_nr', 'EB1', department, []))
    assert no_role.post(BATCH_URL, body, format='json').status_code == 403
    # 仅 list → 403（不能批量改人）
    list_only = APIClient()
    list_only.force_authenticate(
        user=_make_user_with_codes('b_lo', 'EB2', department, ['recruit:demand:list']),
    )
    assert list_only.post(BATCH_URL, body, format='json').status_code == 403
    # 持 batch_update → 200（权限通过；测试库无人员字段定义，落库 0 条但守卫已放行）
    bu_user = _make_user_with_codes('b_bu', 'EB3', department, ['recruit:demand:batch_update'])
    bu_client = APIClient()
    bu_client.force_authenticate(user=bu_user)
    assert bu_client.post(BATCH_URL, body, format='json').status_code == 200


def test_demand_batch_update_rejects_non_people_fields(department):
    # 仅传非人员字段 → 被 ALLOWED_FIELDS 过滤后为空 → 400（防止借批量端点改任意字段）
    user = _make_user_with_codes('b_allow', 'EB4', department, ['recruit:demand:batch_update'])
    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.post(BATCH_URL, {'ids': ['d-x'], 'values': {'title': 'x'}}, format='json')
    assert resp.status_code == 400
