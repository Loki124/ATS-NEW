"""S5-35：数据权限「校招生管理」独立配置卡 —— 维度下发 + 编译穿透（真实 MySQL DB）。

需求（2026-10-21 兵哥）：数据权限中增加针对校招生管理模块的单独配置，
条件支持选择「员工HRBP / 班长 / 班主任 / 导师」，判断符为包含/不包含，
校验值为固定/当前登录用户。

覆盖三层（缺一不可，否则会出现「界面能选、存进去、执行不生效」）：
  1. **下发层**（options_payload）：校招生管理卡存在，可见维度恰为四个人员关系
     维度，且每个维度都带 user 类运算符（包含/不包含）与动态源键。
  2. **校验层**（validate_scope_payload）：四维度均可保存，运算符合法，
     动态源 currentUser.id 适用。
  3. **执行层**（compile_scope_q + 真实过滤）：静态固定值与动态「当前登录用户」
     都能编译成正确的 Q，并只命中目标人员带的那条轮岗安排。

另含两个反向护栏：
  - 隐藏维度（owner/campus_class/dept/creator）不出现在下拉，但仍能编译（存量兼容）；
  - 校招生管理卡的模块键与运行时 data_perm_entity 一致（否则规则永远不生效）。
"""
import uuid

import pytest
from django.contrib.auth import get_user_model

from apps.campus_rotation.models import ClassRoom, RotationArrangement
from apps.core.models import Department
from apps.data_permission.expr_compiler import compile_scope_q, validate_scope_payload
from apps.data_permission.field_map import MODULE_LABELS, MODULE_ORDER
from apps.data_permission.role_scope_api import options_payload

pytestmark = pytest.mark.django_db

# 校招生管理卡对应的模块键与实体键（必须一致，见测试 6）
CAMPUS_MODULE_KEY = 'campus_arrangement'

# 需求指定的四个条件维度
EXPECTED_DIMS = {'hrbp', 'class_monitor', 'head_teacher', 'mentor'}


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _user(tag: str = "u"):
    return get_user_model().objects.create_user(username=_uid(tag), password="Test@1234")


def _dept() -> Department:
    return Department.objects.create(id=_uid("dept"), name=_uid("BG"), code=_uid("BG"))


def _class_room(hrbp, head_teacher, batch="2026秋招") -> ClassRoom:
    """建班级：HRBP 与班主任挂在班级上（员工的 HRBP 经班级取）。"""
    return ClassRoom.objects.create(
        code=_uid("CL"), name=_uid("班"), hrbp=hrbp, head_teacher=head_teacher,
        batch=batch,
    )


def _arrangement(person_id: int, *, class_room=None, hrbp=None, head_teacher=None,
                 mentor=None, class_monitor=None, dept=None) -> RotationArrangement:
    return RotationArrangement.objects.create(
        person_id=person_id,
        class_room=class_room,
        intent_bu='能智BG',
        head_teacher=head_teacher,
        mentor=mentor,
        class_monitor=class_monitor,
        current_dept=dept,
        created_by=hrbp,
        updated_by=hrbp,
    )


def _compile(dimension: str, *, user_ids=None, operator="in", value_source="static",
             dynamic_key=None, user=None, entity=CAMPUS_MODULE_KEY):
    cond = {"dimension": dimension, "operator": operator}
    if value_source == "dynamic":
        cond["valueSource"] = "dynamic"
        cond["dynamicKey"] = dynamic_key
    else:
        cond["values"] = [{"id": i} for i in (user_ids or [])]
    payload = {"expr": "", "groups": [{"expr": "", "conditions": [cond]}]}
    return compile_scope_q(payload, entity, user=user)


