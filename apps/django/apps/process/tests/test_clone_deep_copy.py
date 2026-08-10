"""T4 回归：``clone_process_with_new_version`` 的深拷贝补全（V6 / X2 / 产品 Q3、Q4）。

被修的四类缺陷，以及每类对应的钉子
====================================
1. **X2 软删 link 被一并克隆**（``stage_links.all()``）——本仓反向 Manager 是**原生**
   Manager，不过滤软删。开发库流程 ``Yw9GBzXA4rJT8348AthR2`` 的 8 条 link 里有 4 条
   是软删的，克隆一次就把 4 条已删阶段复活进新版本。
   → :func:`test_clone_excludes_soft_deleted_stage_links`

2. **StageRule 手抄字段清单漏拷**——模型 2026-07-03 扩了 9 个字段
   （``auto_advance_*`` / ``default_handler_*`` / ``time_limit*`` / ``interview_round_ids``），
   clone 里那份 17 字段的手抄清单从未同步，新版本静默丢配置。
   → :func:`test_clone_stage_rule_copies_every_concrete_field`（遍历
   ``_meta.concrete_fields`` 断言，将来加字段自动被覆盖，不需要改测试）

3. **两个反向关系根本没拷**（``entry_condition_rules`` / ``time_limit_rules``）。
   拷的时候有个不显眼的坑：这两个模型上的 ``process_id`` 是**普通 CharField，不是 FK**，
   ``workflow_version`` 同理。自省拷贝会把旧流程 ID 与旧版本号原样带过来，而因为不是 FK，
   **DB 层没有任何约束会报错**——脏引用完全静默。
   → :func:`test_clone_entry_condition_rules_repoint_to_new_process`
   → :func:`test_clone_time_limit_rules_repoint_to_new_process`

4. **AutomationRule 未拷贝**（产品 Q3 裁定本轮实现）。不拷 = 静默的能力归零：
   ``AutomationRule.process`` 是 CASCADE FK 指向**具体行**，新版本行天生没有任何规则，
   用户改个小配置就会「第二天发现自动提醒全停了」。
   → :func:`test_clone_copies_automation_rules_when_stages_unchanged` 等 3 条

另有 Q4 红线（克隆**不**改指业务数据）：
:func:`test_clone_does_not_repoint_demand_position_application`。
"""
from __future__ import annotations

import pytest

from apps.automation.models import AutomationRule
from apps.entry_condition.models import ConditionItem, EntryConditionRule
from apps.process.models import (
    ProcessStageLink,
    RecruitmentProcess,
    RecruitmentStage,
    StageRule,
    StageType,
)
from apps.process.services.versioning import clone_process_with_new_version
from apps.time_limit.models import TimeLimitRule

pytestmark = pytest.mark.django_db


# ============================================================
# 工具
# ============================================================
def make_process(code: str, seq: int = 1, *, is_latest: bool = True, **kwargs) -> RecruitmentProcess:
    """建一行流程版本。``current_version`` 随 seq 走，避免误撞 C2。"""
    defaults = dict(
        code=code,
        name=f'{code} 流程 V{seq}',
        current_version=f'V{seq}.0',
        version_seq=seq,
        is_latest=is_latest,
    )
    defaults.update(kwargs)
    return RecruitmentProcess.objects.create(**defaults)


def make_stage(code: str, name: str, stage_type: str = StageType.SCREEN) -> RecruitmentStage:
    """建一个全局阶段。``code`` 与 ``name`` 都是全局 unique，用例间不得复用。"""
    return RecruitmentStage.objects.create(code=code, name=name, stage_type=stage_type)


def make_link(process, stage, order: int = 1, **kwargs) -> ProcessStageLink:
    return ProcessStageLink.objects.create(
        process=process, stage=stage, order=order, **kwargs,
    )


def make_entry_rule(link, process, seq: int = 1, *, item_count: int = 0) -> EntryConditionRule:
    """建一条进入条件规则（可选带 N 个条件项）。"""
    rule = EntryConditionRule.objects.create(
        link=link,
        process_id=process.id,
        workflow_version=process.current_version,
        rule_name=f'规则{seq}',
        rule_seq=seq,
        expression='1 AND 2',
        reject_message=f'不满足规则{seq}',
    )
    for i in range(1, item_count + 1):
        ConditionItem.objects.create(
            rule=rule,
            item_seq=i,
            condition_type='CANDIDATE',
            field=f'FIELD_{i}',
            operator='EQ',
            value={'v': i},
        )
    return rule


