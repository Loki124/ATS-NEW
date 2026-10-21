"""QA 独立验证：字段 ACL 写接口真实路由 + 缓存立即生效（P0-2 可配，C3）。

## 为什么要有这个文件

实现者声称"路由问题是真正阻塞点"（原 `@action(url_path='rules', methods=['get'])`
占用 path，PUT/DELETE 会 405/404），修法是合并进同一个 `@action`。
这个断言必须**打真实 URL** 才有效 —— 直接调 `FieldACLViewSet().rules(request)`
会绕过 DRF router + Django URL resolver，掩盖了"路由不可达"这类真实缺陷。

## 覆盖（按优先级）

| # | 场景 | 期望 |
|---|---|---|
| 1 | GET/PUT/DELETE 同 path 三方法均可达 | 非 404/405 |
| 2 | 新建 → 重查能读到 → 删除后查不到 | 真实往返 |
| 3 | 写完**立即**生效（不等 60s TTL） | 防"假生效" |
| 4 | 不存在的角色 code → 400 且**不落库** | 双重断言 |
| 5 | 缺参 DELETE → 400 且文案说明缺哪些 | 可定位 |
| 6 | 幂等：重复 PUT 同三元组不建重复行 | 200 不 201 |
| 7 | P2-1 双字段：permission 权威 + action 过渡，三态映射一致 | 契约锁定 |
| 8 | GET→PUT 往返（GET 值原样 PUT 回） | 200 不再 400 |

## 反假绿

场景 3 是本文件的核心：若 invalidate 失效，用例会因读到旧缓存而失败，
而不是"看起来保存成功了"。场景 4 同时断言状态码与行数，任一不满足即红。
"""
import pytest
from django.test import Client

from apps.core.models import User
from apps.core.models_permission_v2 import RoleV2
from apps.field_acl.models import FieldACL
from apps.field_acl.services import FieldAclService

RULES_URL = '/api/v1/field-acl/rules/'


def _token(user):
    from rest_framework_simplejwt.tokens import RefreshToken
    return 'Bearer ' + str(RefreshToken.for_user(user).access_token)


@pytest.fixture
def super_admin(db):
    return User.objects.create(username='qa_acl_writer', is_superuser=True, is_active=True)


@pytest.fixture
def role(db):
    return RoleV2.objects.create(
        system_code='recruit', role_code='QA_ACL_WRITE_ROLE',
        role_name='QA 写接口角色', status=1,
    )


def _client_for(user):
    c = Client()
    c._qa_token = _token(user)
    return c


def _call(client, method, body=None):
    import json
    data = json.dumps(body).encode() if body is not None else None
    r = getattr(client, method)(
        RULES_URL, data=data, content_type='application/json',
        HTTP_AUTHORIZATION=client._qa_token,
    )
    try:
        return r.status_code, r.json()
    except Exception:  # pragma: no cover
        return r.status_code, {'_raw': r.content[:300].decode('utf-8', 'replace')}


# ============ V3-1：真实路由三方法可达 ============

def test_rules_url_is_registered():
    """路由注册自检：`/field-acl/rules/` 的 method_map 必须含 get/put/delete。

    这条专防"加了新 @action 但被首条 GET-only pattern 挡住"的路由回归 ——
    那种情况下直接调 view 方法一切正常，只有真打 URL 才会暴露。
    用 `django.urls.resolve()` 拿权威解析结果，而不是自己递归 pattern
    （QA 第一版手写递归没处理 include 嵌套，误报"未注册"）。
    """
    from django.urls import resolve

    match = resolve('/api/v1/field-acl/rules/')
    assert match is not None, '/api/v1/field-acl/rules/ 无法解析'

    cb = match.func
    actions = getattr(cb, 'actions', None) or {}
    assert actions, (
        f'field-acl/rules 的 callback 无 actions 映射（method_map 为空）: {cb}'
    )
    missing = {'get', 'put', 'delete'} - set(actions)
    assert not missing, (
        f'同一 url_path 未覆盖 {missing} —— 若它们是另一个 @action，会被首条 '
        f'pattern 挡住导致 404/405。当前 method_map={sorted(actions)}'
    )


def test_put_delete_get_all_reachable_over_http(super_admin, role):
    """PUT → GET → DELETE → GET 全链路打真实 URL，均不得 404/405。"""
    c = _client_for(super_admin)
    payload = {
        'entity': 'application', 'field': 'candidate_phone',
        'roleCode': role.role_code, 'permission': 'MASK',
    }

    s, _ = _call(c, 'put', payload)
    assert s not in (404, 405), f'PUT 路由不可达：HTTP {s}'

    s, _ = _call(c, 'get')
    assert s not in (404, 405), f'GET 路由不可达：HTTP {s}'

    s, _ = _call(c, 'delete', {k: v for k, v in payload.items()})
    assert s not in (404, 405), f'DELETE 路由不可达：HTTP {s}'


