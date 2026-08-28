"""配置规则列表页（T01/T02/T03）后端单测。

覆盖：
  - code 自动补号（save() 事务内 select_for_update 防重，风险4）
  - 唯一含状态（is_active 纳入唯一键；启用冲突 409，副本可共存）
  - 复制生成未启用副本；源已未启用再复制 -> IntegrityError（视图层转 409）
  - 停用后 Offer 钩子不命中（风险：实时查 is_active=True）
  - Offer 钩子硬约束阻断 / 软约束放行（决策②：仅 strength 驱动）
  - 月度判定 + count 复用 calc.py 口径（风险2：禁止另写计数）
  - 维度命中：性别 + 院校标签 + 专业标签 全维度（决策①）
  - bu 对齐：position.department.name 须与 DEPTS 对齐
  - 迁移回填 RunPython 真实数据不炸（项目铁律）
"""
from datetime import date
from decimal import Decimal

import importlib
import pytest
from django.apps import apps as django_apps
from django.db import IntegrityError

from apps.campus_control.models import (
    ControlDimension, ControlIndicator, ControlRule, Person,
)
from apps.campus_control.services import (
    ControlRuleViolation, copy_rule, toggle_rule, validate_offer_against_rules,
    validate_rule_unique,
)

# 模块级 transaction=True：本文件测试大量使用 save() 内 select_for_update 自动补号，
# 在 SQLite :memory: + db fixture 的 savepoint 模式下会逃逸回滚导致数据跨测试残留。
# 改用事务模式（flush 隔离）保证每个测试从干净库开始，编号确定性可断言。
pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def sex_dim(db):
    d = ControlDimension.objects.create(name='性别')
    ControlIndicator.objects.create(dimension=d, name='男')
    ControlIndicator.objects.create(dimension=d, name='女')
    return d


@pytest.fixture
def school_dim(db):
    d = ControlDimension.objects.create(name='院校标签')
    for name in ('985', '211', '双一流', '其他'):
        ControlIndicator.objects.create(dimension=d, name=name)
    return d


@pytest.fixture
def major_dim(db):
    d = ControlDimension.objects.create(name='专业标签')
    for name in ('工学', '其他'):
        ControlIndicator.objects.create(dimension=d, name=name)
    return d


def _mk_rule(dim, ind_name, **kw):
    ind = ControlIndicator.objects.get(dimension=dim, name=ind_name)
    year = kw.pop('year', 2026)
    return ControlRule.objects.create(
        dimension=dim, indicator=ind, year=year,
        target=kw.pop('target', Decimal('1')),
        strength=kw.pop('strength', '硬约束'),
        annual_target=kw.pop('annual_target', 0),
        monthly_targets=kw.pop('monthly_targets', [0] * 12),
        **kw,
    )


# ---- T01：code 自动补号 ----
def test_code_auto_numbering(sex_dim):
    r1 = _mk_rule(sex_dim, '男')
    r2 = _mk_rule(sex_dim, '女')
    r3 = _mk_rule(sex_dim, '男', bu='能电BG')
    assert r1.code == 'G0001'
    assert r2.code == 'G0002'
    assert r3.code == 'G0003'
    # 唯一
    assert len({r1.code, r2.code, r3.code}) == 3


def test_code_unique_conflict_raises(sex_dim):
    r = _mk_rule(sex_dim, '男')
    dup = ControlRule(
        dimension=sex_dim, indicator=ControlIndicator.objects.get(dimension=sex_dim, name='女'),
        year=2026, code=r.code,
    )
    with pytest.raises(IntegrityError):
        dup.save()


# ---- T02：唯一含状态（启用冲突 409 / 副本共存） ----
def test_unique_with_is_active_allows_active_plus_inactive(sex_dim):
    _mk_rule(sex_dim, '男', bu='能电BG', is_active=True)
    # 同键未启用副本可共存
    copy = copy_rule(ControlRule.objects.get(bu='能电BG', indicator__name='男', is_active=True))
    assert copy.is_active is False
    assert copy.code != 'G0001'
    # 两条同键（一启用一未启用）不冲突
    assert ControlRule.objects.filter(bu='能电BG', indicator__name='男').count() == 2


