"""T7 单测：``resolve_target_link`` / ``resolve_stage_mapping``（§2.2 阶段映射）。

为什么本文件**必须自带 seed**
=============================
dev 库现状是 ``Application = 0`` / ``Demand = 0``（本轮实测事实 4）。任何依赖
「线上已有申请/流程长什么样」的断言都建立在空表上，看似绿其实什么都没验证。
所以下面每个用例都自建 ``RecruitmentProcess`` + ``RecruitmentStage`` +
``ProcessStageLink``，把要考察的形状（阶段被删 / 前序全没 / 零阶段 / order 重复）
显式摆出来，与 dev 现状完全解耦。

覆盖矩阵（与 §2.2 的 5 条分支一一对应）
=======================================
    精确匹配                → test_exact_match_*
    前序回落                → test_predecessor_fallback_*
    无前序可回落 → 起点     → test_fallback_to_start_*
    无 current_link → 起点  → test_no_current_link_*
    目标流程零阶段 → 报错   → test_empty_process_raises

外加三类「容易写错但不会自己冒烟」的边界：
    - 软删关联不得被选中（既不能精确匹配、也不能当前序/起点）；
    - order 重复时落点必须确定（不随数据库返回顺序漂移）；
    - 纯函数：调用前后 DB 不得有任何写入。
"""
from __future__ import annotations

from typing import List, Optional

import pytest
from django.utils import timezone

from apps.application.services.stage_mapping import (
    ALL_STRATEGIES,
    NO_STAGE_MESSAGE,
    STRATEGY_EXACT,
    STRATEGY_PREDECESSOR,
    STRATEGY_START,
    StageMapping,
    StageMappingError,
    resolve_stage_mapping,
    resolve_target_link,
)
from apps.process.models import (
    ProcessStageLink,
    RecruitmentProcess,
    RecruitmentStage,
    StageType,
)

pytestmark = pytest.mark.django_db


# ============================================================
# Seed 工具 —— 全部自建，不碰 dev 现状
# ============================================================
_STAGE_CACHE: dict = {}


def make_stage(key: str) -> RecruitmentStage:
    """按 key 造（或复用）一个全局阶段。

    ``RecruitmentStage.code`` / ``name`` 都是全局 unique，同一用例里反复造同名阶段
    会撞唯一约束；用 get_or_create 让 seed 写起来像「引用一个字典项」。
    """
    stage, _ = RecruitmentStage.objects.get_or_create(
        code=f'TM{key}',
        defaults={
            'name': f'映射测试阶段-{key}',
            'stage_type': StageType.SCREEN,
        },
    )
    return stage


def make_process(code: str, *, seq: int = 1, is_latest: bool = True) -> RecruitmentProcess:
    """建一行流程版本（``code`` 已去 unique，同 code 可多版本）。"""
    return RecruitmentProcess.objects.create(
        code=code,
        name=f'{code} 映射测试流程 V{seq}',
        current_version=f'V{seq}.0',
        version_seq=seq,
        is_latest=is_latest,
    )


def add_link(
    process: RecruitmentProcess,
    stage: RecruitmentStage,
    order: int,
    *,
    deleted: bool = False,
) -> ProcessStageLink:
    """给流程挂一个阶段关联；``deleted=True`` 时走软删（模拟「新版本删掉了这个阶段」）。"""
    link = ProcessStageLink.objects.create(
        process=process,
        stage=stage,
        order=order,
        is_required=True,
    )
    if deleted:
        link.soft_delete()
    return link


class FakeApplication:
    """只带 ``current_link`` 的最小替身。

    ``resolve_*`` 用鸭子类型取 ``current_link``，不需要真 ``Application``——
    真 Application 要拖 Candidate/Position/Department 整条外键链，
    对一个纯函数的单测来说是纯噪音。真链路的端到端验证在 T3 的 e2e 文件里。
    """

    def __init__(self, current_link: ProcessStageLink | None) -> None:
        self.current_link = current_link