# ============ V3-2：真实往返 ============

def test_create_then_read_then_delete_roundtrip(super_admin, role):
    """新建 → 重新请求能查到 → 删除后查不到（三步式，非单步断言）。"""
    c = _client_for(super_admin)
    payload = {
        'entity': 'application', 'field': 'candidate_phone',
        'roleCode': role.role_code, 'permission': 'NONE',
    }

    # 造前无行
    assert FieldACL.objects.filter(
        entity='application', field='candidate_phone', role_code=role.role_code,
    ).count() == 0, '前置条件失败：建前应无行'

    s, body = _call(c, 'put', payload)
    assert s == 201, f'新建应 201，实际 HTTP {s}: {body}'

    # 重新请求能查到
    s, body = _call(c, 'get')
    assert s == 200, f'HTTP {s}'
    rows = body.get('data') or []
    hit = [r for r in rows
           if (r.get('resource') or r.get('entity')) == 'application'
           and r.get('field') == 'candidate_phone'
           and (r.get('roleCode') or r.get('role_code')) == role.role_code]
    assert hit, f'新建后 GET 查不到该规则：{rows[:3]}'
    # 旧词汇 action 过渡期仍在（NONE→HIDE）；P2-1 起 permission 权威字段并存，
    # 双字段一致性由 test_rules_list_carries_authoritative_permission 锁定。
    assert hit[0].get('action') == 'HIDE', (
        f'NONE 应投影为旧词汇 HIDE，实际：{hit[0]}'
    )

    # 删除后查不到
    s, body = _call(c, 'delete', payload)
    assert s == 200, f'删除应 200，实际 HTTP {s}: {body}'
    assert body['data']['deleted'] == 1, f'应删 1 行：{body}'

    s, body = _call(c, 'get')
    rows = body.get('data') or []
    again = [r for r in rows
             if (r.get('resource') or r.get('entity')) == 'application'
             and r.get('field') == 'candidate_phone'
             and (r.get('roleCode') or r.get('role_code')) == role.role_code]
    assert not again, f'删除后仍能查到：{again}'


def test_put_is_idempotent_no_duplicate_rows(super_admin, role):
    """重复 PUT 同三元组 → 第二次 200（更新）且不产生第二行。"""
    c = _client_for(super_admin)
    payload = {
        'entity': 'application', 'field': 'candidate_phone',
        'roleCode': role.role_code, 'permission': 'MASK',
    }
    s1, _ = _call(c, 'put', payload)
    assert s1 == 201, f'首次应 201，实际 {s1}'

    s2, _ = _call(c, 'put', {**payload, 'permission': 'NONE'})
    assert s2 == 200, f'命中同三元组应 200（更新），实际 {s2}'

    assert FieldACL.objects.filter(
        entity='application', field='candidate_phone', role_code=role.role_code,
    ).count() == 1, '幂等 upsert 产生了重复行'


def test_delete_is_idempotent_for_missing_rule(super_admin, role):
    """删不存在的规则 → 200 + deleted:0（前端 Toast 撤销可无脑重放）。"""
    c = _client_for(super_admin)
    s, body = _call(c, 'delete', {
        'entity': 'application', 'field': 'no_such_field_x',
        'roleCode': role.role_code,
    })
    assert s == 200, f'删不存在的应幂等 200，实际 HTTP {s}: {body}'
    assert body['data']['deleted'] == 0, f'应 deleted=0：{body}'


# ============ V3-3：缓存立即生效（防"假生效"）============

