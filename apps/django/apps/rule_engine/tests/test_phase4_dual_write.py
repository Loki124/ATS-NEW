"""Phase 4：campus_control + mou 双写迁移单元测试（apps/rule_engine + 各 app signals）。

覆盖：
- sync_control_rule_to_unified（CONSTRAINT / OFFER_SUBMITTED / BLOCK_HARD·BLOCK_SOFT）
- sync_mou_rule_to_unified（TCA / BUSINESS_EVENT / SET_PERMISSION）
- 双写信号（post_save 镜像 + post_delete 软删传播）
- check_rule_engine_consistency 对 campus_control / mou 的 MISSING / DRIFT / --fix
- 执行器注册（ConstraintValidator / MouPermissionExecutor 进入 action_registry）
- MouRule 重命名迁移保留物理表 mou_automation_rules（数据完整性）

不依赖现网引擎，仅验证镜像数据正确性与一致性。
"""
import uuid

import pytest
from django.core.management import call_command

from apps.campus_control.models import ControlDimension, ControlIndicator, ControlRule
from apps.automation.models import AutomationRule
from apps.mou.models import MouRule
from apps.rule_engine.bridge import (
    AUTOMATION_SOURCE_APP,
    CAMPUS_CONTROL_SOURCE_APP,
    MOU_SOURCE_APP,
    mirror_campus_offer_validation,
    sync_automation_rule_to_unified,
    sync_control_rule_to_unified,
    sync_mou_rule_to_unified,
)
from apps.rule_engine.integrations.campus_control_executors import ConstraintValidator
from apps.rule_engine.integrations.mou_executors import MouPermissionExecutor
from apps.rule_engine.management.commands.check_rule_engine_consistency import Command
from apps.rule_engine.models import (
    Action,
    EvaluateResult,
    Rule,
    RuleCategory,
    RuleExecutionLog,
    RuleStatus,
    UnifiedActionType,
    UnifiedTriggerType,
)

# campus ControlRule.save() 内 select_for_update 自动补号，需事务隔离（同 test_rule_config）
pytestmark = pytest.mark.django_db(transaction=True)


def _uniq(prefix: str) -> str:
    return f'{prefix}{uuid.uuid4().hex[:10]}'


# ---------------------------------------------------------------------------
# campus_control fixtures / helpers
# ---------------------------------------------------------------------------
@pytest.fixture
def sex_dim(db):
    d = ControlDimension.objects.create(name='性别')
    ControlIndicator.objects.create(dimension=d, name='男')
    ControlIndicator.objects.create(dimension=d, name='女')
    return d


def _mk_control_rule(dim, ind_name='男', **kw):
    ind = ControlIndicator.objects.get(dimension=dim, name=ind_name)
    return ControlRule.objects.create(
        dimension=dim, indicator=ind, year=kw.pop('year', 2026),
        target=kw.pop('target', 1),
        strength=kw.pop('strength', '硬约束'),
        annual_target=kw.pop('annual_target', 0),
        monthly_targets=kw.pop('monthly_targets', [0] * 12),
        **kw,
    )


# ---------------------------------------------------------------------------
# sync_control_rule_to_unified
# ---------------------------------------------------------------------------
def test_sync_control_rule_maps_header_and_action(sex_dim):
    rule = _mk_control_rule(sex_dim, '男', strength='硬约束')
    unified = sync_control_rule_to_unified(rule)

    assert unified.source_app == CAMPUS_CONTROL_SOURCE_APP
    assert unified.legacy_id == rule.id
    assert unified.legacy_model == 'campus_control.ControlRule'
    assert unified.name == rule.code
    assert unified.category == RuleCategory.CONSTRAINT
    assert unified.trigger_type == UnifiedTriggerType.OFFER_SUBMITTED
    assert unified.enabled is True
    assert unified.status == RuleStatus.ENABLED
    assert unified.scope_json == {
        'bu': rule.bu or None, 'position': rule.position or None, 'level': rule.level or None,
    }
    assert unified.conditions.count() == 0  # CONSTRAINT 无结构化条件
    action = unified.actions.first()
    assert action.action_type == UnifiedActionType.BLOCK_HARD
    assert action.params_json['strength'] == '硬约束'