def _link_ids(process: RecruitmentProcess) -> List[str]:
    return list(
        process.stage_links.filter(deleted_at__isnull=True)
        .order_by('order', 'created_at', 'id')
        .values_list('id', flat=True)
    )


# ============================================================
# 1. 精确匹配
# ============================================================
def test_exact_match_returns_same_stage_link() -> None:
    """新版本仍有同一阶段 → 落它，且 remapped=False。"""
    s1, s2, s3 = make_stage('A1'), make_stage('A2'), make_stage('A3')

    old = make_process('WMAP01', seq=1, is_latest=False)
    old_link = add_link(old, s2, 2)

    new = make_process('WMAP01', seq=2, is_latest=True)
    add_link(new, s1, 1)
    new_link = add_link(new, s2, 2)
    add_link(new, s3, 3)

    mapping = resolve_stage_mapping(FakeApplication(old_link), new)

    assert mapping.link.id == new_link.id
    assert mapping.stage.id == s2.id
    assert mapping.strategy == STRATEGY_EXACT
    assert mapping.remapped is False
    assert mapping.source_link_id == old_link.id
    assert mapping.source_stage_id == s2.id
    assert mapping.source_order == 2


def test_exact_match_accepts_link_as_source() -> None:
    """§2.2 明确要求「application 或 current_link」两种入参等价。"""
    s1 = make_stage('B1')
    old = make_process('WMAP02', seq=1, is_latest=False)
    old_link = add_link(old, s1, 1)
    new = make_process('WMAP02', seq=2, is_latest=True)
    new_link = add_link(new, s1, 1)

    assert resolve_target_link(old_link, new).id == new_link.id
    assert resolve_target_link(FakeApplication(old_link), new).id == new_link.id


def test_exact_match_wins_over_order_position() -> None:
    """精确匹配优先于序号：同一阶段在新版本挪到了别的位置也照样命中。"""
    s1, s2 = make_stage('C1'), make_stage('C2')
    old = make_process('WMAP03', seq=1, is_latest=False)
    old_link = add_link(old, s2, 2)

    new = make_process('WMAP03', seq=2, is_latest=True)
    add_link(new, s1, 1)
    moved = add_link(new, s2, 9)  # 同阶段被挪到末尾

    mapping = resolve_stage_mapping(old_link, new)
    assert mapping.link.id == moved.id
    assert mapping.strategy == STRATEGY_EXACT
    assert mapping.link.order == 9


# ============================================================
# 2. 前序回落
# ============================================================
def test_predecessor_fallback_picks_max_order_below_current() -> None:
    """当前阶段在新版本被删 → 取 order 小于它的**最大**一个（不是第一个）。"""
    s1, s2, s3, s4 = make_stage('D1'), make_stage('D2'), make_stage('D3'), make_stage('D4')

    old = make_process('WMAP04', seq=1, is_latest=False)
    old_link = add_link(old, s3, 3)

    new = make_process('WMAP04', seq=2, is_latest=True)
    add_link(new, s1, 1)
    expected = add_link(new, s2, 2)   # 前序里 order 最大 → 落它
    add_link(new, s4, 4)              # 后继，不得被选中

    mapping = resolve_stage_mapping(FakeApplication(old_link), new)

    assert mapping.link.id == expected.id
    assert mapping.strategy == STRATEGY_PREDECESSOR
    assert mapping.remapped is True
    assert mapping.source_stage_id == s3.id
    assert mapping.link.order == 2


def test_predecessor_never_advances_forward() -> None:
    """只有后继没有前序时，绝不能「前进」到后继（那等于白送候选人一个阶段）。"""
    s2, s3 = make_stage('E2'), make_stage('E3')
    old = make_process('WMAP05', seq=1, is_latest=False)
    old_link = add_link(old, s2, 2)

    new = make_process('WMAP05', seq=2, is_latest=True)
    later = add_link(new, s3, 7)  # 唯一的 live 关联，order 比当前大

    mapping = resolve_stage_mapping(old_link, new)

    # 没有前序 → 落起点；这里起点恰好就是 later（全流程只有它），
    # 但策略必须是 START 而不是 PREDECESSOR —— 语义不能混。
    assert mapping.link.id == later.id
    assert mapping.strategy == STRATEGY_START
    assert mapping.remapped is True