def test_two_active_same_key_conflict(sex_dim):
    _mk_rule(sex_dim, '男', bu='能电BG', is_active=True)
    with pytest.raises(IntegrityError):
        _mk_rule(sex_dim, '男', bu='能电BG', is_active=True)


def test_copy_of_inactive_raises_integrity(sex_dim):
    src = _mk_rule(sex_dim, '男', bu='能电BG', is_active=False)
    # 已存在未启用副本（src 本身）-> 再复制撞唯一键
    with pytest.raises(IntegrityError):
        copy_rule(src)


# ---- T02-补充：DRF UniqueTogetherValidator 文案已改写为业务友好 ----
def test_unique_together_validator_friendly_message(sex_dim):
    """DRF ModelSerializer 会从 model.Meta.unique_together 自动注入
    UniqueTogetherValidator，默认 message 是「字段 X...必须能构成唯一集合。」，
    对用户不友好。我们已通过 ControlRuleSerializer.get_validators 把它替换为
    业务友好文案。本测试固定这条契约：未来若回归到默认文案会被 CI 拦截。
    """
    from ..serializers import ControlRuleSerializer

    ind = ControlIndicator.objects.get(dimension=sex_dim, name='男')

    # 1. 先用 is_active=False 创建一条同名副本（DB 层 unique_together 7 字段
    #    含 is_active，故完全相同 7 键的 is_active=False INSERT 会被 DB 拦；
    #    DRF validator 在 INSERT 前先用 is_valid() 拦下）。
    ControlRule.objects.create(
        dimension=sex_dim, indicator=ind, year=2026,
        bu='能电BG', position='', level='',
        target=Decimal('1.0'), strength='硬约束',
        annual_target=0, monthly_targets=[0] * 12,
        is_active=False,
    )

    # 2. 用户用完全相同的 7 字段再 POST（is_active=False）→ DRF validator
    #    应该立刻拒绝，errors 字典里出现业务友好文案，不再含抽象「必须能构成唯一集合」。
    s = ControlRuleSerializer(data={
        'bu': '能电BG', 'position': '', 'level': '',
        'dimension': sex_dim.id, 'indicator': ind.id,
        'year': 2026, 'target': 1.0, 'strength': '硬约束',
        'is_active': False,
        'annual_target': 0, 'monthly_targets': [0] * 12,
    })
    assert not s.is_valid(), f'期望 is_valid=False（撞唯一键），实得 errors={s.errors}'
    flat = ' '.join(
        item if isinstance(item, str) else ' '.join(map(str, item))
        for v in s.errors.values() for item in (v if isinstance(v, list) else [v])
    )
    assert '必须能构成唯一集合' not in flat, (
        f'regression: DRF UniqueTogetherValidator 仍吐默认文案，flat={flat!r}'
    )
    assert '同名规则副本' in flat, (
        f'覆盖后的业务文案未生效（应含「同名规则副本」），flat={flat!r}'
    )


def test_toggle_enable_conflict_409(sex_dim):
    _mk_rule(sex_dim, '男', bu='能电BG', is_active=True)
    inactive = copy_rule(ControlRule.objects.get(bu='能电BG', indicator__name='男', is_active=True))
    # 启用未启用副本 -> 与启用原规则撞键 -> 409
    with pytest.raises(ControlRuleViolation) as e:
        toggle_rule(inactive, True)
    assert e.value.status_code == 409


def test_toggle_disable_then_enable_ok(sex_dim):
    r = _mk_rule(sex_dim, '男', bu='能电BG', is_active=True)
    toggle_rule(r, False)
    r.refresh_from_db()
    assert r.is_active is False
    toggle_rule(r, True)
    r.refresh_from_db()
    assert r.is_active is True


def test_validate_rule_unique_ratio_exceed(sex_dim):
    # 性别维度两个指标：男 0.6 + 女 0.6 = 1.2 > 1 -> 占比超 400
    _mk_rule(sex_dim, '男', bu='能电BG', is_active=True, target=Decimal('0.6'))
    r_female = ControlRule(
        dimension=sex_dim, indicator=ControlIndicator.objects.get(dimension=sex_dim, name='女'),
        year=2026, bu='能电BG', is_active=True, target=Decimal('0.6'),
    )
    with pytest.raises(ControlRuleViolation) as e:
        validate_rule_unique(r_female)
    assert e.value.status_code == 400