def make_time_limit_rule(link, process, *, priority: int = 0) -> TimeLimitRule:
    return TimeLimitRule.objects.create(
        link=link,
        process_id=process.id,
        workflow_version=process.current_version,
        rule_name=f'限时{priority}',
        conditions=[{'field': 'LEVEL', 'op': 'EQ', 'value': 'P7'}],
        lock_duration=7,
        extension_per_person=2,
        priority=priority,
    )


def make_automation_rule(process, stage, *, next_stage=None, name: str = '自动推进') -> AutomationRule:
    return AutomationRule.objects.create(
        name=name,
        process=process,
        stage=stage,
        next_stage=next_stage,
        trigger_type=AutomationRule.TriggerType.STAGE_ENTERED,
        trigger_timing=AutomationRule.TriggerTiming.IMMEDIATE,
        action_type=(
            AutomationRule.ActionType.SKIP_TO if next_stage
            else AutomationRule.ActionType.REMIND
        ),
        condition_json=[{'field': 'SCORE', 'op': 'GTE', 'value': 80}],
        scope_json={'priority': 'P0'},
    )


# ============================================================
# 1. stage_links：只拷 live 行
# ============================================================
def test_clone_excludes_soft_deleted_stage_links() -> None:
    """**X2 钉子**：软删的 link 不得进入新版本。

    把服务里的 ``_live_children(process.stage_links, ...)`` 退化成 ``.all()``，
    本用例立刻变红（新版本会多出一条已删阶段）。
    """
    old = make_process('W940')
    live_stage = make_stage('P940', 'T4 存活阶段')
    dead_stage = make_stage('P941', 'T4 已删阶段')
    make_link(old, live_stage, order=1)
    dead_link = make_link(old, dead_stage, order=2)
    dead_link.soft_delete()

    new = clone_process_with_new_version(old)

    new_stage_ids = set(new.stage_links.values_list('stage_id', flat=True))
    assert new_stage_ids == {live_stage.id}, (
        f'软删 link 被克隆进新版本（拿到 {new_stage_ids}）—— 原生 Manager 不过滤软删，'
        '必须显式 filter(deleted_at__isnull=True)'
    )


def test_clone_preserves_stage_link_order() -> None:
    """顺序即 ``entry_rule_expression``（``(1 AND 2) OR 3``）的序号基准，不得错位。"""
    old = make_process('W941')
    stages = [make_stage(f'P94{i}', f'T4 顺序阶段{i}') for i in (2, 3, 4)]
    for idx, stage in enumerate(stages, start=1):
        make_link(old, stage, order=idx)

    new = clone_process_with_new_version(old)

    assert list(new.stage_links.order_by('order').values_list('stage_id', 'order')) == [
        (stages[0].id, 1), (stages[1].id, 2), (stages[2].id, 3),
    ]


# ============================================================
# 2. StageRule：自省全字段拷贝
# ============================================================
def test_clone_stage_rule_copies_every_concrete_field() -> None:
    """**漏字段钉子**：遍历 ``_meta.concrete_fields`` 逐个断言，而不是列举字段名。

    历史缺陷是手抄 17 个字段、模型有 26 个，扩字段那 9 项（``auto_advance_*`` /
    ``default_handler_*`` / ``time_limit*`` / ``interview_round_ids``）从未被拷。
    用自省断言的好处：将来给 StageRule 加字段而忘了管拷贝，本用例**自动**变红。
    """
    old = make_process('W942')
    stage = make_stage('P945', 'T4 规则阶段')
    link = make_link(old, stage)
    old_rule = StageRule.objects.create(
        link=link,
        data_source='DEMAND',
        data_field='hiring_manager',
        processing_rule='SEQUENTIAL',
        processor_order=['u1', 'u2'],
        current_processor_index=1,
        auto_skip_n_plus_two=True,
        inherit_prior_consensus=True,
        legacy_time_limit_days=9,
        legacy_grab_threshold=11,
        is_grab_mode=True,
        grab_threshold=42,
        interview_rounds=3,
        interview_format='JOINT',
        # ↓ 老实现漏拷的 9 个（2026-07-03 扩字段）
        auto_advance_type='MEET_NEXT',
        auto_advance_timing='DELAYED',
        auto_advance_days=5,
        default_handler_type='FROM_DEMAND',
        default_handler_fields=['hiring_manager'],
        default_handler_user_ids=['u9'],
        time_limit=72,
        time_limit_scope='ALL',
        interview_round_ids=['r1', 'r2'],
    )

    new = clone_process_with_new_version(old)

    new_rule = StageRule.objects.get(link__process=new)
    skip = {'id', 'link', 'created_at', 'updated_at', 'deleted_at', 'created_by', 'updated_by'}
    for field in StageRule._meta.concrete_fields:
        if field.name in skip or field.attname in skip:
            continue
        assert getattr(new_rule, field.attname) == getattr(old_rule, field.attname), (
            f'StageRule.{field.name} 未被拷贝到新版本 —— 手抄字段清单又漏了，'
            f'拷贝必须走 _meta.concrete_fields 自省'
        )
    assert new_rule.id != old_rule.id
    assert new_rule.link_id != link.id, '新 StageRule 指回了老 link'