def test_soft_deleted_link_is_not_a_valid_predecessor() -> None:
    """软删关联不得充当前序：它在新版本里根本不存在。"""
    s1, s2, s3 = make_stage('F1'), make_stage('F2'), make_stage('F3')

    old = make_process('WMAP06', seq=1, is_latest=False)
    old_link = add_link(old, s3, 3)

    new = make_process('WMAP06', seq=2, is_latest=True)
    alive = add_link(new, s1, 1)
    add_link(new, s2, 2, deleted=True)  # order 更大但已软删 → 不得被选中

    mapping = resolve_stage_mapping(old_link, new)

    assert mapping.link.id == alive.id
    assert mapping.strategy == STRATEGY_PREDECESSOR
    assert mapping.link.stage_id == s1.id


def test_soft_deleted_link_cannot_be_exact_match() -> None:
    """同一阶段在新版本存在但已软删 → 不算精确匹配，必须回落。"""
    s1, s2 = make_stage('G1'), make_stage('G2')

    old = make_process('WMAP07', seq=1, is_latest=False)
    old_link = add_link(old, s2, 2)

    new = make_process('WMAP07', seq=2, is_latest=True)
    alive = add_link(new, s1, 1)
    add_link(new, s2, 2, deleted=True)  # 同阶段，但软删了

    mapping = resolve_stage_mapping(old_link, new)

    assert mapping.strategy == STRATEGY_PREDECESSOR
    assert mapping.link.id == alive.id
    assert mapping.remapped is True


# ============================================================
# 3. 无前序 → 起点
# ============================================================
def test_fallback_to_start_when_no_predecessor_exists() -> None:
    """当前阶段是旧版本的第 1 步、新版本里又没有它 → 落新版本起点。"""
    s1, s2 = make_stage('H1'), make_stage('H2')

    old = make_process('WMAP08', seq=1, is_latest=False)
    old_link = add_link(old, s1, 1)

    new = make_process('WMAP08', seq=2, is_latest=True)
    start = add_link(new, s2, 1)
    add_link(new, make_stage('H3'), 2)

    mapping = resolve_stage_mapping(FakeApplication(old_link), new)

    assert mapping.link.id == start.id
    assert mapping.strategy == STRATEGY_START
    assert mapping.remapped is True


def test_fallback_to_start_when_all_predecessors_soft_deleted() -> None:
    """前序全被删光 → 落起点（此时起点是唯一存活的后继）。"""
    s1, s2, s3 = make_stage('I1'), make_stage('I2'), make_stage('I3')

    old = make_process('WMAP09', seq=1, is_latest=False)
    old_link = add_link(old, s2, 5)

    new = make_process('WMAP09', seq=2, is_latest=True)
    add_link(new, s1, 1, deleted=True)   # 唯一前序，已删
    survivor = add_link(new, s3, 8)

    mapping = resolve_stage_mapping(old_link, new)

    assert mapping.link.id == survivor.id
    assert mapping.strategy == STRATEGY_START


# ============================================================
# 4. 无 current_link → 起点
# ============================================================
def test_no_current_link_falls_back_to_start() -> None:
    """Application.current_link 为空（SET_NULL 后遗症）→ 落起点。"""
    s1, s2 = make_stage('J1'), make_stage('J2')
    new = make_process('WMAP10', seq=1, is_latest=True)
    start = add_link(new, s1, 1)
    add_link(new, s2, 2)

    mapping = resolve_stage_mapping(FakeApplication(None), new)

    assert mapping.link.id == start.id
    assert mapping.strategy == STRATEGY_START
    assert mapping.remapped is True
    # 无锚点 → 三个 source_* 快照字段必须全空，不得编造
    assert mapping.source_link_id is None
    assert mapping.source_stage_id is None
    assert mapping.source_order is None