# ---- T03：Offer 钩子 ----
# 钩子仅消费 candidate.gender/school_tag/major_tag 与 position.department.name，
# 用轻量 fake 对象即可，避免 Position 的 hiring_manager/owner/process 等必填 FK 拖累单测。
class _FakeDept:
    def __init__(self, name):
        self.name = name


class _FakePos:
    def __init__(self, name):
        self.department = _FakeDept(name)


class _FakeCand:
    def __init__(self, gender='男', school='985', major='工学'):
        self.gender = gender
        self.school_tag = school
        self.major_tag = major


def test_offer_hook_hard_block(sex_dim):
    _mk_rule(sex_dim, '男', bu='能电BG', annual_target=1, strength='硬约束')
    with pytest.raises(ControlRuleViolation) as e:
        validate_offer_against_rules(
            candidate=_FakeCand(gender='男'), position=_FakePos('能电BG'),
            level='L1', position_title='技术研发', start_date=date(2026, 9, 1),
        )
    assert e.value.status_code == 400
    assert e.value.blocks


def test_offer_hook_soft_warn_passes(sex_dim):
    _mk_rule(sex_dim, '男', bu='能电BG', annual_target=1, strength='软约束')
    res = validate_offer_against_rules(
        candidate=_FakeCand(gender='男'), position=_FakePos('能电BG'),
        level='L1', position_title='技术研发', start_date=date(2026, 9, 1),
    )
    assert res['blocks'] == []
    assert res['warnings']


def test_offer_hook_disabled_not_matched(sex_dim):
    _mk_rule(sex_dim, '男', bu='能电BG', annual_target=1, strength='硬约束', is_active=False)
    # 停用规则不命中 -> 不阻断
    res = validate_offer_against_rules(
        candidate=_FakeCand(gender='男'), position=_FakePos('能电BG'),
        level='L1', position_title='技术研发', start_date=date(2026, 9, 1),
    )
    assert res['blocks'] == []


def test_offer_hook_dim_miss_not_blocked(sex_dim):
    _mk_rule(sex_dim, '男', bu='能电BG', annual_target=1, strength='硬约束')
    res = validate_offer_against_rules(
        candidate=_FakeCand(gender='女'), position=_FakePos('能电BG'),
        level='L1', position_title='技术研发', start_date=date(2026, 9, 1),
    )
    assert res['blocks'] == []


def test_offer_hook_full_dimension_school_major(sex_dim, school_dim, major_dim):
    # 院校标签 + 专业标签 维度各自建规则，全维度命中
    _mk_rule(school_dim, '985', bu='能电BG', annual_target=1, strength='硬约束')
    _mk_rule(major_dim, '工学', bu='能电BG', annual_target=1, strength='硬约束')
    with pytest.raises(ControlRuleViolation) as e:
        validate_offer_against_rules(
            candidate=_FakeCand(gender='男', school='985', major='工学'),
            position=_FakePos('能电BG'), level='L1', position_title='技术研发',
            start_date=date(2026, 9, 1),
        )
    # 命中 2 条（院校 + 专业）
    assert len(e.value.blocks) == 2


def test_offer_hook_month_count(sex_dim):
    # 月度目标 1 人（9 月），start_date 在 9 月 -> 月度命中
    _mk_rule(sex_dim, '男', bu='能电BG', annual_target=0,
             monthly_targets=[0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0], strength='硬约束')
    with pytest.raises(ControlRuleViolation) as e:
        validate_offer_against_rules(
            candidate=_FakeCand(gender='男'), position=_FakePos('能电BG'),
            level='L1', position_title='技术研发', start_date=date(2026, 9, 15),
        )
    assert e.value.blocks[0]['monthTarget'] == 1
    assert e.value.blocks[0]['monthActual'] == 1


