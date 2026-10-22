"""穿透测试：动态策略「受限功能」候选区（governedResources）按 1:N 模块映射归组。

背景（2026-10-20；application:advance 于 0048 归位 candidate）：
- 资源码第 2 段（module）与「策略模块」分组口径不同。兵哥清单把「安排面试」
  (recruit:interview:schedule, module=interview) 与「放入人才库」
  (recruit:talent_pool:create, module=talent_pool) 归在「候选人管理」(策略模块 candidate) 下，
  但它们不属于 `candidate` 资源 module；「推进流程」(recruit:candidate:application:advance)
  原 module=application，0048 已归位 candidate 直接入候选区（'application' 桥接 key 暂留兼容）。
- 后端 _governed_resources() 必须走**独立 1:N 常量** STRATEGY_MODULE_RESOURCE_MODULES
  (candidate -> {candidate, interview, application, talent_pool, invitation})，而不能复用
  role_scope_api 的 1:1 DATA_PERM_MODULE_RESOURCE_MODULES（candidate -> {candidate}）—— 否则
  这些跨 module 资源进不了 candidate 候选区，勾选后也按模块切分不出来。
- 本测试直接调用 _governed_resources() 真实代码路径，断言 3 条跨 module 资源确实
  出现在 candidate 候选区，从根上锁死「常量未切换」这类静默失效。
"""
import pytest

from apps.core.management.commands.seed_v2_init import STRATEGY_GOVERNED_CODES
from apps.core.models_permission_v2 import PermissionResource
from apps.core.views_dynamic_strategy import DynamicStrategyViewSet


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_governed_resources_groups_cross_module_codes_under_candidate():
    """candidate 候选区必须含 interview / application / talent_pool 三条跨 module 资源。

    这三条资源真实 module 不是 candidate，但 STRATEGY_MODULE_RESOURCE_MODULES 把
    candidate 映射到 {candidate, interview, application}（talent_pool:create 走
    candidate 批是因为兵哥清单把「放入人才库」归在候选人管理）。
    """
    for code in STRATEGY_GOVERNED_CODES:
        # 2026-10-21 卡 B5：测试环境会补齐 permission_resources（真源 = seed_v2_init.RESOURCES），
        # 其中已含 recruit:candidate:list / :edit / :delete / :menu:view 等码 → 裸 create 撞
        # permission_resources.resource_code 唯一约束。改 update_or_create：语义仍是
        # 「把这一行置成本用例要断言的状态」，且不依赖库里此前有没有这行。
        PermissionResource.objects.update_or_create(
            resource_code=code,
            defaults={
                'system_code': 'recruit',
                'resource_name': code,
                'resource_type': 'BUTTON',
                'module': code.split(':')[1],  # 资源码第 2 段 == 真实 module（规范 R2）
                'status': 1,
                'strategy_governed': True,
            },
        )

    out = DynamicStrategyViewSet._governed_resources()

    candidate_codes = {r['resourceCode'] for r in out['candidate']}
    # 第一批 4 条（candidate 真实 module）
    assert 'recruit:candidate:list' in candidate_codes
    assert 'recruit:candidate:edit' in candidate_codes
    assert 'recruit:candidate:offer:create' in candidate_codes
    assert 'recruit:candidate:offer:approve' in candidate_codes
    # 第二批 3 条（跨 module，靠 1:N 映射归入 candidate）
    assert 'recruit:interview:schedule' in candidate_codes
    assert 'recruit:candidate:application:advance' in candidate_codes
    assert 'recruit:talent_pool:create' in candidate_codes
    # 第三批（S8-01，2026-10-20）11 条：
    #   - 7 条 module=candidate 直接入候选区（assign/recommend/eliminate/notify + bg_check 三条）
    #   - interview:edit/delete 靠 interview 映射、invitation:edit/reject 靠 invitation
    #     映射（D7 新增）归入 candidate —— 兵哥清单把它们归在候选人管理策略卡下
    for code in (
        'recruit:candidate:assign', 'recruit:candidate:recommend',
        'recruit:candidate:eliminate', 'recruit:candidate:notify',
        'recruit:candidate:bg_check:start', 'recruit:candidate:bg_check:import',
        'recruit:candidate:bg_check:cancel',
        'recruit:interview:edit', 'recruit:interview:delete',
        'recruit:invitation:edit', 'recruit:invitation:reject',
    ):
        assert code in candidate_codes, f'S8-01 新码未进 candidate 候选区：{code}'
    # 候选区总数 = 4 + 3 + 11 = 18（含跨 module 的 interview/application/talent_pool/invitation）
    assert len(candidate_codes) == 18
    # 反向守卫：talent_pool:create 只应归属 candidate，不得同时出现在 talent 候选区，
    # 否则弹窗按模块替换式合并会把另一模块的勾选误删（见 onConfigApply 切分逻辑）。
    talent_codes = {r['resourceCode'] for r in out['talent']}
    assert 'recruit:talent_pool:create' not in talent_codes