def test_none_source_is_accepted_and_falls_back_to_start() -> None:
    """直接传 None 与传「current_link 为空的 application」等价。"""
    s1 = make_stage('K1')
    new = make_process('WMAP11', seq=1, is_latest=True)
    start = add_link(new, s1, 1)

    assert resolve_target_link(None, new).id == start.id


def test_start_ignores_soft_deleted_first_link() -> None:
    """起点必须是第一个 **live** 关联，软删的最小 order 行不得被当起点。"""
    s1, s2 = make_stage('L1'), make_stage('L2')
    new = make_process('WMAP12', seq=1, is_latest=True)
    add_link(new, s1, 1, deleted=True)
    real_start = add_link(new, s2, 2)

    mapping = resolve_stage_mapping(None, new)

    assert mapping.link.id == real_start.id
    assert mapping.strategy == STRATEGY_START


# ============================================================
# 5. 零阶段 → 报错
# ============================================================
def test_empty_process_raises() -> None:
    """目标流程一个关联都没有 → 抛 StageMappingError（ValueError 子类）。"""
    new = make_process('WMAP13', seq=1, is_latest=True)

    with pytest.raises(StageMappingError) as exc:
        resolve_target_link(None, new)
    assert NO_STAGE_MESSAGE in str(exc.value)


def test_all_links_soft_deleted_raises() -> None:
    """关联全被软删 == 零阶段，同样必须报错而不是返回软删行。"""
    s1 = make_stage('M1')
    new = make_process('WMAP14', seq=1, is_latest=True)
    add_link(new, s1, 1, deleted=True)

    with pytest.raises(StageMappingError):
        resolve_stage_mapping(None, new)


def test_stage_mapping_error_is_value_error() -> None:
    """§2.2 要求「抛明确异常（如 ValueError）」，调用方可能按 ValueError 捕获。"""
    assert issubclass(StageMappingError, ValueError)


# ============================================================
# 6. 边界：order 重复 / 入参非法 / 纯函数
# ============================================================
def test_duplicate_orders_resolve_deterministically() -> None:
    """order 重复（dev 实测存在 orders=[2,3,4,4,5,8,9,10]）时落点必须确定。

    连续解析多次结果必须一致，且与「按 (order, created_at, id) 排序后的首个/末个前序」
    一致 —— 否则落点会随数据库返回顺序漂移，同一次升级在两台机器上结果不同。
    """
    s1, s2, s3, s4 = make_stage('N1'), make_stage('N2'), make_stage('N3'), make_stage('N4')

    old = make_process('WMAP15', seq=1, is_latest=False)
    old_link = add_link(old, s4, 9)

    new = make_process('WMAP15', seq=2, is_latest=True)
    add_link(new, s1, 4)
    tie_second = add_link(new, s2, 4)  # 同 order，创建更晚 → 排序在后 → 它是「最大前序」
    add_link(new, s3, 2)

    ordered = _link_ids(new)
    assert ordered[-1] == tie_second.id, '前置：排序键必须让同 order 的后建行排在后面'

    first = resolve_stage_mapping(old_link, new)
    second = resolve_stage_mapping(old_link, new)

    assert first.link.id == second.link.id == tie_second.id
    assert first.strategy == STRATEGY_PREDECESSOR


def test_invalid_source_type_raises_type_error() -> None:
    """传个字符串进来是调用方的编程错误 → 必须响亮失败，不得静默落起点。"""
    s1 = make_stage('O1')
    new = make_process('WMAP16', seq=1, is_latest=True)
    add_link(new, s1, 1)

    with pytest.raises(TypeError):
        resolve_target_link('not-a-link', new)  # type: ignore[arg-type]