def test_clone_deep_copies_stage_rule_json_fields() -> None:
    """JSONField 必须**深**拷：浅拷会让新旧两行共享同一个 Python 对象。"""
    old = make_process('W943')
    stage = make_stage('P946', 'T4 深拷阶段')
    link = make_link(old, stage)
    old_rule = StageRule.objects.create(
        link=link,
        processor_order=['u1'],
        default_handler_fields=['f1'],
        default_handler_user_ids=['u9'],
        interview_round_ids=['r1'],
    )

    new = clone_process_with_new_version(old)
    new_rule = StageRule.objects.get(link__process=new)

    for attr in (
        'processor_order', 'default_handler_fields',
        'default_handler_user_ids', 'interview_round_ids',
    ):
        new_value = getattr(new_rule, attr)
        assert new_value is not getattr(old_rule, attr), f'{attr} 是同一个对象引用（浅拷贝）'
        new_value.append('MUTATED')

    old_rule.refresh_from_db()
    assert old_rule.processor_order == ['u1'], '改新行的 JSON 影响到了老行 —— 违反 BR-103'


def test_clone_link_without_stage_rule_does_not_raise() -> None:
    """link 没有 1:1 的 stage_rule 时，克隆不得抛异常。"""
    old = make_process('W944')
    make_link(old, make_stage('P947', 'T4 无规则阶段'))

    new = clone_process_with_new_version(old)

    assert new.stage_links.count() == 1
    assert StageRule.objects.filter(link__process=new).count() == 0


# ============================================================
# 3. entry_condition_rules / time_limit_rules：新拷 + 改指
# ============================================================
def test_clone_entry_condition_rules_repoint_to_new_process() -> None:
    """**process_id / workflow_version 钉子**（本轮最容易漏的一处）。

    这两个字段是**普通 CharField，不是 FK**——排除列表里写 ``'process'`` 拦不住
    ``process_id``，自省拷贝会把旧流程 ID 与旧版本号原样带过来，且 DB 层无 FK 约束
    可拦，脏引用完全静默。删掉服务里那两行显式覆盖，本用例立刻变红。
    """
    old = make_process('W945')
    stage = make_stage('P948', 'T4 进入条件阶段')
    link = make_link(old, stage)
    make_entry_rule(link, old, seq=1, item_count=3)
    make_entry_rule(link, old, seq=2, item_count=2)

    new = clone_process_with_new_version(old)

    new_rules = EntryConditionRule.objects.filter(link__process=new).order_by('rule_seq')
    assert new_rules.count() == 2, '进入条件规则未被拷贝到新版本'
    for rule in new_rules:
        assert rule.process_id == new.id, (
            f'EntryConditionRule.process_id 仍指向旧流程 {rule.process_id}（应为 {new.id}）'
            ' —— 它是 CharField 不是 FK，没有任何 DB 约束会拦住这个脏引用'
        )
        assert rule.workflow_version == new.current_version, (
            f'workflow_version 仍是旧版本 {rule.workflow_version}（应为 {new.current_version}）'
        )
    # 老行原封不动（BR-103）
    for rule in EntryConditionRule.objects.filter(link__process=old):
        assert rule.process_id == old.id
        assert rule.workflow_version == old.current_version


