"""批次1 两提交（0a54353d 卡1.1 / 87398dbf 卡1.2+1.3）独立验证 —— 生产链路判别用例。

本文件由 QA（严过关）独立编写，目的是**不重复**实现者已覆盖的 21 例（
test_scope_v2_union.py 6 例 + test_role_scope_unset.py 15 例），而是补上
实现者测试没穿过的**生产链路**：

1. 卡 1.1「管理单元并集」的 none+unit 交互（实现者 6 例只覆盖 CUSTOM+unit /
   单方 / ALL 短路，从未把 mode='none' 角色规则与管理单元放一起）。
2. 卡 1.2/1.3 一律走**真实 HTTP 端点** /api/v1/roles/{id}/data-permissions/
   （GET/POST），而实现者 15 例全部直接调 build_modules_response / upsert_modules /
   validate_modules —— 绕过了 CamelCaseJSONParser + normalize_modules_payload 还原
   与 V2Permission + 审计落库整条链路。注意 valueSource 字段穿越解析器的回归已由
   b7430214 的 test_dynamic_cond_http_parser.py 覆盖；本文件补的是 unset / featureGranted
   在真实端点下的行为。

反假绿纪律（DR-01）：每条断言都先验「落库/响应」真实态，再下结论。
"""
import json

import pytest
from django.test import Client

from django.contrib.auth import get_user_model

from apps.core.models import Department
from apps.core.models_permission_v2 import (
    ManagementUnit,
    PermissionResource,
    RolePermissionV2,
    RoleV2,
)
from apps.core.scope_resolver import resolve_scope, scope_filter_q
from apps.data_permission.models import DataPermissionRule

# candidate 读范围 CUSTOM「dept」维度编译为 referrer__department_id
CUSTOM_SCOPE_FIELD = 'referrer__department'
CUSTOM_CREATOR_FIELD = 'created_by'

MODULE_KEYS = ['demand', 'process', 'position', 'candidate', 'talent']


# ---------------------------------------------------------------------------
# 共享 fixture：超管 + JWT client（穿真实 HTTP 链路，V2Permission 对超管放行）
# ---------------------------------------------------------------------------


@pytest.fixture
def admin_client(db):
    user = get_user_model().objects.create(
        username='qa_batch1_admin', is_superuser=True, is_active=True,
    )
    from rest_framework_simplejwt.tokens import RefreshToken

    c = Client()
    c._qa_token = 'Bearer ' + str(RefreshToken.for_user(user).access_token)
    return c


@pytest.fixture
def role(db):
    return RoleV2.objects.create(
        system_code='recruit', role_code='QA_BATCH1_DP_ROLE',
        role_name='批次1 独立验证角色', status=1,
    )


def _dp_url(role):
    return f'/api/v1/roles/{role.pk}/data-permissions/'


def _http_post(client, role, modules):
    resp = client.post(
        _dp_url(role),
        data=json.dumps({'modules': modules}),
        content_type='application/json',
        HTTP_AUTHORIZATION=client._qa_token,
    )
    try:
        body = resp.json()
    except Exception:  # pragma: no cover - 非 JSON 响应兜底
        body = {'_raw': resp.content[:300].decode('utf-8', 'replace')}
    return resp.status_code, body


def _http_get(client, role):
    resp = client.get(_dp_url(role), HTTP_AUTHORIZATION=client._qa_token)
    return resp.status_code, resp.json()


def _module_of(body, mk):
    return next(m for m in body['data']['modules'] if m['moduleKey'] == mk)


# ===========================================================================
# 卡 1.1：none 角色规则 + 管理单元 -> 并集把 none 吸收为 no-op（放宽口径）
# ===========================================================================


def _mk_departments():
    for did in ('D1', 'D2', 'D3'):
        Department.objects.create(id=did, name=did, code=f'u-{did}', path=did, parent=None)


def _mk_user(username, dept_id='D1'):
    return get_user_model().objects.create_user(
        username=username, password='x', department_id=dept_id,
    )


def _grant_unit(user, role_code, unit):
    from apps.core.models_permission_v2 import UserRoleV2

    UserRoleV2.objects.create(
        user_id=user.pk, role_code=role_code, system_code='recruit',
        app_data_scopes={'recruit': [unit.id]}, granted_by_id=1,
    )


def _mk_unit(name, org_scope):
    return ManagementUnit.objects.create(
        unit_name=name, system_code='recruit', unit_type='org',
        org_scope=org_scope, status=1,
    )


