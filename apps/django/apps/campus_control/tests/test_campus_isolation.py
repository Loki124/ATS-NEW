"""S5-24（需求 1-2）四角色数据隔离矩阵 —— 真实 HTTP 穿透测试。

验证 Person / RotationArrangement 列表端点在行级隔离收口后, 不同角色看到的数据范围:

  1. 超管 (SUPER_ADMIN): 全量可见 (is_super_admin bypass)。
  2. HRBP / 班主任 经默认部门范围 (DEPT scope): 只看本部门班主任带出的校招生。
  3. 班主任 经 CUSTOM 规则「head_teacher 包含 当前登录用户」: 只看自己带的校招生
     (跨部门也要能看, 证伪"只看本部门")。
  4. 带教导师 经 CUSTOM 规则「mentor 包含 当前登录用户」: 只看自己带的轮岗安排。

🔴 验证须穿透真实链路: 用 DRF APITestCase + JWT 真实鉴权, 走 ViewSet.get_queryset
  → ScopeQuerysetMixin.scope_queryset → scope_filter_q → role_entity_scope_q →
  expr_compiler 全链路, 不手搓 dict 绕过 CamelCaseJSONParser / scope 解析。

本测试自带幂等角色/用户/客户端构造 (INSERT IGNORE + JWT), 不依赖共享 fixture 的
非幂等 _create_role_v2, 避免测试库残留角色导致的重复插入。
"""
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.campus_control.models import Person
from apps.campus_rotation.models import RotationArrangement
from apps.core.models import Department
from apps.core.models_permission_v2 import RoleV2
from apps.data_permission.models import DataPermissionRule

pytestmark = pytest.mark.django_db

BASE = '/api/v1/campus'
ROT_BASE = '/api/v1/campus-rotation'

USER = get_user_model()


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _insert_role_ignore(code: str) -> RoleV2:
    """幂等创建 V2 角色 (INSERT IGNORE), 避免测试库残留导致的重复插入。"""
    from django.utils import timezone
    now = timezone.now()
    with connection.cursor() as c:
        c.execute(
            """INSERT IGNORE INTO roles
               (system_code, role_code, role_name, description, is_system,
                status, default_data_scope_type, created_at, updated_at)
               VALUES ('recruit', %s, %s, '', 0, 1, 'ALL', %s, %s)""",
            [code, code, now, now],
        )
    return RoleV2.objects.get(role_code=code, system_code='recruit')


def _attach_role(user, role) -> None:
    with connection.cursor() as c:
        c.execute(
            """INSERT IGNORE INTO user_roles
               (user_id, role_code, system_code, granted_by_id, granted_at, updated_at)
               VALUES (%s, %s, 'recruit', %s, %s, %s)""",
            [user.pk, role.role_code, user.pk, timezone_now(), timezone_now()],
        )


def timezone_now():
    from django.utils import timezone
    return timezone.now()


def _make_user(username, department, employee_id):
    return USER.objects.create_user(
        username=username, password='Test@1234', employee_id=employee_id,
        department=department,
    )