def test_clone_recursively_copies_condition_items_in_order() -> None:
    """二级 ``items`` 必须递归拷贝，且顺序不变（``expression`` 按序号引用条件项）。"""
    old = make_process('W946')
    link = make_link(old, make_stage('P949', 'T4 条件项阶段'))
    old_rule = make_entry_rule(link, old, seq=1, item_count=3)

    new = clone_process_with_new_version(old)

    new_rule = EntryConditionRule.objects.get(link__process=new)
    old_items = list(old_rule.items.order_by('item_seq').values_list('item_seq', 'field'))
    new_items = list(new_rule.items.order_by('item_seq').values_list('item_seq', 'field'))
    assert new_items == old_items == [(1, 'FIELD_1'), (2, 'FIELD_2'), (3, 'FIELD_3')], (
        '条件项顺序错位 —— entry_rule_expression 的序号会指向另一条件，静默改变准入逻辑'
    )
    assert not ConditionItem.objects.filter(rule=new_rule, id__in=[i.id for i in old_rule.items.all()]).exists(), (
        '新规则复用了旧条件项的行（应是新建）'
    )


def test_clone_time_limit_rules_repoint_to_new_process() -> None:
    """``TimeLimitRule`` 同样带 CharField 型 ``process_id`` / ``workflow_version``。"""
    old = make_process('W947')
    link = make_link(old, make_stage('P950', 'T4 限时阶段'))
    make_time_limit_rule(link, old, priority=0)
    make_time_limit_rule(link, old, priority=1)

    new = clone_process_with_new_version(old)

    new_rules = TimeLimitRule.objects.filter(link__process=new).order_by('priority')
    assert new_rules.count() == 2, '限时规则未被拷贝到新版本'
    assert [r.lock_duration for r in new_rules] == [7, 7]
    for rule in new_rules:
        assert rule.process_id == new.id, 'TimeLimitRule.process_id 仍指向旧流程'
        assert rule.workflow_version == new.current_version


def test_clone_children_never_point_back_to_old_link() -> None:
    """所有子对象的 FK 必须落在**新** link 上，一条都不许指回旧 link。"""
    old = make_process('W948')
    link = make_link(old, make_stage('P951', 'T4 指向阶段'))
    StageRule.objects.create(link=link)
    make_entry_rule(link, old, seq=1, item_count=1)
    make_time_limit_rule(link, old)

    new = clone_process_with_new_version(old)
    old_link_ids = set(old.stage_links.values_list('id', flat=True))
    new_link_ids = set(new.stage_links.values_list('id', flat=True))

    assert old_link_ids.isdisjoint(new_link_ids)
    for model in (StageRule, EntryConditionRule, TimeLimitRule):
        stray = model.objects.filter(link_id__in=old_link_ids).count()
        original = 1
        assert stray == original, (
            f'{model.__name__} 挂在旧 link 上的行数变成 {stray}（应恒为 {original}）'
            ' —— 克隆把旧行搬走了或多写了一份'
        )
        assert model.objects.filter(link_id__in=new_link_ids).count() == 1


# ============================================================
# 4. automation_rules（产品 Q3）
# ============================================================
def test_clone_copies_automation_rules_when_stages_unchanged() -> None:
    """阶段未变更时，新版本的规则数与旧版本相等，且 ``enabled`` 保持原值。"""
    old = make_process('W949')
    stage_a = make_stage('P952', 'T4 自动化阶段A')
    stage_b = make_stage('P953', 'T4 自动化阶段B')
    make_link(old, stage_a, order=1)
    make_link(old, stage_b, order=2)
    make_automation_rule(old, stage_a, next_stage=stage_b, name='A→B 自动推进')
    make_automation_rule(old, stage_b, name='B 超时提醒')

    new = clone_process_with_new_version(old)

    assert new.automation_rules.count() == old.automation_rules.count() == 2, (
        '克隆未复制自动化规则 —— AutomationRule.process 是指向具体行的 CASCADE FK，'
        '不复制等于新版本上线即「自动提醒全停」'
    )
    copied = new.automation_rules.get(name='A→B 自动推进')
    assert copied.stage_id == stage_a.id
    assert copied.next_stage_id == stage_b.id, 'next_stage 指向全局阶段字典，阶段仍在就不该被清空'
    assert copied.enabled is True
    assert copied.condition_json == [{'field': 'SCORE', 'op': 'GTE', 'value': 80}]
    assert new._degraded_automation_rules == [], '阶段未变更却报告了降级规则'


