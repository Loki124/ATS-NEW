"""字段 ACL 写接口 + 接入面回归（2026-10-14 P0-2 / P0-4，设计文档 T04）。

覆盖两批必须**同批交付**的内容（拆开即为事故，见 §5.5.1 C3/C4 约束）：

- C3 写接口：`PUT/DELETE /field-acl/rules` 路由可用、缓存立即失效、
  `matrix` 双字段、批量 dryRun 不落库、非法输入 400。
- C4 接入面：`application` 硬编码脱敏删除后**默认仍脱敏**（DR-03 强制）、
  `NONE` 删除字段、审计 `masked_fields` 非空、`offer.salary` 脱敏生效。

⚠️ DR-03 的防假绿要求：`test_application_list_phone_masked_by_default`
必须在"补 DEFAULT_SENSITIVE_FIELDS 之后、删硬编码之前"先失败一次（红→绿），
恒真断言视为无效证据。
"""
import pytest

from apps.application.serializers import ApplicationListSerializer
from apps.candidate.models import Candidate
from apps.core.models import User
from apps.core.models_permission_v2 import RoleV2, UserRoleV2
from apps.field_acl.models import FieldACL
from apps.field_acl.services import FieldAclService
from apps.offer.serializers import OfferListSerializer

pytestmark = pytest.mark.django_db

LIST = '/api/v1/field-acl/'
# DR-04a：默认路由带尾斜杠，缺斜杠会被APPEND_SLASH 重定向（301）→ 测试拿到空响应
RULES = '/api/v1/field-acl/rules/'
BATCH = '/api/v1/field-acl/rules/batch/'


@pytest.fixture
def role(db):
    return RoleV2.objects.create(
        system_code='recruit', role_code='ACL_TEST_ROLE', role_name='ACL 测试角色', status=1,
    )


@pytest.fixture
def hr_user(db, department, role):
    """带普通角色（非超管）的用户 —— ACL 脱敏的真正验证对象。"""
    user = User.objects.create(
        username='acl_hr', is_active=True, is_superuser=False, department=department,
    )
    UserRoleV2.objects.create(
        user_id=user.pk, role_code=role.role_code, system_code='recruit',
    )
    return user


@pytest.fixture
def client_for(db, hr_user):
    """以 hr_user 登录的 APIClient（用于验证脱敏，而非超管旁路）。"""
    from rest_framework.test import APIClient
    c = APIClient()
    c.force_authenticate(user=hr_user)
    # 记下身份：_req() 需要按"当前用户"构造 request，否则会把超管当普通用户
    # （脱敏断言假绿）或反之（超管断言被脱敏而红）。
    c._acl_user = hr_user
    return c


# ==================== C3：写接口路由 ====================

def test_put_rule_creates_then_updates(auth_client, role):
    """PUT /field-acl/rules：首次 201 建、命中同三元组再 PUT 返 200 且不重复建行。"""
    payload = {'entity': 'candidate', 'field': 'phone', 'role_code': role.role_code, 'permission': 'MASK'}

    resp = auth_client.put(RULES, payload, format='json')
    assert resp.status_code == 201, resp.data
    assert resp.data['data']['permission'] == 'MASK'

    resp2 = auth_client.put(RULES, {**payload, 'permission': 'NONE'}, format='json')
    assert resp2.status_code == 200, resp2.data
    assert resp2.data['data']['permission'] == 'NONE'
    # 幂等：同一三元组只应有一行
    assert FieldACL.objects.filter(
        entity='candidate', field='phone', role_code=role.role_code,
    ).count() == 1


def test_put_rule_rejects_unknown_role(auth_client, db):
    """role_code 不存在 → 400 且**不落库**（失败必须响亮，禁静默写孤儿规则）。"""
    resp = auth_client.put(
        RULES,
        {'entity': 'candidate', 'field': 'phone', 'role_code': 'NO_SUCH_ROLE_X', 'permission': 'MASK'},
        format='json',
    )
    assert resp.status_code == 400, resp.data
    assert not FieldACL.objects.filter(role_code='NO_SUCH_ROLE_X').exists()