# ---------------------------------------------------------------------------
# 1. 下发层：校招生管理卡 + 四个维度 + 运算符 + 动态源
# ---------------------------------------------------------------------------
def test_campus_module_card_is_published_with_four_person_dimensions():
    """options_payload 必须下发校招生管理卡，且可见维度恰为需求指定的四个。"""
    # 先建一个用户：user 类维度的「固定」值选项来自真实用户表
    # （_user_options() 读 User 表），无用户时 options 为空列表。
    _user("opt_src")

    resp = options_payload()
    modules = {m['moduleKey']: m for m in resp['modules']}

    assert CAMPUS_MODULE_KEY in modules, '校招生管理卡未下发'
    card = modules[CAMPUS_MODULE_KEY]
    assert card['label'] == '校招生管理', f"卡片文案不对：{card['label']}"
    assert card['label'] == MODULE_LABELS[CAMPUS_MODULE_KEY]

    visible = {d['key'] for d in card['dimensions']}
    assert visible == EXPECTED_DIMS, f'可见维度不符预期（多/缺）：{visible ^ EXPECTED_DIMS}'

    # 每个维度都必须是 user 类：带包含/不包含运算符 + 当前登录用户动态源
    for d in card['dimensions']:
        assert d['valueType'] == 'user', f"维度 {d['key']} 必须是 user 类"
        ops = {o['value'] for o in d.get('operators', [])}
        assert {'in', 'not_in'} <= ops, f"维度 {d['key']} 缺少包含/不包含运算符：{ops}"
        assert 'currentUser.id' in (d.get('contextKeys') or []), \
            f"维度 {d['key']} 未接入「当前登录用户」动态源"
        # 固定值选项必须有值源（用户下拉），否则「固定」是空控件
        assert d.get('options'), f"维度 {d['key']} 无固定值选项源"


def test_campus_module_hidden_dimensions_not_offered():
    """隐藏维度不下发，但后端映射保留（存量规则仍可编译）。"""
    card = next(m for m in options_payload()['modules'] if m['moduleKey'] == CAMPUS_MODULE_KEY)
    visible = {d['key'] for d in card['dimensions']}
    for hidden in ('owner', 'campus_class', 'dept', 'creator'):
        assert hidden not in visible, f'隐藏维度 {hidden} 不应出现在下拉'


def test_campus_module_in_module_order():
    """校招生管理卡必须进入 MODULE_ORDER（否则 GET/POST 端点不接受该模块）。"""
    assert CAMPUS_MODULE_KEY in MODULE_ORDER
    assert MODULE_ORDER.index(CAMPUS_MODULE_KEY) == len(MODULE_ORDER) - 1, \
        '校招生管理卡应排在最后（校招域独立于社招五模块）'


# ---------------------------------------------------------------------------
# 2. 校验层：保存期校验放行
# ---------------------------------------------------------------------------
def test_validate_scope_payload_accepts_four_dimensions():
    """四维度 + 包含/不包含 + 固定/动态，四种组合都必须通过保存期校验。"""
    for dim in sorted(EXPECTED_DIMS):
        for operator in ('in', 'not_in'):
            static = {"expr": "", "groups": [{"expr": "", "conditions": [
                {"dimension": dim, "operator": operator, "values": [{"id": 1}]},
            ]}]}
            assert validate_scope_payload(static, CAMPUS_MODULE_KEY) is None, \
                f'{dim}/{operator} 固定值应可保存'

            dynamic = {"expr": "", "groups": [{"expr": "", "conditions": [
                {"dimension": dim, "operator": operator, "values": [],
                 "valueSource": "dynamic", "dynamicKey": "currentUser.id"},
            ]}]}
            assert validate_scope_payload(dynamic, CAMPUS_MODULE_KEY) is None, \
                f'{dim}/{operator} 动态值应可保存'


def test_validate_scope_payload_rejects_bad_operator():
    """越权运算符必须被拦（防止前端传 is_empty 到用户类维度）。"""
    bad = {"expr": "", "groups": [{"expr": "", "conditions": [
        {"dimension": "class_monitor", "operator": "is_empty", "values": []},
    ]}]}
    reason = validate_scope_payload(bad, CAMPUS_MODULE_KEY)
    assert reason, 'is_empty 对 class_monitor 应被拒绝'