def test_rule_takes_effect_immediately_no_60s_wait(super_admin, role, department):
    """🔴 写完必须立即生效，不能等 60s TTL（防"假生效"）。

    ⚠️ QA 两次注入反证（防假绿，都有实测记录）：
      1. 第一版只断言 `get_rules_map()` —— 注入"去掉显式 invalidate"后**仍然绿**，
         因为 `signals.py` 的 post_save/post_delete 也在清缓存，把缺陷遮住了。
         这种"看起来验证了缓存失效"的用例就是假绿。
      2. 故改为**端到端**断言：PUT 之后立刻走真实序列化器读字段，
         这同时覆盖显式 invalidate 与信号两条路径，任一失效都会红。
    """
    from rest_framework.test import APIRequestFactory

    from apps.application.serializers import ApplicationListSerializer
    from apps.candidate.models import Candidate
    from apps.position.models import Position, PositionState
    from apps.process.models import (
        ProcessStageLink,
        RecruitmentProcess,
        RecruitmentStage,
        StageType,
    )
    from apps.application.models import Application

    # 造一条可序列化的投递（用超管自身作为创建人，便于读取）
    import uuid
    process = RecruitmentProcess.objects.create(
        code=f'CACHE{uuid.uuid4().hex[:6].upper()}', name='缓存流程',
        current_version='V1.0', version_seq=1, is_latest=True, status='ENABLED',
    )
    stage = RecruitmentStage.objects.create(
        code=f'CACHES{uuid.uuid4().hex[:6].upper()}', name='缓存阶段',
        stage_type=StageType.SCREEN,
    )
    link = ProcessStageLink.objects.create(process=process, stage=stage, order=1, is_required=True)
    position = Position.objects.create(
        code=f'CACHEP{uuid.uuid4().hex[:6].upper()}', title='缓存职位',
        department=department, hiring_manager=super_admin, owner=super_admin,
        process=process, state=PositionState.DRAFT,
    )
    cand = Candidate.objects.create(name='缓存候选人', phone='13812348000')
    app = Application.objects.create(
        code=f'CACHEA{uuid.uuid4().hex[:8].upper()}', candidate=cand,
        position=position, process=process, workflow_version='V1.0',
        current_link=link, current_stage=stage,
    )
    # 观察者必须是**持有该角色的非超管**：超管会 bypass ACL 直接看明文，
    # 用超管观察会让"是否生效"的断言恒真（QA 实测踩过，第一版因此假绿）。
    from apps.core.models_permission_v2 import RolePermissionV2, UserRoleV2
    observer = User.objects.create(
        username='qa_acl_cache_observer', is_active=True, department=department,
    )
    UserRoleV2.objects.create(
        user_id=observer.pk, role_code=role.role_code, system_code='recruit',
    )
    RolePermissionV2.objects.get_or_create(
        role_code=role.role_code, resource_code='recruit:candidate:application:list',
        system_code='recruit',
    )
    req = APIRequestFactory().get('/api/v1/applications/')
    req.user = observer

    c = _client_for(super_admin)
    # ⚠️ 用 `candidate_name` 而非 `candidate_phone`：后者被
    # test_p0_4_acl_security_qa.py 的多个用例共用，且 conftest 只清
    # `field_acl:rules:*` 键（不像 QA 此前的覆盖 fixture 那样 cache.clear()），
    # 曾观察到约 1/14 的偶发失败。换成一个**无其他用例触碰、也不在默认
    # 脱敏清单**的字段，使本用例完全自洽（hermetic）。
    payload = {
        'entity': 'application', 'field': 'candidate_name',
        'roleCode': role.role_code, 'permission': 'NONE',
    }

    # 前置：此刻该字段仍在（无规则 → READ → 明文保留）
    before = ApplicationListSerializer(app, context={'request': req}).data
    assert 'candidate_name' in before, '前置条件失败：规则生效前字段应存在'

    s_put, _ = _call(c, 'put', payload)
    assert s_put == 201, f'HTTP {s_put}'

    # 关键：**无 sleep**，端到端立刻生效
    after = ApplicationListSerializer(app, context={'request': req}).data
    assert 'candidate_name' not in after, (
        '写入后未立即生效 —— 疑似缓存未失效（要等 60s TTL 才生效）。'
        f'before={before.get("candidate_name")!r} after={after.get("candidate_name")!r}'
    )

    # 删除同样必须立即生效
    s_del, _ = _call(c, 'delete', payload)
    assert s_del == 200
    after_del = ApplicationListSerializer(app, context={'request': req}).data
    assert 'candidate_name' in after_del, (
        '删除后未立即生效（字段仍未恢复）—— 缓存失效链路仍有缺口'
    )


# ============ V3-4：非法角色 → 400 且不落库（双重断言）============