def test_put_rule_rejects_bad_permission(auth_client, role):
    """三态之外的词汇→ 400（禁自建映射表产生后端不认的值）。"""
    resp = auth_client.put(
        RULES,
        {'entity': 'candidate', 'field': 'phone', 'role_code': role.role_code, 'permission': 'HIDE'},
        format='json',
    )
    assert resp.status_code == 400, resp.data
    assert not FieldACL.objects.exists()


def test_delete_rule_is_idempotent(auth_client, role):
    """DELETE：删存在的返 deleted=1；删不存在的返 200 + deleted=0（前端撤销可无脑重放）。"""
    FieldACL.objects.create(
        entity='candidate', field='phone', role_code=role.role_code, permission='MASK',
    )
    body = {'entity': 'candidate', 'field': 'phone', 'role_code': role.role_code}

    resp = auth_client.delete(RULES, body, format='json')
    assert resp.status_code == 200, resp.data
    assert resp.data['data']['deleted'] == 1

    resp2 = auth_client.delete(RULES, body, format='json')
    assert resp2.status_code == 200
    assert resp2.data['data']['deleted'] == 0


def test_delete_rule_missing_params_returns_400(auth_client):
    """DELETE 缺三元组 → 400 且说明缺了哪些（错误文案要能定位问题）。"""
    resp = auth_client.delete(RULES, {'entity': 'candidate'}, format='json')
    assert resp.status_code == 400
    assert 'field' in resp.data['message']
    assert 'role_code' in resp.data['message']


def test_rules_requires_super_admin(client_for, role):
    """非超管 → 403（P0-2 的 ACL 配置是超管权限，不能被普通 HR 改）。"""
    resp = client_for.put(
        RULES,
        {'entity': 'candidate', 'field': 'phone', 'role_code': role.role_code, 'permission': 'NONE'},
        format='json',
    )
    assert resp.status_code == 403, resp.status_code


# ==================== C3：缓存失效（RK-7 / DR-04c） ====================

def test_write_invalidates_cache_immediately(auth_client, client_for, role):
    """改完规则**立刻**生效 —— 不等 60s TTL。

    这是 RK-7 的核心：不调invalidate 的话，"保存成功但最长 60s 内不生效"，
    权限收紧不生效比不配更危险（管理员以为收紧了）。
    """
    # 先让普通角色看到明文（无规则 → candidate 不在 application 清单时走 READ）
    FieldAclService.invalidate_rules_cache('application')
    FieldACL.objects.create(
        entity='application', field='candidate_phone', role_code=role.role_code, permission='NONE',
    )
    # 缓存此刻应已被 post_save 信号清掉；直接读一次把规则灌进缓存
    assert FieldAclService.get_rules_map('application')

    # 通过写接口改回 MASK
    resp = auth_client.put(
        RULES,
        {'entity': 'application', 'field': 'candidate_phone',
         'role_code': role.role_code, 'permission': 'MASK'},
        format='json',
    )
    assert resp.status_code in (200, 201), resp.data

    # 立刻读缓存必须是新值，不能是 60s 前的旧值
    rules_map = FieldAclService.get_rules_map('application')
    assert rules_map[('candidate_phone', role.role_code)] == 'MASK'


def test_invalidate_all_covers_entities_not_in_default_dict(auth_client, role):
    """invalidate_rules_cache(None) 必须覆盖**不在默认清单里**的 entity。

    DR-04c/RK-7 的坑：原实现 entity=None 时只清 DEFAULT_SENSITIVE_FIELDS 的 key，
    批量改完其它实体后缓存不清 → 假生效。
    """
    FieldACL.objects.create(
        entity='some_new_entity', field='x', role_code=role.role_code, permission='MASK',
    )
    # 把该实体的规则灌进缓存
    assert FieldAclService.get_rules_map('some_new_entity')
    FieldACL.objects.filter(entity='some_new_entity').delete()

    # 全量失效（None 分支）—— 必须能清掉不在默认清单里的实体
    FieldAclService.invalidate_rules_cache(None)
    assert FieldAclService.get_rules_map('some_new_entity') == {}, '全量失效漏掉了非默认实体'


# ==================== C3：matrix 双字段 ====================

