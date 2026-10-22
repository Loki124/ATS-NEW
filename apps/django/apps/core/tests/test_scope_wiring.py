"""M02 行级接入守卫测试 (2026-10-12).

背景: 行级数据范围的历史入口曾有三条直调/复刻路径 (scope_filter_q 直调 /
ScopeQuerysetMixin 独立复刻 / role_entity_scope_q 直调), 2026-10-08 又新增
entity_scope.py 统一非 ViewSet 入口。M02 将全部入口收敛到两条公开 API:
  - ViewSet: ScopeQuerysetMixin.scope_queryset (委托 scope_filter_q 全语义)
  - 非 ViewSet (导出/批量): entity_scope_q / scoped_queryset (同样委托)

本文件是三道防线:
  1. 完整性: field_map.MODULE_DIMENSION_FIELDS 的每个 entity 都必须登记在册的
     行级接入路径 —— 新模块加进 field_map 却忘记接线, 本文件第一个测试即失败;
  2. 不漂移: ENTITY_SCOPE 的 (scope_field, creator_field) 与各 ViewSet 类属性
     声明逐一一致 (entity_scope.py docstring 引用、但从未创建的
     test_entity_scope.py 由此文件承接);
  3. 口径一致: ScopeQuerysetMixin 与 scope_filter_q 对同一用户/queryset 产出
     等价 SQL —— 锁定 G2 修复 (管理单元 USER 成员可见性 / data_range AND /
     per-app 范围优先 / SELF 兜底字段), 防止未来再次分叉。
"""
import pytest
from django.contrib.auth import get_user_model

from apps.data_permission.field_map import MODULE_DIMENSION_FIELDS

# ---------------------------------------------------------------------------
# 1. 接入路径登记表
# ---------------------------------------------------------------------------
# entity (field_map 键) -> ViewSet 类 (声明 data_perm_entity 的那个).
# 新增模块登记进 MODULE_DIMENSION_FIELDS 时必须同步本表, 否则
# test_all_field_map_entities_wired 失败 —— 漏接成本 = 改一行测试。
ENTITY_VIEWSETS = {
    'candidate': 'apps.candidate.views.CandidateViewSet',
    'demand': 'apps.demand.views.DemandViewSet',
    'position': 'apps.position.views.PositionViewSet',
    'process': 'apps.process.views.RecruitmentProcessViewSet',
    'talent': 'apps.talent_pool.views.TalentPoolEntryViewSet',
    # 2026-10-21 卡 B1: 校招轮岗三实体随 S5-10/S5-21 接入 field_map 后补登记。
    #   三者的 scope 口径与 core/entity_scope.py 的 ENTITY_SCOPE 完全一致
    #   (campus_arrangement=current_dept / campus_class=hrbp__department /
    #    campus_resource=bu, creator 均为 created_by), 已同时登记进
    #   ENTITY_SCOPE_VIEWSETS 以锁死「改一处忘另一处」的口径漂移。
    'campus_arrangement': 'apps.campus_rotation.views.RotationArrangementViewSet',
    'campus_class': 'apps.campus_rotation.views.ClassRoomViewSet',
    'campus_resource': 'apps.campus_rotation.views.RotationResourceViewSet',
    'campus_person': 'apps.campus_control.views.PersonViewSet',
}

# ENTITY_SCOPE 键 -> ViewSet 类 (导出/批量入口与列表页口径一致性断言用).
ENTITY_SCOPE_VIEWSETS = {
    'candidate': 'apps.candidate.views.CandidateViewSet',
    'demand': 'apps.demand.views.DemandViewSet',
    'position': 'apps.position.views.PositionViewSet',
    'offer': 'apps.offer.views.OfferViewSet',
    'interview': 'apps.interview.views.InterviewViewSet',
    'onboarding': 'apps.onboarding.views.OnboardingViewSet',
    'invitation': 'apps.invitation.views.InvitationViewSet',
    'talent_pool': 'apps.talent_pool.views.TalentPoolEntryViewSet',
    'referral': 'apps.referral.views.ReferralViewSet',
    'application': 'apps.application.views.ApplicationViewSet',
    # 2026-10-21 卡 B1: 同上, 校招轮岗三实体。
    'campus_arrangement': 'apps.campus_rotation.views.RotationArrangementViewSet',
    'campus_class': 'apps.campus_rotation.views.ClassRoomViewSet',
    'campus_resource': 'apps.campus_rotation.views.RotationResourceViewSet',
    'campus_person': 'apps.campus_control.views.PersonViewSet',
}