def test_unknown_role_code_400_and_no_row_created(super_admin, role):
    """role_code 不存在 → 400 **且**行数未增（失败必须响亮，禁静默写孤儿）。"""
    c = _client_for(super_admin)

    before = FieldACL.objects.count()
    assert before == 0, f'前置条件失败：建前应无规则行，实际 {before}'

    s, body = _call(c, 'put', {
        'entity': 'application', 'field': 'candidate_phone',
        'roleCode': 'NO_SUCH_ROLE_QA_X', 'permission': 'MASK',
    })

    # 断言一：状态码
    assert s == 400, f'不存在的角色应 400，实际 HTTP {s}: {body}'
    # 断言二：文案可定位（字段级错误在 errors 里，message 只是通用文案）
    assert body.get('success') is False
    errs = body.get('errors') or {}
    blob = str(errs) + str(body.get('message') or '')
    assert '角色' in blob or '不存在' in blob, (
        f'错误文案未说明是角色问题：{body}'
    )
    assert 'roleCode' in errs or 'role_code' in errs, (
        f'错误未定位到 roleCode 字段：{body}'
    )
    # 断言三：未落库（双重的"未落库"半边）
    assert FieldACL.objects.count() == before, (
        f'400 之后仍落库：{before} -> {FieldACL.objects.count()}'
    )
    assert not FieldACL.objects.filter(role_code='NO_SUCH_ROLE_QA_X').exists(), (
        '写入了孤儿规则行'
    )


# ============ V3-5：缺参与非法三态 ============

def test_delete_missing_params_400_lists_which(super_admin, role):
    """DELETE 缺三元组 → 400 且文案说明缺了哪些（错误要能定位问题）。"""
    c = _client_for(super_admin)
    s, body = _call(c, 'delete', {'entity': 'application'})
    assert s == 400, f'缺参应 400，实际 HTTP {s}: {body}'
    msg = body.get('message', '')
    assert 'field' in msg, f'应说明缺 field：{body}'
    assert 'role_code' in msg, f'应说明缺 role_code：{body}'


def test_put_bad_permission_value_400(super_admin, role):
    """三态之外的词汇（如已废弃的 HIDE）→ 400，禁自建映射表。"""
    c = _client_for(super_admin)
    before = FieldACL.objects.count()

    s, body = _call(c, 'put', {
        'entity': 'application', 'field': 'candidate_phone',
        'roleCode': role.role_code, 'permission': 'HIDE',
    })
    assert s == 400, f'废弃词汇 HIDE 应 400，实际 HTTP {s}: {body}'
    assert FieldACL.objects.count() == before, '非法 permission 却落库'


def test_rules_requires_super_admin(role):
    """非超管 → 403（ACL 配置是超管权限，不能被普通 HR 改）。"""
    from apps.core.models import User
    from apps.core.models_permission_v2 import RolePermissionV2, UserRoleV2
    from apps.field_acl.views import FieldACLViewSet

    plain = User.objects.create(username='qa_acl_nonadmin', is_active=True)
    UserRoleV2.objects.create(
        user_id=plain.pk, role_code=role.role_code, system_code='recruit',
    )
    c = _client_for(plain)

    s, body = _call(c, 'put', {
        'entity': 'application', 'field': 'candidate_phone',
        'roleCode': role.role_code, 'permission': 'MASK',
    })
    assert s == 403, f'非超管改 ACL 应 403，实际 HTTP {s}: {body}'
    assert not FieldACL.objects.exists(), '非超管的写入竟然落库了'


# ============ V3-6：契约一致性（P2-1 双字段 + GET→PUT 往返） ============

#: 三态 → 旧词汇的权威映射（与 serializers.PERMISSION_TO_ACTION 一致，
#: 这里**硬编码**而非 import，避免用被测代码自证（同函数会变成恒真断言）。
PERMISSION_ACTION_PAIRS = [
    ('READ', 'VIEW'),
    ('MASK', 'MASK'),
    ('NONE', 'HIDE'),
]