def test_clone_skips_automation_rule_whose_stage_was_removed() -> None:
    """触发阶段已从新版本移除 → **跳过不复制**，并出现在降级清单里。"""
    old = make_process('W950')
    stage_a = make_stage('P954', 'T4 保留阶段')
    stage_gone = make_stage('P955', 'T4 移除阶段')
    make_link(old, stage_a, order=1)
    make_link(old, stage_gone, order=2).soft_delete()
    make_automation_rule(old, stage_a, name='保留的规则')
    make_automation_rule(old, stage_gone, name='哑规则')

    new = clone_process_with_new_version(old)

    assert list(new.automation_rules.values_list('name', flat=True)) == ['保留的规则'], (
        '绑定已移除阶段的规则被复制过来了 —— 它永不触发，是纯粹的哑规则'
    )
    assert [(d['rule_name'], d['action'], d['reason']) for d in new._degraded_automation_rules] == [
        ('哑规则', 'SKIPPED', 'STAGE_REMOVED'),
    ]


def test_clone_disables_automation_rule_whose_next_stage_was_removed() -> None:
    """目标阶段已移除 → 仍复制规则（用户可重配），但 ``next_stage`` 置空并禁用。"""
    old = make_process('W951')
    stage_a = make_stage('P956', 'T4 起点阶段')
    stage_gone = make_stage('P957', 'T4 目标已移除阶段')
    make_link(old, stage_a, order=1)
    make_link(old, stage_gone, order=2).soft_delete()
    make_automation_rule(old, stage_a, next_stage=stage_gone, name='跳转到已删阶段')

    new = clone_process_with_new_version(old)

    copied = new.automation_rules.get()
    assert copied.stage_id == stage_a.id
    assert copied.next_stage_id is None, '目标阶段已移除，next_stage 必须置空，不能带着悬空目标运行'
    assert copied.enabled is False, '目标阶段已移除的规则必须禁用，等用户重配'
    assert [(d['rule_name'], d['action'], d['reason']) for d in new._degraded_automation_rules] == [
        ('跳转到已删阶段', 'DISABLED', 'NEXT_STAGE_REMOVED'),
    ]
    # 老行不受影响（BR-103）
    old_rule = old.automation_rules.get()
    assert old_rule.next_stage_id == stage_gone.id
    assert old_rule.enabled is True


# ============================================================
# 5. Q4 红线：克隆不改指任何业务数据
# ============================================================
def test_clone_does_not_repoint_demand_position_application(department, hr_user) -> None:
    """**Q4 钉子**：新版本只对之后新建的需求生效，在跑的一律不动（BR-102）。

    Demand / Position / Application 三张表的 ``process_id`` 在克隆前后必须逐行相同。
    用「快照全表」而非「查我建的那几行」，这样将来新增指向流程的业务表也能被扫到。
    """
    from apps.application.models import Application
    from apps.candidate.models import Candidate
    from apps.demand.models import Demand
    from apps.position.models import Position

    old = make_process('W952')
    make_link(old, make_stage('P958', 'T4 Q4 阶段'))

    demand = Demand.objects.create(
        code='D-T4-001', title='T4 需求', department=department,
        requested_by=hr_user, hr=hr_user, headcount=1,
        process=old, process_version=old.current_version,
    )
    position = Position.objects.create(
        code='POS-T4-001', title='T4 职位', department=department,
        hiring_manager=hr_user, owner=hr_user,
        process=old, process_version=old.current_version,
    )
    candidate = Candidate.objects.create(
        id='cand-t4-q4-001', name='T4 候选人', phone='13800000940',
    )
    application = Application.objects.create(
        code='APP-T4-001', candidate=candidate, position=position,
        process=old, workflow_version=old.current_version,
    )

    def snapshot() -> dict:
        return {
            model.__name__: dict(model.objects.values_list('id', 'process_id'))
            for model in (Demand, Position, Application)
        }

    before = snapshot()
    assert before['Demand'] and before['Position'] and before['Application'], (
        '前置条件：三张表都得有行，否则本用例是空断言'
    )

    new = clone_process_with_new_version(old)

    assert snapshot() == before, (
        'clone 改指了在跑的业务数据 —— 违反产品 Q4 裁定与 BR-102；'
        '改指必须由显式的升版本动作发起'
    )
    assert demand.process_id == old.id
    assert new.demands.count() == 0, '新版本行不应凭空拥有需求引用'
    assert application.process_id == old.id