def test_matrix_returns_permission_and_action(auth_client, role):
    """matrix 同时返回 permission（代码枚举）与 action（旧词汇），供过渡期双读。"""
    FieldACL.objects.create(
        entity='candidate', field='phone', role_code=role.role_code, permission='MASK',
    )
    resp = auth_client.get('/api/v1/field-acl/matrix/')
    assert resp.status_code == 200
    cell = resp.data['data']['candidate']['phone'][role.role_code]
    assert cell['permission'] == 'MASK'
    assert cell['action'] == 'MASK', '过渡期 action 字段必须保留（旧前端靠它渲染）'


def test_catalog_lists_configurable_entities(auth_client):
    """catalog 下发可配实体与字段（前端矩阵的行/列定义由后端给，不在前端硬编码）。"""
    resp = auth_client.get('/api/v1/field-acl/catalog/')
    assert resp.status_code == 200
    data = resp.data['data']
    assert 'application' in data
    assert 'candidate_phone' in data['application']['fields']
    # 默认脱敏清单必须与 services 的真源一致（前端要据此打「默认脱敏」标记）
    assert set(data['application']['defaultMasked']) == set(
        FieldAclService.DEFAULT_SENSITIVE_FIELDS['application']
    )


# ==================== C3：批量 dryRun ====================

def test_batch_dryrun_does_not_persist(auth_client, role):
    """dryRun=true 只算影响不落库（批量破坏性操作前的"影响范围"数据源）。"""
    resp = auth_client.post(
        BATCH,
        {'mode': 'by_role', 'roleCode': role.role_code,
         'items': [{'field': 'candidate_phone', 'permission': 'NONE'}], 'dryRun': True},
        format='json',
    )
    assert resp.status_code == 200, resp.data
    assert resp.data['data']['dryRun'] is True
    assert resp.data['data']['willCreate'] >= 1
    assert FieldACL.objects.count() == 0, 'dryRun 不应落库'


def test_batch_apply_persists_and_rejects_bad_input(auth_client, role):
    """dryRun=false 落库；非法 mode / 空 items → 400 且不落库。"""
    resp = auth_client.post(
        BATCH,
        {'mode': 'by_role', 'roleCode': role.role_code,
         'items': [{'field': 'candidate_phone', 'permission': 'NONE'}], 'dryRun': False},
        format='json',
    )
    assert resp.status_code == 200, resp.data
    assert FieldACL.objects.filter(
        entity='application', field='candidate_phone', role_code=role.role_code, permission='NONE',
    ).exists()

    bad = auth_client.post(
        BATCH, {'mode': 'by_bogus', 'items': [{'field': 'x', 'permission': 'MASK'}]},
        format='json',
    )
    assert bad.status_code == 400

    empty = auth_client.post(
        BATCH, {'mode': 'by_role', 'roleCode': role.role_code, 'items': []},
        format='json',
    )
    assert empty.status_code == 400


# ==================== C4：接入面（DR-03 强制） ====================

def test_application_list_phone_masked_by_default(client_for, app_scenario):
    """🔴 DR-03 核心：默认配置下（**无任何 ACL 规则**）投递手机号仍必须脱敏。

    这条用例是"删硬编码脱敏"的安全前提。它必须有鉴别力 —— 若只删
    ApplicationListSerializer.get_candidate_phone 而没补
    DEFAULT_SENSITIVE_FIELDS['application']，本用例会红（明文泄漏）。
    """
    from apps.application.serializers import ApplicationListSerializer
    data = ApplicationListSerializer(
        app_scenario['app'], context={'request': _req(client_for)},
    ).data

    assert 'candidate_phone' in data, '字段被整体丢弃，ACL 契约异常'
    assert '13800001234' != data['candidate_phone'], '明文泄漏！默认脱敏未生效'
    assert '*' in data['candidate_phone']


def test_application_list_phone_readable_for_super_admin(auth_client, app_scenario):
    """超管仍看明文（apply_acl 的bypass 分支不能被破坏）。"""
    from apps.application.serializers import ApplicationListSerializer
    # 超管走 apply_acl 的 bypass 分支；必须显式传超管身份，不能靠 client 反推
    data = ApplicationListSerializer(
        app_scenario['app'], context={'request': _req(auth_client, user=app_scenario['user'])},
    ).data
    assert data['candidate_phone'] == app_scenario['candidate'].phone