def test_sync_control_rule_soft_constraint_maps_to_block_soft(sex_dim):
    rule = _mk_control_rule(sex_dim, '女', strength='软约束')
    unified = sync_control_rule_to_unified(rule)
    assert unified.actions.first().action_type == UnifiedActionType.BLOCK_SOFT


def test_sync_control_rule_disabled_maps_to_disabled(sex_dim):
    rule = _mk_control_rule(sex_dim, '男', is_active=False)
    unified = sync_control_rule_to_unified(rule)
    assert unified.enabled is False
    assert unified.status == RuleStatus.DISABLED


def test_sync_control_rule_idempotent(sex_dim):
    rule = _mk_control_rule(sex_dim, '男')
    sync_control_rule_to_unified(rule)
    sync_control_rule_to_unified(rule)
    sync_control_rule_to_unified(rule)
    assert Rule.objects.filter(
        source_app=CAMPUS_CONTROL_SOURCE_APP, legacy_id=rule.id,
    ).count() == 1


def test_sync_control_rule_config_carries_domain(sex_dim):
    rule = _mk_control_rule(sex_dim, '男', annual_target=5)
    unified = sync_control_rule_to_unified(rule)
    cfg = unified.config_json
    assert cfg['dimension'] == '性别'
    assert cfg['indicator'] == '男'
    assert cfg['annual_target'] == 5


# ---------------------------------------------------------------------------
# sync_mou_rule_to_unified
# ---------------------------------------------------------------------------
def _mk_mou_rule(**kw):
    defaults = dict(
        name=_uniq('规则'),
        trigger_event='stage-entered',
        conditions=[{'field': 'candidate_id', 'operator': 'IS_NOT_EMPTY', 'value': None}],
        actions={'role': 'HRBP', 'scope': 'all'},
        is_active=True,
    )
    defaults.update(kw)
    return MouRule.objects.create(**defaults)


def test_sync_mou_rule_maps_header_and_action():
    rule = _mk_mou_rule()
    unified = sync_mou_rule_to_unified(rule)

    assert unified.source_app == MOU_SOURCE_APP
    assert unified.legacy_id == rule.id
    assert unified.legacy_model == 'mou.MouRule'
    assert unified.name == rule.name
    assert unified.category == RuleCategory.TCA
    assert unified.trigger_type == UnifiedTriggerType.BUSINESS_EVENT
    assert unified.enabled is True
    assert unified.config_json['event'] == 'stage-entered'
    # conditions 为 list → 重建
    assert unified.conditions.count() == 1
    assert unified.conditions.first().field == 'candidate_id'
    # 动作固定 SET_PERMISSION
    action = unified.actions.first()
    assert action.action_type == UnifiedActionType.SET_PERMISSION
    assert action.params_json['actions'] == {'role': 'HRBP', 'scope': 'all'}


def test_sync_mou_rule_dict_conditions_not_rebuilt_as_conditions():
    # conditions 为 dict 时不应重建 Condition 行（进 config_json）
    rule = _mk_mou_rule(conditions={'field': 'x', 'op': 'EQ'})
    unified = sync_mou_rule_to_unified(rule)
    assert unified.conditions.count() == 0
    assert unified.config_json['conditions'] == {'field': 'x', 'op': 'EQ'}


def test_sync_mou_rule_disabled_maps_to_disabled():
    rule = _mk_mou_rule(is_active=False)
    unified = sync_mou_rule_to_unified(rule)
    assert unified.enabled is False
    assert unified.status == RuleStatus.DISABLED


def test_sync_mou_rule_idempotent():
    rule = _mk_mou_rule()
    sync_mou_rule_to_unified(rule)
    sync_mou_rule_to_unified(rule)
    assert Rule.objects.filter(source_app=MOU_SOURCE_APP, legacy_id=rule.id).count() == 1


# ---------------------------------------------------------------------------
# 双写信号：post_save 镜像 + post_delete 软删传播
# ---------------------------------------------------------------------------
def test_campus_signal_mirrors_on_save_and_soft_deletes_on_delete(sex_dim):
    rule = _mk_control_rule(sex_dim, '男')  # post_save → 镜像
    unified = Rule.objects.get(source_app=CAMPUS_CONTROL_SOURCE_APP, legacy_id=rule.id)
    assert unified.deleted_at is None

    rule.delete()  # post_delete → 软删统一侧
    unified.refresh_from_db()
    assert unified.deleted_at is not None