@pytest.mark.django_db
@pytest.mark.v2_permission
def test_governed_resources_respects_status_and_type_and_flag():
    """三道过滤缺一不可：strategy_governed / BUTTON / status=1。"""
    from apps.core.views_dynamic_strategy import STRATEGY_MODULE_RESOURCE_MODULES

    # 候选区内只该出现 strategy_governed=True 的 BUTTON 且 status=1
    # 2026-10-21 卡 B5：update_or_create 而非 create —— 测试环境已补齐同码种子行，
    # 裸 create 会撞 resource_code 唯一约束。
    # 且先把全库的 strategy_governed 清零：本用例的前提是「受管控候选区**只有**
    # 下面这 4 行」，而测试环境的种子已把 STRATEGY_GOVERNED_CODES 全部置为受管控
    # （18 条 candidate 码），不隔离就会多出 17 条让断言失真。
    PermissionResource.objects.update(strategy_governed=False)
    PermissionResource.objects.update_or_create(
        resource_code='recruit:candidate:list',
        defaults={
            'system_code': 'recruit', 'resource_name': '候选人列表', 'resource_type': 'BUTTON',
            'module': 'candidate', 'status': 1, 'strategy_governed': True,
        },
    )
    # 反例 1：停用（status=0）—— 勾了也不生效，不得入候选
    PermissionResource.objects.update_or_create(
        resource_code='recruit:candidate:edit',
        defaults={
            'system_code': 'recruit', 'resource_name': '编辑候选人', 'resource_type': 'BUTTON',
            'module': 'candidate', 'status': 0, 'strategy_governed': True,
        },
    )
    # 反例 2：菜单（非 BUTTON）—— 受限功能是按钮级，菜单不是功能
    PermissionResource.objects.update_or_create(
        resource_code='recruit:candidate:menu:view',
        defaults={
            'system_code': 'recruit', 'resource_name': '候选人菜单', 'resource_type': 'MENU',
            'module': 'candidate', 'status': 1, 'strategy_governed': True,
        },
    )
    # 反例 3：未标记受管控 —— 不得入候选
    PermissionResource.objects.update_or_create(
        resource_code='recruit:candidate:delete',
        defaults={
            'system_code': 'recruit', 'resource_name': '删除候选人', 'resource_type': 'BUTTON',
            'module': 'candidate', 'status': 1, 'strategy_governed': False,
        },
    )

    out = DynamicStrategyViewSet._governed_resources()
    candidate_codes = {r['resourceCode'] for r in out['candidate']}
    assert candidate_codes == {'recruit:candidate:list'}

    # 常量维度自检：candidate 必须覆盖 interview / application / talent_pool（1:N 不复用 1:1 表）
    # S8-01（D7）起再并入 invitation：邀约 edit/reject 两条码（module=invitation）按兵哥
    # 清单归候选人管理策略卡，不并入则勾不到 = 策略管不了。
    assert STRATEGY_MODULE_RESOURCE_MODULES['candidate'] == {
        'candidate', 'interview', 'application', 'talent_pool', 'invitation',
    }
    # talent 策略模块当前无受管控资源（talent_pool:create 已并入 candidate）
    assert STRATEGY_MODULE_RESOURCE_MODULES['talent'] == set()
    assert STRATEGY_MODULE_RESOURCE_MODULES['process'] == {'settings'}