def test_offer_hook_bu_mismatch_silent(sex_dim):
    # bu 维度规则设在「三到BG」，offer 在「能电BG」-> 静默不命中（风险3：依赖 department.name 对齐）
    _mk_rule(sex_dim, '男', bu='三到BG', annual_target=1, strength='硬约束')
    res = validate_offer_against_rules(
        candidate=_FakeCand(gender='男'), position=_FakePos('能电BG'),
        level='L1', position_title='技术研发', start_date=date(2026, 9, 1),
    )
    assert res['blocks'] == []


def test_offer_hook_count_reuses_calc(sex_dim):
    # 已有 1 名计入「男」人员 -> 加合成 offer = 2，annual_target=2 触发硬约束（验证复用 count_rule 口径）
    Person.objects.create(
        code='P1', name='现员', bu='能电BG', school='985', sex='男', major='工学',
        month='9月', status='在职', counted=True,
    )
    _mk_rule(sex_dim, '男', bu='能电BG', annual_target=2, strength='硬约束')
    with pytest.raises(ControlRuleViolation) as e:
        validate_offer_against_rules(
            candidate=_FakeCand(gender='男'), position=_FakePos('能电BG'),
            level='L1', position_title='技术研发', start_date=date(2026, 9, 1),
        )
    assert e.value.blocks[0]['annualActual'] == 2


# ---- 迁移回填 RunPython 真实数据不炸（项目铁律） ----
def test_migration_backfill_real_data(sex_dim):
    """RunPython 存量回填真实数据不炸（项目铁律）。

    造真实 ControlRule 数据，将「单行」code 置空（unique 列仅允许一个空串；真实迁移中
    该列先为非唯一再回填，故可多行同时空串），直接调用迁移 0006 的 _backfill_codes
    RunPython，断言空行被补为合法 G 编号、其余保留、整体唯一（不绑定具体序号）。

    注意：造数时显式传 code（绕过 save() 事务内 select_for_update 自动补号），置空用
    queryset.update()（不触发 model.save）。这样全程不触发 select_for_update，规避
    SQLite :memory: 下 select_for_update 可能引发的多连接/陈旧数据问题。

    注意2：本测试对「确定性」做了两层加固：
    (1) 开头清空历史累积行（--reuse-db 跨运行会残留 ControlRule 行）；
    (2) 断言只校验「空行拿到合法 G####、未空行保留、整体唯一」，不绑定 G0001 到具体行——
        因为 ControlIndicator PK 是随机 UUID，_backfill_codes 按 indicator_id 排序后
        男/女先后非确定，空行可能落 G0001 或 G0002，绑定 G0001 会在 ~50% 运行 flaky。
    """
    ControlRule.objects.all().delete()
    ind_m = ControlIndicator.objects.get(dimension=sex_dim, name='男')
    ind_f = ControlIndicator.objects.get(dimension=sex_dim, name='女')
    # 显式 code 绕过自动补号（避免 select_for_update 多连接干扰）
    r1 = ControlRule.objects.create(
        dimension=sex_dim, indicator=ind_m, year=2026, target=Decimal('1'),
        strength='硬约束', annual_target=0, monthly_targets=[0] * 12, code='TMP1',
    )
    r2 = ControlRule.objects.create(
        dimension=sex_dim, indicator=ind_f, year=2026, target=Decimal('1'),
        strength='硬约束', annual_target=0, monthly_targets=[0] * 12, code='TMP2',
    )
    # 仅单行置空（unique 列仅允许一个空串）；真实迁移时列非唯一可多行同时空串
    ControlRule.objects.filter(pk=r1.pk).update(code='')

    mod = importlib.import_module(
        'apps.campus_control.migrations.0006_alter_controlrule_unique_together_controlrule_code_and_more'
    )
    mod._backfill_codes(django_apps, None)

    r1.refresh_from_db()
    r2.refresh_from_db()
    # 空行被补为合法 G 编号；不绑定具体序号（ControlIndicator PK 为随机 UUID，
    # _backfill_codes 按 indicator_id 排序后男/女先后非确定，空行可能落 G0001 或 G0002）
    assert r1.code.startswith('G') and r1.code[1:5].isdigit() and len(r1.code) == 5
    # 未空行保留原 code
    assert r2.code == 'TMP2'
    # 整体唯一
    codes = list(ControlRule.objects.values_list('code', flat=True))
    assert len(set(codes)) == len(codes)