def _import(path: str):
    module_path, cls = path.rsplit('.', 1)
    import importlib
    return getattr(importlib.import_module(module_path), cls)


@pytest.mark.v2_permission
def test_all_field_map_entities_wired():
    """完整性: field_map 每个 entity 都有登记在册的 ViewSet 接入路径.

    新模块加进 MODULE_DIMENSION_FIELDS 但忘记接线 -> 本测试失败并提示补登记。
    """
    missing = set(MODULE_DIMENSION_FIELDS) - set(ENTITY_VIEWSETS)
    assert not missing, (
        f'以下实体登记进了 field_map 但未登记行级接入路径: {sorted(missing)}。'
        '请为其 ViewSet 声明 data_perm_entity 并补进 ENTITY_VIEWSETS 登记表'
        ' (apps/core/tests/test_scope_wiring.py)。'
    )


@pytest.mark.v2_permission
def test_wired_viewsets_declare_entity_attr():
    """登记表中的 ViewSet 必须真实声明 data_perm_entity = 对应 entity."""
    for entity, path in ENTITY_VIEWSETS.items():
        view_cls = _import(path)
        declared = getattr(view_cls, 'data_perm_entity', '')
        assert declared == entity, (
            f'{path} 应声明 data_perm_entity={entity!r}, 实际 {declared!r}'
        )


@pytest.mark.v2_permission
def test_entity_scope_matches_viewset_declarations():
    """不漂移: ENTITY_SCOPE 的 (scope_field, creator_field) 与 ViewSet 声明一致.

    导出走 ENTITY_SCOPE、列表走 ViewSet 类属性, 两边改一处忘另一处即口径漂移。
    """
    from apps.core.entity_scope import ENTITY_SCOPE

    for key, path in ENTITY_SCOPE_VIEWSETS.items():
        cfg = ENTITY_SCOPE[key]
        view_cls = _import(path)
        assert view_cls.scope_field == cfg['scope_field'], (
            f'{path}.scope_field={view_cls.scope_field!r} 与 '
            f'ENTITY_SCOPE[{key!r}].scope_field={cfg["scope_field"]!r} 漂移'
        )
        assert view_cls.scope_creator_field == cfg['creator_field'], (
            f'{path}.scope_creator_field={view_cls.scope_creator_field!r} 与 '
            f'ENTITY_SCOPE[{key!r}].creator_field={cfg["creator_field"]!r} 漂移'
        )


# ---------------------------------------------------------------------------
# 2. 口径一致: mixin 委托 scope_filter_q 全语义 (G2 回归)
# ---------------------------------------------------------------------------

class _StubView:
    """最小 request stub: mixin 只依赖 request.user / request.recruit_type."""

    def __init__(self, user, recruit_type='social'):
        self.request = type('Req', (), {'user': user, 'recruit_type': recruit_type})()