def _mk_candidate(name, referrer):
    from apps.candidate.models import Candidate

    return Candidate.objects.create(name=name, referrer=referrer, created_by=referrer)


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_union_none_rule_absorbed_by_management_unit():
    """卡 1.1 边界：角色自定义范围 = mode='none' + 用户另有管理单元 -> 并集后 none 被吸收。

    实现者 6 例覆盖 CUSTOM+unit / 单方 / ALL 短路，但从未把 none 规则与单元组合。
    enforcement.py:183 明确「NONE -> Q(pk__in=[])（OR 并集中 no-op）」，本例把这条
    注释钉成可执行的回归：

      - 旧「替换」语义：none 替换管理单元 -> 该模块对谁都不可见（连单元数据也看不到）。
      - 新「并集」语义：none 在 OR 中是空集 no-op -> 单元数据仍可见（none 被吸收）。

    断言：仅管理单元(D2)内的候选人可见；角色 none 规则不再把单元数据一并抹掉，
    也不放宽到 none 规则本不该允许的 D1/D3。
    """
    from apps.candidate.models import Candidate

    _mk_departments()
    u = _mk_user('none_unit_u', dept_id='D1')
    ref_d1 = _mk_user('ref_d1', dept_id='D1')
    ref_d2 = _mk_user('ref_d2', dept_id='D2')  # 管理单元域
    ref_d3 = _mk_user('ref_d3', dept_id='D3')

    unit = _mk_unit('none单元测试单元', ['D2'])
    _grant_unit(u, 'R_NONE_UNIT', unit)

    # 角色自定义范围 = 显式「无权限」(scope_type=NONE)
    DataPermissionRule.objects.create(
        dimension_type='ROLE', dimension_value='R_NONE_UNIT', level='ROW',
        entity='candidate', scope_type='NONE', status=1,
    )

    c_d1 = _mk_candidate('自己部门', ref_d1)
    c_d2 = _mk_candidate('管理单元内', ref_d2)
    c_d3 = _mk_candidate('都不属于', ref_d3)

    # 前置：用户确实挂在管理单元上
    assert resolve_scope(u, app_code='recruit').get('management_unit_ids'), \
        '前置条件: 用户必须确实挂在管理单元上'

    q = scope_filter_q(
        u, app_code='recruit', scope_field=CUSTOM_SCOPE_FIELD,
        creator_field=CUSTOM_CREATOR_FIELD, entity='candidate',
    )
    names = set(Candidate.objects.filter(q).values_list('name', flat=True))

    # 并集 = 单元(D2) 数据；none 规则被吸收，不再抹掉单元数据
    assert names == {c_d2.name}, f'none 应被单元吸收, 实际可见={names}'
    # none 不越权放宽到 D1/D3
    assert c_d1.name not in names and c_d3.name not in names

    # 对称对照：去掉管理单元后，同一条 none 规则必须让该模块对谁都不可见
    DataPermissionRule.objects.filter(
        dimension_type='ROLE', dimension_value='R_NONE_UNIT', entity='candidate',
    ).delete()
    from apps.core.models_permission_v2 import UserRoleV2

    UserRoleV2.objects.filter(user_id=u.pk, role_code='R_NONE_UNIT').delete()
    # 重建纯 none 角色（无单元）
    u2 = _mk_user('none_only_u2', dept_id='D1')
    UserRoleV2.objects.create(
        user_id=u2.pk, role_code='R_NONE_ONLY', system_code='recruit', granted_by_id=1,
    )
    DataPermissionRule.objects.create(
        dimension_type='ROLE', dimension_value='R_NONE_ONLY', level='ROW',
        entity='candidate', scope_type='NONE', status=1,
    )
    q2 = scope_filter_q(
        u2, app_code='recruit', scope_field=CUSTOM_SCOPE_FIELD,
        creator_field=CUSTOM_CREATOR_FIELD, entity='candidate',
    )
    assert not Candidate.objects.filter(q2).exists(), \
        'none-only（无单元）必须对该模块不可见 —— 证明吸收只在并集侧发生'


# ===========================================================================
# 卡 1.2：unset 真实 HTTP 链路（实现者 15 例全函数级，未穿端点）
# ===========================================================================


def test_http_unset_deletes_read_row(admin_client, role):
    """POST unset -> GET 回显 mode='unset' 且库里真的没有读行（删行，非落 NONE）。

    实现者 test_unset_deletes_existing_custom_read_row 调 upsert_modules 直接验；
    本例验同一行为经真实端点（CamelCaseJSONParser + normalize + V2Permission + 审计）。
    """
    # 先造一条 CUSTOM 读行
    DataPermissionRule.objects.create(
        dimension_type='ROLE', dimension_value=role.role_code, level='ROW',
        entity='candidate', scope_type='CUSTOM', status=1,
        scope_payload={'expr': '1', 'groups': [{
            'expr': '1',
            'conditions': [{'dimension': 'dept', 'operator': 'in',
                            'values': [{'id': 'D1'}]}],
        }]},
    )
    status, body = _http_post(
        admin_client, role, [{'moduleKey': mk, 'mode': 'unset'} for mk in MODULE_KEYS],
    )
    assert status == 200, f'HTTP {status}: {body}'
    assert body.get('success') is True, body

    # 库里不再有该实体读行
    assert not DataPermissionRule.objects.filter(
        dimension_type='ROLE', dimension_value=role.role_code,
        level='ROW', entity='candidate',
    ).exists(), 'unset 经真实端点后库里不应残留 candidate 读行'

    # GET 回显 unset
    gstatus, gbody = _http_get(admin_client, role)
    assert gstatus == 200, gbody
    assert _module_of(gbody, 'candidate')['mode'] == 'unset'