# ---------------------------------------------------------------------------
# 3. 执行层：静态固定值 + 动态「当前登录用户」真实穿透
# ---------------------------------------------------------------------------
def test_campus_class_monitor_static_and_dynamic_filter_real_rows():
    """班长维度：固定值与当前登录用户都只命中目标人员带的那条记录。"""
    dept = _dept()
    hrbp = _user("hrbp")
    head_teacher = _user("ht")
    monitor_a = _user("mon_a")
    monitor_b = _user("mon_b")

    room = _class_room(hrbp, head_teacher)
    arr_a = _arrangement(900001, class_room=room, hrbp=hrbp, head_teacher=head_teacher,
                         mentor=monitor_a, class_monitor=monitor_a, dept=dept)
    arr_b = _arrangement(900002, class_room=room, hrbp=hrbp, head_teacher=head_teacher,
                         mentor=monitor_b, class_monitor=monitor_b, dept=dept)

    # 静态：班长包含 monitor_a
    q = _compile('class_monitor', user_ids=[monitor_a.pk])
    assert q is not None, 'class_monitor 应编译出非空 Q'
    matched = set(RotationArrangement.objects.filter(q).values_list('pk', flat=True))
    assert arr_a.pk in matched, '班长=monitor_a 的轮岗安排应命中'
    assert arr_b.pk not in matched, '班长=monitor_b 的轮岗安排不应命中'

    # 静态 not_in：取反
    q_neg = _compile('class_monitor', user_ids=[monitor_a.pk], operator='not_in')
    matched_neg = set(RotationArrangement.objects.filter(q_neg).values_list('pk', flat=True))
    assert arr_b.pk in matched_neg, 'not_in 应命中非 monitor_a 的记录'
    assert arr_a.pk not in matched_neg

    # 动态：当前登录用户 = monitor_a -> 只命中自己带的那条
    q_dyn = _compile('class_monitor', value_source='dynamic',
                     dynamic_key='currentUser.id', user=monitor_a)
    assert q_dyn is not None
    matched_dyn = set(RotationArrangement.objects.filter(q_dyn).values_list('pk', flat=True))
    assert arr_a.pk in matched_dyn, '动态「当前登录用户」应命中自己是班长的记录'
    assert arr_b.pk not in matched_dyn, '动态「当前登录用户」不应命中别人的记录'


def test_campus_hrbp_head_teacher_mentor_dimensions_filter_real_rows():
    """员工HRBP（经班级）/ 班主任 / 导师 三个维度同样可按人过滤。"""
    dept = _dept()
    hrbp = _user("hrbp")
    other_hrbp = _user("hrbp2")
    head_teacher = _user("ht")
    mentor = _user("mentor")

    room = _class_room(hrbp, head_teacher)
    room_other = _class_room(other_hrbp, head_teacher)
    arr_mine = _arrangement(910001, class_room=room, hrbp=hrbp, head_teacher=head_teacher,
                            mentor=mentor, dept=dept)
    arr_other = _arrangement(910002, class_room=room_other, hrbp=other_hrbp,
                             head_teacher=head_teacher, mentor=mentor, dept=dept)

    # 员工HRBP：经班级取 hrbp
    q = _compile('hrbp', user_ids=[hrbp.pk])
    matched = set(RotationArrangement.objects.filter(q).values_list('pk', flat=True))
    assert arr_mine.pk in matched, '员工HRBP=hrbp 应命中'
    assert arr_other.pk not in matched, '员工HRBP=other 应不命中'

    # 班主任
    q = _compile('head_teacher', user_ids=[head_teacher.pk])
    matched = set(RotationArrangement.objects.filter(q).values_list('pk', flat=True))
    assert arr_mine.pk in matched and arr_other.pk in matched, '班主任相同则两条都命中'

    # 导师（动态当前登录用户）
    q_dyn = _compile('mentor', value_source='dynamic',
                     dynamic_key='currentUser.id', user=mentor)
    matched_dyn = set(RotationArrangement.objects.filter(q_dyn).values_list('pk', flat=True))
    assert arr_mine.pk in matched_dyn and arr_other.pk in matched_dyn


def test_hidden_dimensions_still_compile_for_legacy_rules():
    """隐藏维度只影响 UI 下拉，后端仍能编译（存量规则不因隐藏而失效）。"""
    dept = _dept()
    hrbp = _user("hrbp")
    arr = _arrangement(920001, hrbp=hrbp, dept=dept)

    q = _compile('creator', user_ids=[hrbp.pk])
    assert q is not None, '隐藏维度 creator 仍应可编译'
    assert arr.pk in set(RotationArrangement.objects.filter(q).values_list('pk', flat=True))