def _make_scope_user(username):
    User = get_user_model()
    return User.objects.create_user(username=username, password='x')


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_mixin_equivalent_to_scope_filter_q():
    """同一用户/queryset 下, mixin 与 scope_filter_q 编译出等价 SQL."""
    from apps.candidate.models import Candidate
    from apps.candidate.views import CandidateViewSet
    from apps.core.scope_resolver import scope_filter_q

    user = _make_scope_user('sw_equiv')
    view = CandidateViewSet()
    view.request = type('Req', (), {'user': user, 'recruit_type': 'social'})()

    qs_mixin = view.scope_queryset(Candidate.objects.all())
    qs_direct = Candidate.objects.filter(scope_filter_q(
        user,
        app_code='recruit',
        scope_field=CandidateViewSet.scope_field,
        creator_field=CandidateViewSet.scope_creator_field,
        recruit_type='social',
        entity='candidate',
    ))
    assert str(qs_mixin.query) == str(qs_direct.query)


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_mixin_sees_unit_member_users_data():
    """G2 回归: 管理单元 USER 成员创建的候选人, 经 mixin 与直调同样可见.

    委托前 mixin 只用 unit_ids_to_dept_ids (部门集合), 成员 USER 的
    created_by__in OR 分支缺失 —— 列表页看不到、导出看得到的"隐形数据"。
    """
    from apps.candidate.models import Candidate
    from apps.candidate.views import CandidateViewSet
    from apps.core.models_permission_v2 import (
        ManagementUnit,
        ManagementUnitMember,
        UserRoleV2,
    )
    from apps.core.role_v2_query import is_super_admin
    from apps.core.scope_resolver import scope_filter_q

    user = _make_scope_user('sw_lead')
    member = _make_scope_user('sw_member')
    assert not is_super_admin(user)

    unit = ManagementUnit.objects.create(
        unit_name='SW-成员单元', system_code='recruit', unit_type='org',
        org_scope=['D1'], status=1,
    )
    UserRoleV2.objects.create(
        user_id=user.pk, role_code='R_SW', system_code='recruit',
        app_data_scopes={'recruit': [unit.id]}, granted_by_id=1,
    )
    ManagementUnitMember.objects.create(
        unit_id=unit.id, member_type='USER', user_id=member.pk, status=1,
    )
    Candidate.objects.create(name='成员建的', created_by=member)
    Candidate.objects.create(name='别人建的', created_by=_make_scope_user('sw_other'))

    view = CandidateViewSet()
    view.request = type('Req', (), {'user': user, 'recruit_type': 'social'})()
    names = set(view.scope_queryset(Candidate.objects.all()).values_list('name', flat=True))
    assert names == {'成员建的'}, names

    # 与唯一真相源直调结果一致
    direct = Candidate.objects.filter(scope_filter_q(
        user, app_code='recruit',
        scope_field='referrer__department', creator_field='created_by',
        entity='candidate',
    ))
    assert set(direct.values_list('name', flat=True)) == {'成员建的'}


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_process_keeps_custom_only_semantics():
    """路径③收敛不改变 process 语义: 无 CUSTOM 配置 -> 全量; 有配置 -> 收窄.

    process 无部门字段可依, apply_default_scope=False 显式保留原语义,
    防止收敛时把可见性从全量静默收窄为 SELF。
    """
    from apps.core.models_permission_v2 import UserRoleV2
    from apps.data_permission.models import DataPermissionRule
    from apps.process.models import RecruitmentProcess
    from apps.process.views import RecruitmentProcessViewSet

    user = _make_scope_user('sw_proc')
    UserRoleV2.objects.create(
        user_id=user.pk, role_code='R_PROC', system_code='recruit',
        granted_by_id=1,
    )
    other = _make_scope_user('sw_proc_other')
    RecruitmentProcess.objects.create(code='SW001', name='流程甲', created_by=user)
    RecruitmentProcess.objects.create(code='SW002', name='流程乙', created_by=other)

    view = RecruitmentProcessViewSet()
    view.request = type('Req', (), {'user': user, 'recruit_type': 'social'})()

    # 无 CUSTOM 规则 -> 全量可见 (原语义)
    assert view.scope_queryset(RecruitmentProcess.objects.all()).count() == 2

    # 配 CUSTOM 规则 (creator 包含当前用户) -> 仅自己的
    DataPermissionRule.objects.create(
        dimension_type='ROLE', dimension_value='R_PROC',
        level='ROW', entity='process', scope_type='CUSTOM',
        scope_payload={'expr': '', 'groups': [{'expr': '', 'conditions': [
            {'dimension': 'creator', 'operator': 'in',
             'values': [{'id': user.pk, 'label': '我'}]},
        ]}]},
        status=1,
    )
    codes = set(
        view.scope_queryset(RecruitmentProcess.objects.all())
        .values_list('code', flat=True)
    )
    assert codes == {'SW001'}, codes


# ---------------------------------------------------------------------------
# 3. clear_column_cache 实体集合派生 (M02 顺带修复)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@pytest.mark.v2_permission
def test_clear_column_cache_derives_entity_set():
    """clear_column_cache() 不得硬编码实体集合; 新增实体不漏清."""
    from django.core.cache import cache

    from apps.data_permission.enforcement import (
        _column_rules_for_entity,
        clear_column_cache,
    )
    from apps.data_permission.models import DataPermissionRule

    # 造一个不在原硬编码三元组里的实体, 证明派生集合覆盖它
    DataPermissionRule.objects.create(
        dimension_type='ROLE', dimension_value='R_CACHE',
        level='COLUMN', entity='onboarding', field='salary',
        permission='MASK', status=1,
    )
    # 预热缓存再清
    _column_rules_for_entity('onboarding')
    assert cache.get('data_perm:col:onboarding') is not None

    clear_column_cache()
    assert cache.get('data_perm:col:onboarding') is None, (
        'clear_column_cache() 漏清了库中存在的实体 —— 硬编码实体集合复发'
    )