def test_resolution_is_side_effect_free() -> None:
    """纯函数保证：解析前后不得新增/修改任何行。

    这条守的是「有人图省事把改指逻辑塞进 resolve_target_link」——
    一旦发生，T3/T8 的事务边界就被偷偷绕过了。
    """
    s1, s2 = make_stage('P1'), make_stage('P2')
    old = make_process('WMAP17', seq=1, is_latest=False)
    old_link = add_link(old, s2, 2)
    new = make_process('WMAP17', seq=2, is_latest=True)
    add_link(new, s1, 1)

    before_links = ProcessStageLink.objects.count()
    before_processes = RecruitmentProcess.objects.count()
    before_updated = list(
        ProcessStageLink.objects.order_by('id').values_list('id', 'updated_at'),
    )

    resolve_stage_mapping(old_link, new)
    resolve_target_link(old_link, new)

    assert ProcessStageLink.objects.count() == before_links
    assert RecruitmentProcess.objects.count() == before_processes
    assert list(
        ProcessStageLink.objects.order_by('id').values_list('id', 'updated_at'),
    ) == before_updated


# ============================================================
# 7. 契约：返回结构与审计字段
# ============================================================
def test_strategy_value_is_always_within_declared_set() -> None:
    """策略常量集合是对外契约（T3/T8 会把它写进审计），不得返回集合外的值。"""
    s1, s2 = make_stage('Q1'), make_stage('Q2')
    old = make_process('WMAP18', seq=1, is_latest=False)
    old_link = add_link(old, s2, 2)
    new = make_process('WMAP18', seq=2, is_latest=True)
    add_link(new, s1, 1)

    for source in (None, old_link, FakeApplication(old_link)):
        mapping = resolve_stage_mapping(source, new)
        assert mapping.strategy in ALL_STRATEGIES
        assert isinstance(mapping, StageMapping)
        assert mapping.remapped is (mapping.strategy != STRATEGY_EXACT)


def test_as_audit_detail_shape() -> None:
    """审计字典的 key 集合固定：T3 与 T8 靠它保持同构。"""
    s1, s2 = make_stage('R1'), make_stage('R2')
    old = make_process('WMAP19', seq=1, is_latest=False)
    old_link = add_link(old, s2, 5)
    new = make_process('WMAP19', seq=2, is_latest=True)
    target = add_link(new, s1, 1)

    detail = resolve_stage_mapping(old_link, new).as_audit_detail()

    assert set(detail) == {
        'stage_remapped', 'stage_map_strategy',
        'from_link_id', 'from_stage_id', 'from_stage_order',
        'to_link_id', 'to_stage_id', 'to_stage_order',
    }
    assert detail['stage_remapped'] is True
    assert detail['stage_map_strategy'] == STRATEGY_PREDECESSOR
    assert detail['from_link_id'] == old_link.id
    assert detail['from_stage_id'] == s2.id
    assert detail['from_stage_order'] == 5
    assert detail['to_link_id'] == target.id
    assert detail['to_stage_id'] == s1.id
    assert detail['to_stage_order'] == 1


def test_returned_link_always_belongs_to_target_process_and_is_live() -> None:
    """跨所有分支的不变量：落点必属于目标流程且未软删。"""
    s1, s2, s3 = make_stage('S1'), make_stage('S2'), make_stage('S3')
    old = make_process('WMAP20', seq=1, is_latest=False)
    exact_src = add_link(old, s1, 1)
    fallback_src = add_link(old, s3, 9)

    new = make_process('WMAP20', seq=2, is_latest=True)
    add_link(new, s1, 1)
    add_link(new, s2, 2)

    for source in (exact_src, fallback_src, None):
        link = resolve_target_link(source, new)
        assert link.process_id == new.id
        assert link.deleted_at is None


def test_timezone_import_is_not_required_for_pure_resolution() -> None:
    """回归哨兵：解析路径不得依赖「当前时间」，否则结果不可复现。

    直接断言两次调用（中间推进一个时间戳）结果完全一致。
    """
    s1, s2 = make_stage('T1'), make_stage('T2')
    old = make_process('WMAP21', seq=1, is_latest=False)
    old_link = add_link(old, s2, 3)
    new = make_process('WMAP21', seq=2, is_latest=True)
    add_link(new, s1, 1)

    first = resolve_stage_mapping(old_link, new)
    _ = timezone.now()
    second = resolve_stage_mapping(old_link, new)

    assert first.link.id == second.link.id
    assert first.strategy == second.strategy
    assert first.as_audit_detail() == second.as_audit_detail()
