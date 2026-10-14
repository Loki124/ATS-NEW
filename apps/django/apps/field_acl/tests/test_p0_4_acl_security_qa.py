"""QA 独立验证：字段 ACL 安全回归（P0-2 / P0-4）。

## 为什么这个文件存在（DR-03 的核心风险）

C3+C4+C6 做了两件**必须同批次**的事：
  1. 删掉 ApplicationListSerializer.get_candidate_phone 的硬编码两档脱敏；
  2. 把 DEFAULT_SENSITIVE_FIELDS['application'] 补为 ['candidate_phone','candidate_email']。

`_get_field_permission` 对「不在默认清单内」的字段返回 READ（原值放行）。
若两步不同步，效果会从「硬编码脱敏」退化为「**完全不脱敏**」——比原 bug 更严重，
且接口照常 200，肉眼极难发现（这正是 DR-03 要求实测反证的原因）。

本文件一律穿透真实 HTTP（GET /api/v1/applications/），
断言里显式区分「明文」与「脱敏形态」，不做"非空即通过"这类恒真断言。

##鉴别力自证（必读）

test_default_list_phone_is_masked_not_plaintext 在把
DEFAULT_SENSITIVE_FIELDS['application'] 改回 [] 时**必须失败**。
若你在本地注入后它仍绿，说明断言无效，请勿采信本文件结论。
"""
import json
import re

import pytest
from django.test import Client

from apps.core.models import User
from apps.core.models_permission_v2 import RoleV2, UserRoleV2
from apps.field_acl.models import FieldACL
from apps.field_acl.services import FieldAclService

LIST_URL = '/api/v1/applications/'
RULES_URL = '/api/v1/field-acl/rules/'

# 明确的长号码，便于断言脱敏形态（138****8000 形态可辨）
REAL_PHONE = '13812348000'
REAL_EMAIL = 'alice@example.com'


def _token(user):
    from rest_framework_simplejwt.tokens import RefreshToken
    return 'Bearer ' + str(RefreshToken.for_user(user).access_token)


# ⚠️ P1-1 回归护栏（QA 实测 + 工程师已修，2026-10-14）：
# 本文件**故意不再**用同名 fixture 覆盖 conftest 的
# `_isolate_field_acl_rules_cache`。此前 conftest 那条 autouse fixture
# 没有 db 依赖却会反查 FieldACL 表，导致任何 pytest 函数式用例在 setup 阶段
# 报 `RuntimeError: Database access not allowed`（QA 实测 8/8 全 ERROR），
# 而工程师的 TestCase 用例因自带事务不受影响 —— 是"只对 TestCase 生效"的
# 隐藏护栏缺口。
# 工程师已改为依赖 db。去掉覆盖后，本文件即成为该修复的**回归护栏**：
# 若 conftest 的 db 依赖被回删，这里会立刻 8/8 ERROR 而不是静默通过。


@pytest.fixture
def plain_user(db, department):
    """非超管 HR —— 脱敏验证的真正对象（超管会 bypass，见 test_superuser_*）。

    三个坑（QA 逐条实测，都是"接口 200 但列表空/403"的假绿陷阱）：
    1. 必须授予 `recruit:application:list`：ApplicationViewSet 声明了
       `permission_required`，无此码 GET /api/v1/applications/ 直接 **403**；
    2. 必须挂 `department`：ApplicationViewSet.scope_field = 'position__department'
       做行级过滤，无部门 → 列表恒空 → "脱敏断言"在空列表上恒不执行；
    3. 必须与 `_make_application()` 用同一个 department，否则同样空列表。
    """
    u = User.objects.create(
        username='qa_acl_plain', is_active=True, department=department,
    )
    RoleV2.objects.create(
        system_code='recruit', role_code='QA_ACL_ROLE', role_name='qa', status=1,
    )
    UserRoleV2.objects.create(
        user_id=u.pk, role_code='QA_ACL_ROLE', system_code='recruit',
    )
    from apps.core.models_permission_v2 import RolePermissionV2
    RolePermissionV2.objects.get_or_create(
        role_code='QA_ACL_ROLE',
        resource_code='recruit:application:list',
        system_code='recruit',
    )
    return u


@pytest.fixture
def admin(db):
    return User.objects.create(username='qa_acl_admin', is_superuser=True, is_active=True)


def _client_for(user):
    c = Client()
    c._qa_token = _token(user)
    return c


def _get(client, url):
    r = client.get(url, HTTP_AUTHORIZATION=client._qa_token)
    try:
        return r.status_code, r.json()
    except Exception:  # pragma: no cover
        return r.status_code, {'_raw': r.content[:300].decode('utf-8', 'replace')}


def _field(row, snake_name: str):
    """按字段名取值，兼容 drf-camel-case 渲染后的 camelCase 键。

    ⚠️ ACL 在序列化器 `to_representation` 阶段按 snake_case 键名（candidate_phone）
    裁决，camelCase 转换发生在之后的 renderer 阶段。所以 HTTP 响应里看到的是
    `candidatePhone` —— QA 第一版按 snake_case 取键得到 None，误判成"字段被删"。
    真实链路上必须按响应实际键名断言。
    """
    camel = re.sub(r'_([a-z])', lambda m: m.group(1).upper(), snake_name)
    for k in (camel, snake_name):
        if k in row:
            return row[k], k
    return None, None