@pytest.mark.parametrize('permission,expected_action', PERMISSION_ACTION_PAIRS)
def test_rules_list_carries_authoritative_permission(
    super_admin, role, permission, expected_action,
):
    """P2-1 契约：GET /rules 同时回权威 `permission`（READ/MASK/NONE）与过渡 `action`。

    背景（P2-1，commit 98557be9）：修复前 `FieldAclRuleSerializer` 只回旧词汇
    `action`（VIEW/MASK/HIDE），而 matrix 端点已回双字段（permission 权威 +
    action 过渡），两处口径不一致：
      1. 前端 `FieldAclSettings.vue reload()` 读 `r.permission` 建基线快照恒为
         undefined —— 该段是死代码。但**基线值不变**：matrix 端点由同一张
         FieldACL 表构建（rules ⊆ matrix，QA 已核实 views.matrix 用
         `FieldACL.objects.all()`），且 FE 的 matrix 循环在 rules 循环之后
         以同源数据覆盖，兜底产出正确基线。即"值不变、死代码变活代码"；
      2. 往返断裂（真实用户可见缺陷）：GET 回 `action:'HIDE'`，PUT 却拒收
         `permission:'HIDE'`（旧词汇不是合法代码枚举，见
         test_put_bad_permission_value_400），客户端 GET→改→PUT 必 400。

    本用例锁住修复后的双字段契约（action 为 TODO(P0-4 过渡) 字段，下批删）：
      1. `permission` 存在且 ∈ {READ, MASK, NONE}（代码枚举，非旧词汇）；
      2. `action` 过渡期仍在，且与 permission 严格一致（映射硬编码在本文件）；
      3. 三态全覆盖，不允许"只修了某一个取值"。
    """
    c = _client_for(super_admin)
    assert FieldACL.objects.filter(
        entity='application', field='candidate_phone', role_code=role.role_code,
    ).count() == 0, '前置条件失败：建前应无行'

    s_put, body_put = _call(c, 'put', {
        'entity': 'application', 'field': 'candidate_phone',
        'roleCode': role.role_code, 'permission': permission,
    })
    assert s_put == 201, f'新建应 201，实际 HTTP {s_put}: {body_put}'

    s_get, body = _call(c, 'get')
    assert s_get == 200, f'HTTP {s_get}'
    rows = body.get('data') or []
    hit = [r for r in rows
           if r.get('field') == 'candidate_phone'
           and (r.get('roleCode') or r.get('role_code')) == role.role_code]
    assert hit, f'GET 查不到该规则：{rows[:3]}'
    row = hit[0]

    # 断言一：权威 permission 存在且为代码枚举
    assert 'permission' in row, f'rules 列表缺权威 permission 字段：{row}'
    assert row['permission'] == permission, (
        f'permission 应回显所写入的 {permission}，实际 {row.get("permission")!r}'
    )
    assert row['permission'] in {'READ', 'MASK', 'NONE'}, (
        f'permission 必须是代码枚举而非旧词汇：{row.get("permission")!r}'
    )

    # 断言二：过渡 action 仍在且与 permission 一致（映射为测试内置 ground truth）
    assert 'action' in row, f'过渡期 action 字段不应被提前删掉：{row}'
    assert row['action'] == expected_action, (
        f'{permission} 应投影为 {expected_action}，实际 {row.get("action")!r}'
    )


def test_get_put_roundtrip_with_permission_returns_200(super_admin, role):
    """端到端往返：PUT NONE → GET 得 `permission:'NONE'` → 原样 PUT 回 → 200。

    这是 P2-1 修复的**用户可见效果**：客户端"读列表→管理员改某个格子→保存"
    的往返链路不再 400。往返值直接取 GET 响应里的 `permission`（数据驱动），
    而不是在用例里硬编码 —— 若序列化器又退回只回 action，`row['permission']`
    会直接 KeyError（红），而不是绕过缺陷。
    """
    c = _client_for(super_admin)
    assert FieldACL.objects.filter(
        entity='application', field='candidate_phone', role_code=role.role_code,
    ).count() == 0, '前置条件失败：建前应无行'

    # 1. PUT NONE → 201
    s_put, body_put = _call(c, 'put', {
        'entity': 'application', 'field': 'candidate_phone',
        'roleCode': role.role_code, 'permission': 'NONE',
    })
    assert s_put == 201, f'新建应 201，实际 HTTP {s_put}: {body_put}'

    # 2. GET 得 permission:'NONE'
    s_get, body = _call(c, 'get')
    assert s_get == 200, f'HTTP {s_get}'
    rows = body.get('data') or []
    hit = [r for r in rows
           if r.get('field') == 'candidate_phone'
           and (r.get('roleCode') or r.get('role_code')) == role.role_code]
    assert hit, f'GET 查不到该规则：{rows[:3]}'
    got = hit[0].get('permission')
    assert got == 'NONE', f'GET 应回 permission:"NONE"，实际：{hit[0]}'

    # 3. 把 GET 得到的权威值原样 PUT 回 → 必须 200（更新而非新建）
    s_rt, body_rt = _call(c, 'put', {
        'entity': 'application', 'field': 'candidate_phone',
        'roleCode': role.role_code, 'permission': got,
    })
    assert s_rt == 200, (
        f'GET→PUT 往返应 200（幂等更新），实际 HTTP {s_rt}: {body_rt}'
    )

    # 4. 往返后仍只有一行，值未被改写
    assert FieldACL.objects.filter(
        entity='application', field='candidate_phone', role_code=role.role_code,
    ).count() == 1, '往返产生了重复行'
    s_get2, body2 = _call(c, 'get')
    rows2 = body2.get('data') or []
    hit2 = [r for r in rows2
            if r.get('field') == 'candidate_phone'
            and (r.get('roleCode') or r.get('role_code')) == role.role_code]
    assert hit2 and hit2[0].get('permission') == 'NONE', (
        f'往返后值应仍为 NONE：{hit2[:1]}'
    )