def _client_for(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client


def _make_dept(did, name):
    return Department.objects.get_or_create(
        id=did, defaults={'name': name, 'code': did, 'path': f'/{name}'},
    )[0]


def _make_person(head_teacher, created_by, code):
    return Person.objects.create(
        code=code, name=code, bu='能电BG', school='985', sex='男', major='工学',
        month='1月', status='在职', head_teacher=head_teacher,
        created_by=created_by, updated_by=created_by,
    )


def _list_ids(client, url):
    resp = client.get(url, {'page_size': 200})
    assert resp.status_code == 200, resp.content.decode()
    body = resp.json()
    return {row['id'] for row in body['data']}, body['pagination']['total']


def _grant_permission(role_code, *resources):
    """自包含授予角色资源码权限 (INSERT IGNORE), 不依赖 session 级 role_permission 种子。

    测试库 role_permission 在 --reuse-db 下不会被 session fixture 持久化 (事务回滚),
    故每个用例自行授予所需码, 确保 HRBP 能真实通过 V2Permission 守卫。
    """
    from django.utils import timezone
    now = timezone.now()
    with connection.cursor() as c:
        for rc in resources:
            c.execute(
                """INSERT IGNORE INTO role_permission
                   (role_code, resource_code, system_code, created_at)
                   VALUES (%s, %s, 'recruit', %s)""",
                [role_code, rc, now],
            )


def _custom_rule(role_code, entity, dimension):
    return DataPermissionRule.objects.create(
        dimension_type='ROLE', dimension_value=role_code, level='ROW',
        scope_type='CUSTOM', entity=entity, status=1,
        scope_payload={
            'expr': '1',
            'groups': [{'expr': '1', 'conditions': [
                {'dimension': dimension, 'operator': 'in',
                 'valueSource': 'dynamic', 'dynamicKey': 'currentUser.id'},
            ]}],
        },
        created_by=1,
    )


# ---------------------------------------------------------------------------
# 1. 超管基线: 全量可见
# ---------------------------------------------------------------------------
def test_super_admin_sees_all_persons():
    admin_role = _insert_role_ignore('SUPER_ADMIN')
    dept = _make_dept('dept-iso-admin', '隔离管理部')
    admin = _make_user(f'admin_{_uid()}', dept, 'E_ADMIN')
    _attach_role(admin, admin_role)
    client = _client_for(admin)

    dept_other = _make_dept('dept-iso-other', '隔离他部')
    ht_same = _make_user(f'ht_same_{_uid()}', dept, 'E_SAME')
    ht_other = _make_user(f'ht_other_{_uid()}', dept_other, 'E_OTHER')
    p_same = _make_person(ht_same, admin, f'PSAME_{_uid()}')
    p_other = _make_person(ht_other, admin, f'POTHER_{_uid()}')

    ids, total = _list_ids(client, f'{BASE}/persons/')
    assert p_same.id in ids and p_other.id in ids
    assert total >= 2


# ---------------------------------------------------------------------------
# 2. HRBP / 班主任 默认部门范围: 只看本部门班主任带出的校招生
# ---------------------------------------------------------------------------
def test_hrbp_dept_scope_sees_only_same_dept_persons():
    hrbp_role = _insert_role_ignore('HRBP')
    # 默认数据范围改为 DEPT (部门范围)
    RoleV2.objects.filter(role_code='HRBP', system_code='recruit').update(
        default_data_scope_type='DEPT')
    _grant_permission('HRBP', 'recruit:campus:person:list')

    dept = _make_dept('dept-iso-main', '隔离主部')
    hrbp = _make_user(f'hrbp_{_uid()}', dept, 'E_HRBP')
    _attach_role(hrbp, hrbp_role)
    client = _client_for(hrbp)

    dept_other = _make_dept('dept-iso-main2', '隔离主部2')
    ht_same = _make_user(f'ht_same_{_uid()}', dept, 'E_SAME')      # 与 hrbp 同部门
    ht_other = _make_user(f'ht_other_{_uid()}', dept_other, 'E_OTHER')
    p_same = _make_person(ht_same, hrbp, f'PSAME_{_uid()}')
    p_other = _make_person(ht_other, hrbp, f'POTHER_{_uid()}')

    ids, total = _list_ids(client, f'{BASE}/persons/')
    assert p_same.id in ids
    assert p_other.id not in ids
    assert total == 1


# ---------------------------------------------------------------------------
# 3. 班主任 CUSTOM 规则「head_teacher 包含 当前登录用户」: 只看自己带的 (跨部门也要能看)
# ---------------------------------------------------------------------------
def test_head_teacher_custom_rule_sees_only_self_mentored():
    hrbp_role = _insert_role_ignore('HRBP')
    # 默认范围收紧为 SELF (只看 created_by=自己); 实际放行靠 CUSTOM 规则
    RoleV2.objects.filter(role_code='HRBP', system_code='recruit').update(
        default_data_scope_type='SELF')
    _grant_permission('HRBP', 'recruit:campus:person:list')

    dept = _make_dept('dept-iso-mt', '隔离带教部')
    hrbp = _make_user(f'hrbp_{_uid()}', dept, 'E_HRBP')
    _attach_role(hrbp, hrbp_role)
    client = _client_for(hrbp)

    dept_other = _make_dept('dept-iso-mt2', '隔离带教部2')
    ht_other = _make_user(f'ht_other_{_uid()}', dept_other, 'E_OTHER')
    p_mine = _make_person(hrbp, hrbp, f'PMINE_{_uid()}')       # head_teacher = hrbp
    p_cross = _make_person(hrbp, ht_other, f'PCROSS_{_uid()}')  # 跨部门, 仍由其带
    p_other = _make_person(ht_other, ht_other, f'POTHER_{_uid()}')  # 别人带的

    _custom_rule('HRBP', 'campus_person', 'head_teacher')

    ids, total = _list_ids(client, f'{BASE}/persons/')
    assert p_mine.id in ids
    assert p_cross.id in ids          # 跨部门也可见 (规则按人, 非按部门)
    assert p_other.id not in ids
    assert total == 2


# ---------------------------------------------------------------------------
# 4. 带教导师 CUSTOM 规则「mentor 包含 当前登录用户」: 只看自己带的轮岗安排
# ---------------------------------------------------------------------------
def test_mentor_custom_rule_sees_only_self_arrangements():
    hrbp_role = _insert_role_ignore('HRBP')
    RoleV2.objects.filter(role_code='HRBP', system_code='recruit').update(
        default_data_scope_type='SELF')
    _grant_permission('HRBP', 'recruit:campus:rotation:list')

    dept = _make_dept('dept-iso-mentor', '隔离导师部')
    hrbp = _make_user(f'hrbp_{_uid()}', dept, 'E_HRBP')
    _attach_role(hrbp, hrbp_role)
    client = _client_for(hrbp)

    other_mentor = _make_user(f'om_{_uid()}', dept, 'E_OM')
    arr_mine = RotationArrangement.objects.create(
        person_id=900001, mentor=hrbp, head_teacher=hrbp,
        current_dept=dept, created_by=hrbp, updated_by=hrbp,
    )
    arr_other = RotationArrangement.objects.create(
        person_id=900002, mentor=other_mentor, head_teacher=other_mentor,
        current_dept=dept, created_by=other_mentor, updated_by=other_mentor,
    )

    _custom_rule('HRBP', 'campus_arrangement', 'mentor')

    ids, total = _list_ids(client, f'{ROT_BASE}/rotation-arrangements/')
    assert arr_mine.id in ids
    assert arr_other.id not in ids
    assert total == 1