def test_mou_signal_mirrors_on_save_and_soft_deletes_on_delete():
    rule = _mk_mou_rule()  # post_save → 镜像
    unified = Rule.objects.get(source_app=MOU_SOURCE_APP, legacy_id=rule.id)
    assert unified.deleted_at is None

    rule.delete()  # post_delete → 软删统一侧
    unified.refresh_from_db()
    assert unified.deleted_at is not None


# ---------------------------------------------------------------------------
# 一致性命令：campus_control + mou（MISSING / DRIFT / --fix）
# ---------------------------------------------------------------------------
def test_consistency_campus_and_mou_ok(capsys, sex_dim):
    _mk_control_rule(sex_dim, '男')
    _mk_mou_rule()

    call_command(Command())  # 一致 → 不抛异常
    out = capsys.readouterr().out
    assert '一致' in out


def test_consistency_detects_campus_drift_and_fix(capsys, sex_dim):
    rule = _mk_control_rule(sex_dim, '男')
    unified = Rule.objects.get(source_app=CAMPUS_CONTROL_SOURCE_APP, legacy_id=rule.id)
    unified.name = '篡改'
    unified.save()

    with pytest.raises(SystemExit) as exc:
        call_command(Command())
    assert exc.value.code == 1
    assert 'DRIFT' in capsys.readouterr().out

    call_command(Command(), '--fix')
    unified.refresh_from_db()
    assert unified.name == rule.code
    call_command(Command())  # 应一致
    assert '一致' in capsys.readouterr().out


def test_consistency_detects_mou_missing_and_fix(capsys):
    rule = _mk_mou_rule()
    Rule.objects.filter(source_app=MOU_SOURCE_APP, legacy_id=rule.id).delete()  # 制造 MISSING

    with pytest.raises(SystemExit) as exc:
        call_command(Command())
    assert exc.value.code == 1
    assert 'MISSING' in capsys.readouterr().out

    call_command(Command(), '--fix')
    assert Rule.objects.filter(
        source_app=MOU_SOURCE_APP, legacy_id=rule.id,
    ).exists()


# ---------------------------------------------------------------------------
# 执行器注册
# ---------------------------------------------------------------------------
def test_executors_registered():
    cv = ConstraintValidator()
    assert cv.supports(UnifiedActionType.BLOCK_HARD)
    assert cv.supports(UnifiedActionType.BLOCK_SOFT)
    assert not cv.supports(UnifiedActionType.SET_PERMISSION)

    mp = MouPermissionExecutor()
    assert mp.supports(UnifiedActionType.SET_PERMISSION)
    assert not mp.supports(UnifiedActionType.BLOCK_HARD)


# ---------------------------------------------------------------------------
# campus Offer 校验事件 → RuleExecutionLog（best-effort）
# ---------------------------------------------------------------------------
def test_mirror_campus_offer_validation_writes_logs(sex_dim):
    rule = _mk_control_rule(sex_dim, '男', strength='硬约束')
    sync_control_rule_to_unified(rule)  # 先有统一镜像可供 FK 反查

    written = mirror_campus_offer_validation(
        candidate_id='cand-1',
        blocks=[{
            'rule_id': rule.id, 'strength': '硬约束', 'code': rule.code,
            'dimension': '性别', 'indicator': '男',
        }],
        warnings=[{
            'rule_id': rule.id, 'strength': '软约束', 'code': rule.code,
            'dimension': '性别', 'indicator': '女',
        }],
    )
    assert written == 2
    logs = RuleExecutionLog.objects.filter(
        rule__source_app=CAMPUS_CONTROL_SOURCE_APP, candidate_id='cand-1',
    )
    assert logs.count() == 2
    assert logs.filter(evaluate_result=EvaluateResult.BLOCKED).exists()
    assert logs.filter(evaluate_result=EvaluateResult.REJECTED).exists()