def test_application_acl_none_removes_field(client_for, role, app_scenario):
    """ACL 配NONE → 响应中**不含** candidate_phone 键（NONE 是删字段，不是置空）。"""
    FieldACL.objects.create(
        entity='application', field='candidate_phone',
        role_code=role.role_code, permission='NONE',
    )
    FieldAclService.invalidate_rules_cache('application')

    from apps.application.serializers import ApplicationListSerializer
    data = ApplicationListSerializer(
        app_scenario['app'], context={'request': _req(client_for)},
    ).data
    assert 'candidate_phone' not in data, 'NONE 未删除字段'


def test_acl_access_log_records_masked_fields(client_for, app_scenario):
    """审计 masked_fields 必须非空（PRD P0-4 验收③：1607 条全空的历史问题不再复现）。"""
    from apps.application.serializers import ApplicationListSerializer
    from apps.field_acl.models import FieldAclAccessLog
    ApplicationListSerializer(
        app_scenario['app'], context={'request': _req(client_for)},
    ).data

    log = FieldAclAccessLog.objects.filter(entity='application').latest('created_at')
    assert log.masked_fields, 'masked_fields 为空 —— 审计埋点失效'


def test_offer_salary_masked_by_default(client_for, app_scenario):
    """offer 的 salary 接 mixin 后按默认脱敏（DEFAULT_SENSITIVE_FIELDS['offer']已存在）。"""
    offer = _offer_with_salary(app_scenario, 30000)
    data = OfferListSerializer(offer, context={'request': _req(client_for)}).data
    assert '*' in str(data['salary']), f'salary 未脱敏：{data["salary"]}'


def test_application_acl_read_shows_plaintext(client_for, role, app_scenario):
    """ACL 配 READ → 明文放行。

    这是 P0-2「可配」的正向证明：默认脱敏只是兜底，管理员**显式**配 READ 后
    该角色确实能看到明文（业务侧已确认接受此口径，见设计文档 DR-03）。
    没有这条就可能出现"配 READ 也没用"的静默失效。
    """
    FieldACL.objects.create(
        entity='application', field='candidate_phone',
        role_code=role.role_code, permission='READ',
    )
    FieldAclService.invalidate_rules_cache('application')

    from apps.application.serializers import ApplicationListSerializer
    data = ApplicationListSerializer(
        app_scenario['app'], context={'request': _req(client_for)},
    ).data
    assert data['candidate_phone'] == app_scenario['candidate'].phone, (
        f"显式配 READ 后仍被脱敏：{data['candidate_phone']}"
    )


def test_application_acl_none_wins_over_mask_across_roles(client_for, db, app_scenario):
    """多角色命中时从严取值：MASK + NONE 并存 → 最终 NONE（字段被删）。

    对齐 FieldAclService._get_field_permission 的 NONE > MASK > READ 与前端
    PERMISSION_SEVERITY。若这条失效，同一用户换个角色组合就能看到本该隐藏的字段。
    """
    from apps.application.serializers import ApplicationListSerializer
    from apps.core.models_permission_v2 import UserRoleV2

    role_a = RoleV2.objects.create(
        system_code='recruit', role_code='ACL_MASK_ROLE', role_name='MASK 角色', status=1,
    )
    role_b = RoleV2.objects.create(
        system_code='recruit', role_code='ACL_NONE_ROLE', role_name='NONE 角色', status=1,
    )
    FieldACL.objects.create(
        entity='application', field='candidate_phone',
        role_code=role_a.role_code, permission='MASK',
    )
    FieldACL.objects.create(
        entity='application', field='candidate_phone',
        role_code=role_b.role_code, permission='NONE',
    )
    # 该用户同时持有两个角色 → 两个规则同时命中
    UserRoleV2.objects.create(
        user_id=client_for._acl_user.pk, role_code=role_a.role_code, system_code='recruit',
    )
    UserRoleV2.objects.create(
        user_id=client_for._acl_user.pk, role_code=role_b.role_code, system_code='recruit',
    )
    FieldAclService.invalidate_rules_cache('application')

    data = ApplicationListSerializer(
        app_scenario['app'], context={'request': _req(client_for)},
    ).data
    assert 'candidate_phone' not in data, 'NONE 未从严生效（字段应被删除）'