def test_http_unset_with_existing_write_row_rejected_400(admin_client, role):
    """存在存量 WRITE 行时 POST unset -> 真实端点必须 400（fail-closed）。

    实现者 test_unset_rejected_when_write_row_exists 直接调 upsert_modules 验；
    本例验经真实端点（含 @transaction.atomic 回滚）后写行原样还在 + 响应 400 + 文案。
    """
    DataPermissionRule.objects.create(
        dimension_type='ROLE', dimension_value=role.role_code, level='ROW',
        entity='position', scope_type='ALL', row_access='WRITE',
        actions=['edit'], status=1,
    )
    status, body = _http_post(
        admin_client, role, [{'moduleKey': 'position', 'mode': 'unset'}],
    )
    assert status == 400, f'应 400 拒绝, 实际 HTTP {status}: {body}'
    assert body.get('success') is False
    msg = body.get('message') or ''
    assert 'position' in msg and '写范围' in msg, f'文案须含模块名+操作指引: {msg}'

    # 事务回滚：存量 WRITE 行必须原样在
    assert DataPermissionRule.objects.filter(
        dimension_type='ROLE', dimension_value=role.role_code,
        level='ROW', entity='position', row_access='WRITE',
    ).exists(), '拒绝保存后存量 WRITE 行不得被删除'


def test_http_clear_write_then_unset_allowed_200(admin_client, role):
    """同一次保存先 write.mode=none 再置 unset -> 真实端点 200 且最终 unset。

    实现者 test_unset_allowed_when_same_payload_clears_write 函数级验；本例验真实端点。
    """
    DataPermissionRule.objects.create(
        dimension_type='ROLE', dimension_value=role.role_code, level='ROW',
        entity='talent', scope_type='ALL', row_access='WRITE',
        actions=['edit'], status=1,
    )
    modules = [{
        'moduleKey': 'talent', 'mode': 'unset',
        'write': {'mode': 'none', 'expr': '', 'groups': [], 'actions': []},
    }]
    status, body = _http_post(admin_client, role, modules)
    assert status == 200, f'HTTP {status}: {body}'
    assert body.get('success') is True, body

    # 最终该模块无任何行
    assert not DataPermissionRule.objects.filter(
        dimension_type='ROLE', dimension_value=role.role_code, entity='talent',
    ).exists()
    gstatus, gbody = _http_get(admin_client, role)
    assert _module_of(gbody, 'talent')['mode'] == 'unset'


# ===========================================================================
# 卡 1.3：featureGranted 真实 HTTP 链路（实现者 15 例全函数级，未穿端点）
# ===========================================================================


@pytest.fixture
def grant_seed(db):
    """建 process 真实资源（module='settings'）+ application 反例资源。"""
    PermissionResource.objects.all().delete()
    RolePermissionV2.objects.all().delete()
    PermissionResource.objects.create(
        system_code='recruit',
        resource_code='recruit:settings:recruitment_process:edit',
        resource_name='编辑招聘流程', resource_type='BUTTON', module='settings', status=1,
    )
    PermissionResource.objects.create(
        system_code='recruit', resource_code='recruit:application:edit',
        resource_name='推进申请', resource_type='BUTTON', module='application', status=1,
    )
    yield


def test_http_feature_granted_process_via_settings(admin_client, role, grant_seed):
    """授 recruitment-process:edit 经真实 GET -> process 卡 featureGranted=True, candidate=False。

    实现者 test_process_granted_via_settings_module 函数级验 build_modules_response；
    本例验 build_modules_response 经真实端点 GET 回显，且 process->settings 映射生效
    （工单原 process->application 会让真实管流程角色被禁用）。
    """
    RolePermissionV2.objects.create(
        role_code=role.role_code, system_code='recruit',
        resource_code='recruit:settings:recruitment_process:edit',
    )
    status, body = _http_get(admin_client, role)
    assert status == 200, body
    assert _module_of(body, 'process')['featureGranted'] is True
    assert _module_of(body, 'candidate')['featureGranted'] is False


def test_http_feature_granted_super_admin_always_true(admin_client, grant_seed):
    """SUPER_ADMIN 角色经真实 GET -> 5 模块 featureGranted 全 True（绕过资源判定）。"""
    sa = RoleV2.objects.create(
        system_code='recruit', role_code='SUPER_ADMIN', role_name='超管', status=1,
    )
    status, body = _http_get(admin_client, sa)
    assert status == 200, body
    for m in body['data']['modules']:
        assert m['featureGranted'] is True, m['moduleKey']


def test_http_feature_granted_cross_system_not_leaked(admin_client, role, grant_seed):
    """同名 role_code 在 other_sys 授 candidate 资源 -> 经真实 GET recruit 侧仍为 False。

    实现者 test_cross_system_permission_not_leaked 函数级验；本例验经真实端点
    （build_modules_response 的 system_code=role.system_code 过滤）确实不过滤跨系统。
    """
    RolePermissionV2.objects.create(
        role_code=role.role_code, system_code='other_sys',
        resource_code='recruit:candidate:list',
    )
    status, body = _http_get(admin_client, role)
    assert status == 200, body
    assert _module_of(body, 'candidate')['featureGranted'] is False