def _first_row(body):
    rows = _rows(body)
    assert rows, f'列表为空，无法验证脱敏：{json.dumps(body, ensure_ascii=False)[:400]}'
    return rows[0]


def _rows(body):
    d = body.get('data', body)
    if isinstance(d, dict):
        for key in ('results', 'items', 'list', 'rows'):
            if isinstance(d.get(key), list):
                return d[key]
        if isinstance(d.get('data'), list):
            return d['data']
    return d if isinstance(d, list) else []


def _make_application(department, super_user, owner=None):
    """造一条投递记录（候选人手机号为明文长号码）。

    建法复用 apps/field_acl/tests/test_p0_4_acl_coverage.py:403 的
    `app_scenario` fixture（已处理 Position / RecruitmentProcess /
    ProcessStageLink 等 NOT NULL 外键）。**QA 第一版漏了 Position**，
    触发 `IntegrityError: NOT NULL constraint failed: applications.position_id`
    → 7/8 失败，且该异常会破坏 atomic 块、污染 teardown 缓存清理
    （见测试报告 P1-3 污染链）。故这里显式补齐整条外键链。
    """
    import uuid

    from apps.application.models import Application
    from apps.candidate.models import Candidate
    from apps.position.models import Position, PositionState
    from apps.process.models import (
        ProcessStageLink,
        RecruitmentProcess,
        RecruitmentStage,
        StageType,
    )

    process = RecruitmentProcess.objects.create(
        code=f'QA{uuid.uuid4().hex[:6].upper()}', name='QA 流程',
        current_version='V1.0', version_seq=1, is_latest=True, status='ENABLED',
    )
    stage = RecruitmentStage.objects.create(
        code=f'QAS{uuid.uuid4().hex[:6].upper()}', name='QA 阶段',
        stage_type=StageType.SCREEN,
    )
    link = ProcessStageLink.objects.create(
        process=process, stage=stage, order=1, is_required=True,
    )
    position = Position.objects.create(
        code=f'QAP{uuid.uuid4().hex[:6].upper()}', title='QA 测试职位',
        department=department, hiring_manager=super_user, owner=super_user,
        process=process, state=PositionState.DRAFT,
    )
    cands = Candidate.objects.filter(phone=REAL_PHONE)
    cand = cands.first() if cands.exists() else Candidate.objects.create(
        name='QA候选人', phone=REAL_PHONE, email=REAL_EMAIL,
    )
    app = Application.objects.create(
        code=f'QA_APP_{uuid.uuid4().hex[:8].upper()}',
        candidate=cand, position=position, process=process,
        workflow_version=process.current_version,
        current_link=link, current_stage=stage,
    )
    # ⚠️ 必须写 created_by：无数据权限规则时 scope_filter_q 回退 SELF
    # （Q(created_by=user.pk)），不写则列表恒空、脱敏断言根本不执行（假绿）。
    if owner is not None:
        app.created_by = owner
        app.save(update_fields=['created_by'])
    return app


# ============ V2-1：默认配置下必须脱敏（DR-03 核心）============

def test_default_list_phone_is_masked_not_plaintext(plain_user, department, super_user):
    """无任何 ACL 规则时，投递列表 candidate_phone 必须是脱敏形态。

    🔴 反证锚点：把 DEFAULT_SENSITIVE_FIELDS['application'] 改回 [] 本用例必须红。
    """
    _make_application(department, super_user, owner=plain_user)
    status, body = _get(_client_for(plain_user), LIST_URL)

    assert status == 200, f'HTTP {status}: {json.dumps(body, ensure_ascii=False)[:300]}'
    row = _first_row(body)

    got, _key = _field(row, 'candidate_phone')
    assert got is not None, (
        f'列表应输出 candidate_phone 字段，实际字段：{sorted(row.keys())[:20]}'
    )
    assert got != REAL_PHONE, (
        f'🔴 明文泄漏：candidate_phone 返回了完整号码 {got!r}'
    )
    assert got != '', '脱敏不应把字段置空（应保留可辨形态）'
    # 脱敏形态断言：138****8000 —— 不能是"任意非明文"就算过
    assert '*' in got or '***' in got, (
        f'candidate_phone 应呈脱敏形态（含掩码），实际 {got!r}'
    )
    assert got.startswith('138'), f'应保留号段前缀便于识别，实际 {got!r}'
    assert got.endswith('8000'), f'应保留后四位便于识别，实际 {got!r}'


def test_default_list_email_is_masked(plain_user, department, super_user):
    """candidate_email 同属默认清单，默认也必须脱敏（不能只护手机号）。"""
    _make_application(department, super_user, owner=plain_user)
    status, body = _get(_client_for(plain_user), LIST_URL)
    assert status == 200, f'HTTP {status}'

    row = _first_row(body)
    got, _key = _field(row, 'candidate_email')
    assert got is not None, f'列表应输出 candidate_email：{sorted(row.keys())[:20]}'
    assert got != REAL_EMAIL, f'🔴 明文泄漏：candidate_email 返回了完整邮箱 {got!r}'
    assert '***' in got or '*' in got, f'candidate_email 应脱敏，实际 {got!r}'