def test_serializer_acl_entities_are_declared():
    """静态护栏：接了 mixin 的序列化器必须显式声明 acl_entity。

    否则 acl_entity='' → mixin 直接放行，接了等于没接（静默失效，最难查）。
    """
    for ser in (ApplicationListSerializer, OfferListSerializer):
        assert ser.acl_entity, f'{ser.__name__} 未声明 acl_entity'


def test_default_sensitive_fields_cover_all_configured_entities():
    """🔴 DR-03 同批次约束的静态自检：catalog 里每个 entity 都必须有默认脱敏清单。

    「catalog 里有实体但 DEFAULT_SENSITIVE_FIELDS 里是空列表」= 该实体
    在"无规则时完全裸奔"，正是 P0-4 要消灭的病灶形态。
    """
    from apps.field_acl.views import ENTITY_CATALOG
    for entity in ENTITY_CATALOG:
        assert FieldAclService.DEFAULT_SENSITIVE_FIELDS.get(entity), (
            f'{entity} 已在 catalog 中可配，但默认脱敏清单为空 —— 接 mixin 等于裸奔'
        )


# ============ helpers ============

@pytest.fixture
def app_scenario(db, department, super_user):
    """最小可序列化场景：候选人 + 职位 + 流程 + 投递。

    直接复用 apps/application/tests/test_envelope.py 里已验证的建法——
    Application.state 是 FSMField(protected=True)，只能走 defaults 不能赋值。
    """
    import uuid

    from apps.application.models import Application
    from apps.position.models import Position, PositionState
    from apps.process.models import (
        ProcessStageLink,
        RecruitmentProcess,
        RecruitmentStage,
        StageType,
    )

    process = RecruitmentProcess.objects.create(
        code=f'ACL{uuid.uuid4().hex[:6].upper()}', name='ACL 流程',
        current_version='V1.0', version_seq=1, is_latest=True, status='ENABLED',
    )
    stage = RecruitmentStage.objects.create(
        code=f'ACLS{uuid.uuid4().hex[:6].upper()}', name='ACL 阶段', stage_type=StageType.SCREEN,
    )
    link = ProcessStageLink.objects.create(process=process, stage=stage, order=1, is_required=True)
    position = Position.objects.create(
        code=f'ACLP{uuid.uuid4().hex[:6].upper()}', title='ACL 测试职位',
        department=department, hiring_manager=super_user, owner=super_user,
        process=process, state=PositionState.DRAFT,
    )
    candidate = Candidate.objects.create(name='ACL 候选人', phone='13800001234', email='acl@x.com')
    app = Application.objects.create(
        code=f'ACLA{uuid.uuid4().hex[:8].upper()}',
        candidate=candidate, position=position, process=process,
        workflow_version=process.current_version,
        current_link=link, current_stage=stage,
    )
    return {'app': app, 'candidate': candidate, 'position': position, 'user': super_user}


class _FakeReq:
    """最小 request 替身：mixin 只需要 user / path / META / _field_acl_audited。"""

    path = '/api/v1/applications/'
    META = {'REMOTE_ADDR': '127.0.0.1'}

    def __init__(self, user=None):
        self.user = user
        self._field_acl_audited = None


def _req(client, user=None):
    """构造与指定用户绑定的 request。

    mixin 的 to_representation 从 context['request'] 取 user 交给 apply_acl，
    非超管才走脱敏分支 —— 若这里给错用户（超管），所有脱敏断言都会假绿。
    """
    if user is not None:
        return _FakeReq(user)
    tagged = getattr(client, '_acl_user', None)
    if tagged is not None:
        return _FakeReq(tagged)
    handler = getattr(client, 'handler', None)
    real = getattr(handler, '_request', None)
    if real is not None and getattr(real, 'user', None) is not None:
        return real
    return _FakeReq()


def _offer_with_salary(app_scenario: dict, salary: int = 30000):
    """造一条带薪资的 Offer（复用 app_scenario 的职位/候选人/投递）。"""
    from apps.offer.models import Offer
    return Offer.objects.create(
        code='ACL-OFFER-1', application=app_scenario['app'],
        position=app_scenario['position'], candidate=app_scenario['candidate'],
        salary=salary, salary_currency='CNY',
    )