# ---------------------------------------------------------------------------
# MouRule 重命名数据完整性：物理表名保持 mou_automation_rules
# ---------------------------------------------------------------------------
def test_mou_rename_preserves_db_table():
    assert MouRule._meta.db_table == 'mou_automation_rules'
    rule = _mk_mou_rule()
    # 直接查物理表确认行可落库（迁移未改表名）
    from django.db import connection
    with connection.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM mou_automation_rules WHERE id = %s", [rule.id]
        )
        assert cur.fetchone()[0] == 1


# ---------------------------------------------------------------------------
# sync_automation_rule_to_unified — condition_json 兼容性
# ---------------------------------------------------------------------------
def _mk_automation_rule(condition_json):
    """建 AutomationRule 不走完整 signals → 直接 ORM.create 避免拉太多外键。"""
    import uuid as _uuid
    from apps.process.models import RecruitmentProcess, RecruitmentStage
    rid = _uuid.uuid4().hex[:12]
    # process / stage 是 FK NOT NULL，用最小集合 placeholder 行
    proc = RecruitmentProcess.objects.create(
        id=f'rp_{rid}', code=f'TEST_{rid}', name='tproc',
        applicable_scope={}, is_template=False, status='ENABLED',
    )
    stage = RecruitmentStage.objects.create(
        id=f'st_{rid}', code=f'T{rid}', name='tstg',
        stage_type='SCREEN', status='ENABLED',
    )
    return AutomationRule.objects.create(
        id=f'ar_{rid}',
        name=f'测试规则_{rid}',
        process=proc,
        stage=stage,
        trigger_type='STAGE_ENTERED',
        trigger_timing='IMMEDIATE',
        action_type='AUTO_ADVANCE',
        priority='P1',
        enabled=True,
        condition_json=condition_json,
    )


def test_sync_automation_rule_string_condition_goes_to_meta():
    """[P0 回归] condition_json=['stage.state == PROCESSING']（load_process_templates
    包成的 list[str]）必须不再抛 AttributeError；expression 整体塞到 meta_json。

    历史 bug: bridge.sync_automation_rule_to_unified 把每条 cond 当 dict 处理
    (cond.get('field',''))，遇到 str → 'str' object has no attribute 'get'。
    """
    rule = _mk_automation_rule(['stage.state == PROCESSING'])
    unified = sync_automation_rule_to_unified(rule)

    assert unified.source_app == AUTOMATION_SOURCE_APP
    assert unified.legacy_id == rule.id
    cond = unified.conditions.first()
    assert cond is not None
    assert cond.seq == 1
    assert cond.field == ''  # expression 串场景: field 留空
    assert cond.operator == 'EQ'  # 默认
    assert cond.meta_json.get('expression') == 'stage.state == PROCESSING'
    assert cond.meta_json.get('legacy_format') == 'string'


def test_sync_automation_rule_dict_condition_still_works():
    """[回归] dict 形态仍走原路径(field/operator/value 三元组)"""
    rule = _mk_automation_rule([{'field': 'evaluation.score', 'operator': 'GTE', 'value': 60}])
    unified = sync_automation_rule_to_unified(rule)

    cond = unified.conditions.first()
    assert cond is not None
    assert cond.field == 'evaluation.score'
    assert cond.operator == 'GTE'
    assert cond.value == 60
    assert cond.meta_json == {}


def test_sync_automation_rule_mixed_conditions_skips_invalid_gracefully():
    """[防御] 混合 list 里出现非 dict/str 元素（如 None/int）— 跳过并 warning，不抛"""
    rule = _mk_automation_rule([
        {'field': 'x', 'operator': 'EQ', 'value': 1},
        None,            # idx=1 → 跳过
        42,              # idx=2 → 跳过
        'pure_expression',  # idx=3 → seq=4
    ])
    unified = sync_automation_rule_to_unified(rule)
    assert unified.conditions.count() == 2  # dict (seq=1) + str (seq=4)
    seq_to_meta = {c.seq: c.meta_json for c in unified.conditions.all()}
    assert 1 in seq_to_meta and 4 in seq_to_meta, f'expected seq 1+4, got {list(seq_to_meta)}'
    assert seq_to_meta[4].get('expression') == 'pure_expression'