# ---------------------------------------------------------------------------
# 4. 端到端：走真实 HTTP 链路，证明配置卡「配了就生效」
# ---------------------------------------------------------------------------
def test_campus_card_rule_actually_filters_via_real_http():
    """校招生管理卡的规则经真实 API 保存后，轮岗安排列表真的被过滤。

    🔴 这是本需求的关键验收点：新增一张配置卡若只在 options 里露出维度、
    但规则存不进 / 存进了不执行，管理员会看到「配了没反应」——比不做更糟。

    链路：RoleEditModal 保存 -> POST /roles/{id}/data-permissions/（真实端点，
    经 CamelCaseJSONParser + normalize）-> DataPermissionRule 行 ->
    GET /campus-rotation/rotation-arrangements/（真实列表端点，
    经 ScopeQuerysetMixin -> scope_filter_q -> role_entity_scope_q -> 编译器）。
    """
    from django.db import connection
    from django.utils import timezone
    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken

    from apps.core.models_permission_v2 import RoleV2
    from apps.data_permission.role_scope_api import upsert_modules

    def _insert_role_ignore(code: str) -> RoleV2:
        now = timezone.now()
        with connection.cursor() as c:
            c.execute(
                """INSERT IGNORE INTO roles
                   (system_code, role_code, role_name, description, is_system,
                    status, default_data_scope_type, created_at, updated_at)
                   VALUES ('recruit', %s, %s, '', 0, 1, 'SELF', %s, %s)""",
                [code, code, now, now],
            )
        return RoleV2.objects.get(role_code=code, system_code='recruit')

    role = _insert_role_ignore('HRBP')
    dept = _dept()

    # 登录用户 = 班长本人（角色挂在**这个**用户身上，否则列表端点 403）
    monitor = _user("http_monitor")
    other_monitor = _user("http_other_monitor")
    hrbp = _user("http_hrbp")
    head_teacher = _user("http_ht")

    now = timezone.now()
    with connection.cursor() as c:
        c.execute(
            """INSERT IGNORE INTO user_roles
               (user_id, role_code, system_code, granted_by_id, granted_at, updated_at)
               VALUES (%s, %s, 'recruit', %s, %s, %s)""",
            [monitor.pk, 'HRBP', monitor.pk, now, now],
        )
    # 授予列表权限（走真实 V2Permission 守卫）
    with connection.cursor() as c:
        c.execute(
            """INSERT IGNORE INTO role_permission
               (role_code, resource_code, system_code, created_at)
               VALUES (%s, %s, 'recruit', %s)""",
            ['HRBP', 'recruit:campus:rotation:list', now],
        )

    room = _class_room(hrbp, head_teacher)
    arr_mine = _arrangement(930001, class_room=room, hrbp=hrbp, head_teacher=head_teacher,
                            mentor=monitor, class_monitor=monitor, dept=dept)
    arr_other = _arrangement(930002, class_room=room, hrbp=hrbp, head_teacher=head_teacher,
                             mentor=other_monitor, class_monitor=other_monitor, dept=dept)

    # 通过真实保存入口写入规则（模拟管理员在弹窗里点「保存」）
    payload = [{
        'moduleKey': CAMPUS_MODULE_KEY,
        'mode': 'scope',
        'expr': '',
        'groups': [{
            'id': 'g1', 'expr': '',
            'conditions': [{
                'id': 'c1', 'dimension': 'class_monitor', 'operator': 'in',
                'valueSource': 'dynamic', 'dynamicKey': 'currentUser.id', 'values': [],
            }],
        }],
        'write': {'mode': 'none', 'expr': '', 'groups': [], 'actions': []},
    }]
    upsert_modules(role, payload, monitor)

    from apps.data_permission.models import DataPermissionRule
    rule = DataPermissionRule.objects.filter(
        dimension_type='ROLE', dimension_value='HRBP', level='ROW',
        entity=CAMPUS_MODULE_KEY, scope_type='CUSTOM',
    ).first()
    assert rule is not None, '规则未落库 —— 配置卡保存链路断了'

    # 真实列表端点：登录用户 = monitor，应只看到自己当班长的那条
    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(monitor).access_token}')

    resp = client.get('/api/v1/campus-rotation/rotation-arrangements/', {'page_size': 200})
    assert resp.status_code == 200, resp.content.decode()
    body = resp.json()
    ids = {row['id'] for row in body['data']}
    assert arr_mine.id in ids, '当前登录用户当班长的轮岗安排应可见'
    assert arr_other.id not in ids, '别人当班长的轮岗安排不应可见'