def test_default_sensitive_fields_application_not_empty():
    """静态护栏：application 的默认脱敏清单不能为空。

    空清单 = 删掉硬编码脱敏后完全裸奔（DR-03 描述的退化态）。
    """
    fields = FieldAclService.DEFAULT_SENSITIVE_FIELDS.get('application')
    assert fields, (
        '🔴 DEFAULT_SENSITIVE_FIELDS["application"] 为空 —— '
        '已删硬编码脱敏却没补清单 = 投递列表手机号/邮箱完全不脱敏'
    )
    assert 'candidate_phone' in fields, '默认清单必须含 candidate_phone'
    assert 'candidate_email' in fields, '默认清单必须含 candidate_email'


# ============ V2-2：超管路径未被误伤 ============

def test_superuser_sees_plaintext(department, super_user):
    """超管不应被脱敏（acl_strict fail-closed 只影响拿不到 context 的场景）。

    注意用 `super_user`（真超管，含 is_superuser + SUPER_ADMIN 角色）而不是
    自建的普通 User —— QA 第一版用普通 User 导致 got=None，是身份搞错。
    """
    assert super_user.is_superuser, 'fixture 应提供真超管'
    _make_application(department, super_user, owner=super_user)
    status, body = _get(_client_for(super_user), LIST_URL)
    assert status == 200, f'HTTP {status}'

    row = _first_row(body)
    got, _key = _field(row, 'candidate_phone')
    assert got == REAL_PHONE, (
        f'超管应看到明文（业务依赖导出/联系），实际 {got!r}'
    )


# ============ V2-3：READ / MASK / NONE 三态============

def _set_rule(role_code, entity, field, permission):
    FieldACL.objects.update_or_create(
        entity=entity, role_code=role_code, field=field,
        defaults={'permission': permission},
    )
    FieldAclService.invalidate_rules_cache(None)


def test_permission_mask_masks(admin, plain_user, department, super_user):
    """permission=MASK → 脱敏。"""
    _make_application(department, super_user, owner=plain_user)
    _set_rule('QA_ACL_ROLE', 'application', 'candidate_phone', 'MASK')

    status, body = _get(_client_for(plain_user), LIST_URL)
    assert status == 200, f'HTTP {status}'
    got, _k = _field(_first_row(body), 'candidate_phone')
    assert got != REAL_PHONE, f'MASK 应脱敏，实际 {got!r}'
    assert '*' in (got or ''), f'MASK 形态应含掩码，实际 {got!r}'


def test_permission_read_shows_plaintext(admin, plain_user, department, super_user):
    """permission=READ → 明文放行（显式放开，不是被mask 挡住）。"""
    _make_application(department, super_user, owner=plain_user)
    _set_rule('QA_ACL_ROLE', 'application', 'candidate_phone', 'READ')

    status, body = _get(_client_for(plain_user), LIST_URL)
    assert status == 200, f'HTTP {status}'
    got, _k = _field(_first_row(body), 'candidate_phone')
    assert got == REAL_PHONE, f'READ 应放行明文，实际 {got!r}'


def test_permission_none_removes_field(admin, plain_user, department, super_user):
    """permission=NONE → 字段被**移除**（不是置空、不是明文）。"""
    _make_application(department, super_user, owner=plain_user)
    _set_rule('QA_ACL_ROLE', 'application', 'candidate_phone', 'NONE')

    status, body = _get(_client_for(plain_user), LIST_URL)
    assert status == 200, f'HTTP {status}'
    row = _first_row(body)
    got, _k = _field(row, 'candidate_phone')
    assert got is None, f'NONE 应移除字段，实际仍存在：{got!r}'


def test_none_is_strictest_takeover(admin, plain_user, department, super_user):
    """NONE 与 MASK 同时命中时取最严（NONE）—— strictestPermission 语义。"""
    _make_application(department, super_user, owner=plain_user)
    FieldACL.objects.update_or_create(
        entity='application', role_code='QA_ACL_ROLE', field='candidate_phone',
        defaults={'permission': 'MASK'},
    )
    FieldACL.objects.update_or_create(
        entity='application', role_code='QA_ACL_SUPER', field='candidate_phone',
        defaults={'permission': 'NONE'},
    )
    # 让该用户同时拥有两个角色
    RoleV2.objects.get_or_create(
        system_code='recruit', role_code='QA_ACL_SUPER',
        defaults={'role_name': 'sup', 'status': 1},
    )
    UserRoleV2.objects.get_or_create(
        user_id=plain_user.pk, role_code='QA_ACL_SUPER', system_code='recruit',
    )
    FieldAclService.invalidate_rules_cache(None)

    status, body = _get(_client_for(plain_user), LIST_URL)
    assert status == 200, f'HTTP {status}'
    row = _first_row(body)
    got, _k = _field(row, 'candidate_phone')
    assert got is None, f'两角色 MASK+NONE 应取最严 NONE，实际 {got!r}'
