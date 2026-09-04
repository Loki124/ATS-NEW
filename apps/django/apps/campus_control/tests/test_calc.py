"""校招管控 v2.4 — 计算引擎与 API 端点测试。

覆盖：
  - 纯函数：count / rule_matches / persons_for_rule / count_rule / denom_rule /
    ratio_of / ratio_status / count_status / compute_ratio /
    simulate / check_dimension_sums / _largest_remainder_allocate
    （适用范围由规则自带，人数目标承载于规则；人数规划看板 compute_count/kpi 已在 v2.8 真删）
  - §9 断言（基于 §9.0 样例数据）
  - 100% 加和硬校验（序列化器 + API 双路径，按(适用范围, 年度)分组）
  - API 端点（dimensions/indicators/rules+ratio/validate/batch/with-targets/persons；
    plan 端点已真删 → 404 断言）
"""
import pytest
from decimal import Decimal

from ..sample_data import SAMPLE_PERSONS, build_rules
from ..calc import (
    count, rule_matches, persons_for_rule, count_rule, denom_rule,
    ratio_of, ratio_status, count_status,
    compute_ratio, simulate, check_dimension_sums, _largest_remainder_allocate, _scope_key,
    compute_rollover_target,
)
from ..constants import (
    RATIO_NORMAL, RATIO_ABOVE, COUNT_MET, COUNT_GAP,
    VERDICT_BLOCK, VERDICT_WARN, VERDICT_PASS,
)
from ..models import (
    ControlDimension, ControlIndicator, ControlRule, Person,
)
from ..serializers import ControlRuleSerializer


@pytest.fixture
def hr_user(db):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    u, _ = User.objects.get_or_create(
        username='campus_test_hr',
        defaults={'is_active': True, 'first_name': 'Campus', 'last_name': 'Tester'},
    )
    u.set_password('test123')
    u.save()
    return u


@pytest.fixture
def api_client(hr_user):
    from rest_framework.test import APIClient
    client = APIClient()
    client.force_authenticate(user=hr_user)
    return client


def _cnt(persons, bu=None, sex=None, school=None, major=None):
    n = 0
    for p in persons:
        if bu and p['bu'] != bu:
            continue
        if sex and p['sex'] != sex:
            continue
        if school and p['school'] != school:
            continue
        if major and p['major'] != major:
            continue
        n += 1
    return n


# ============================ 纯函数 ============================
class TestPureCalc:
    def test_count_filters(self):
        persons = [{'bu': '能电BG', 'school': '985'}, {'bu': '能电BG', 'school': '211'}, {'bu': '三到BG', 'school': '985'}]
        assert count(persons, {'bu': '能电BG'}) == 2
        assert count(persons, {'bu': '能电BG', 'school': '985'}) == 1
        assert count(persons, {'school': '985'}) == 2

    def test_rule_matches_scope(self):
        rule = {'bu': '', 'position': '', 'level': ''}
        assert rule_matches({'bu': '能电BG', 'position': '', 'level': ''}, rule)
        rule_bu = {'bu': '能电BG', 'position': '', 'level': ''}
        assert rule_matches({'bu': '能电BG'}, rule_bu)
        assert not rule_matches({'bu': '三到BG'}, rule_bu)
        rule_pos = {'bu': '能电BG', 'position': '技术研发', 'level': ''}
        assert rule_matches({'bu': '能电BG', 'position': '技术研发'}, rule_pos)
        assert not rule_matches({'bu': '能电BG', 'position': ''}, rule_pos)

    def test_denom_rule_is_scope_count(self):
        persons = [
            {'bu': '能电BG', 'sex': '男', 'counted': True, 'status': '在职'},
            {'bu': '能电BG', 'sex': '女', 'counted': True, 'status': '在职'},
            {'bu': '三到BG', 'sex': '男', 'counted': True, 'status': '在职'},
        ]
        rule_bu = {'bu': '能电BG', 'position': '', 'level': '', 'dimension': '性别', 'indicator': '男'}
        assert denom_rule(rule_bu, persons) == 2
        rule_global = {'bu': '', 'position': '', 'level': '', 'dimension': '性别', 'indicator': '男'}
        assert denom_rule(rule_global, persons) == 3

    def test_ratio_of_zero_denom_returns_zero(self):
        rule = {'bu': 'X', 'position': '', 'level': '', 'dimension': '性别', 'indicator': '男'}
        assert ratio_of(rule, []) == Decimal('0')

    def test_ratio_status_ceiling(self):
        # v2.4：以 target 为管控上限，超过 target+TOL 即「高于上限」
        rule = {'target': Decimal('0.3')}
        assert ratio_status(Decimal('0.5'), rule) == RATIO_ABOVE
        assert ratio_status(Decimal('0.301'), rule) == RATIO_ABOVE
        assert ratio_status(Decimal('0.3'), rule) == RATIO_NORMAL
        assert ratio_status(Decimal('0.1'), rule) == RATIO_NORMAL

    def test_count_status(self):
        assert count_status(10, 10) == COUNT_MET
        assert count_status(9, 10) == COUNT_GAP
        assert count_status(5, None) == '未设目标'


# ============================ v2.10：本月浮动目标（roll-over）纯函数测试 ============================
class TestComputeRolloverTarget:
    """覆盖设计文档 §7 T01 / PRD §3.3 全部边界：

      - Q-A10 零回归（rollover_enabled=False → (0,0,0,0)）
      - Q-A5 跨年防御（rule.year != today.year → (0,0,0,0)）
      - Q-A4 curMonth 越界（today.month ∉ [1,12] → (0,0,0,0)）
      - B8 无过去月份（curMonth=1 → rollBase=0）
      - Q3-A 浮动基数 = Σ monthly_targets[0..curMonth-2]
      - Q4-A / Q5-A rollActual = 仅「在职」且 actual_entry_date ∈ [本年 1/1, curMonth-1 月末]
      - Q6-B 负数裁 0（rollBase < rollActual → rollover=0）
    """

    def _rule(self, **kw):
        base = {
            'bu': '能电BG', 'position': '', 'level': '',
            'dimension': '性别', 'indicator': '男',
            'year': 2026, 'target': 1.0, 'strength': '硬约束',
            'annual_target': 0,
            'monthly_targets': [0] * 12,
            'rollover_enabled': False,
        }
        base.update(kw)
        return base

    def test_rollover_disabled_returns_zeros(self):
        """Q-A10 零回归：rollover_enabled=False → (0,0,0,0)。"""
        from datetime import date
        rule = self._rule(rollover_enabled=False, monthly_targets=[10] * 12)
        persons = [
            {'bu': '能电BG', 'sex': '男', 'counted': True, 'status': '在职',
             'actual_entry_date': '2026-03-15', 'expected_entry_date': None,
             'month': '3月'},
        ]
        result = compute_rollover_target(rule, persons, today=date(2026, 9, 15))
        assert result == (0, 0, 0, 0), f'rollover_enabled=False 应恒返 0 元组，实得 {result}'

    def test_cross_year_rule_returns_zero(self):
        """Q-A5 跨年：rule.year=2025, today.year=2026 → (0,0,0,0)。"""
        from datetime import date
        rule = self._rule(rollover_enabled=True, year=2025, monthly_targets=[10] * 12)
        result = compute_rollover_target(rule, [], today=date(2026, 9, 15))
        assert result == (0, 0, 0, 0), f'跨年防御失败，实得 {result}'

    def test_cur_month_out_of_range_returns_zeros(self):
        """Q-A4 越界：today.month=13 → (0,0,0,0)。"""
        from datetime import date
        rule = self._rule(rollover_enabled=True, monthly_targets=[10] * 12)
        result = compute_rollover_target(rule, [], today=date(2026, 13, 1))
        assert result == (0, 0, 0, 0), f'curMonth 越界防御失败，实得 {result}'

    def test_cur_month_1_returns_zeros(self):
        """B8：无过去月份（curMonth=1）→ rollBase=0, monthRollover=0。"""
        from datetime import date
        rule = self._rule(rollover_enabled=True, monthly_targets=[10] * 12)
        result = compute_rollover_target(rule, [], today=date(2026, 1, 15))
        # 1月无过去月份 → rollBase=0, rollActual=0, rollover=0, monthRollover=0
        assert result == (0, 0, 0, 0), f'B8 边界应返 (0,0,0,0)，实得 {result}'

    def test_roll_base_equals_sum_of_past_months(self):
        """Q3-A：curMonth=9 → rollBase = Σ monthly_targets[0..6]（即 1..7月）。"""
        from datetime import date
        monthly = [10, 12, 8, 15, 6, 11, 9, 7, 5, 4, 3, 2]
        rule = self._rule(rollover_enabled=True, monthly_targets=monthly)
        # 无在职人员 → rollActual=0, rollover = rollBase - 0
        # Σ[0..6] = 10+12+8+15+6+11+9 = 71
        result = compute_rollover_target(rule, [], today=date(2026, 9, 1))
        assert result[0] == 71, f'rollBase 应为 71，实得 {result[0]}'
        assert result[1] == 0, f'rollActual 应为 0，实得 {result[1]}'
        assert result[2] == 71, f'rollover 应为 71，实得 {result[2]}'
        assert result[3] == 71, f'monthRollover 应为 71（开启），实得 {result[3]}'

    def test_roll_actual_only_counts_in_service_with_past_actual_entry(self):
        """Q4-A / Q5-A：仅「在职」且 actual_entry_date ∈ [本年 1/1, curMonth-1 月末]。

        测试场景（curMonth=9, 即 [2026-01-01, 2026-08-31]）：
          ✓ 在职 + 2026-03-15 入职 → 计入
          ✗ 在职 + 2026-09-01 入职（curMonth 当月）→ 不计入
          ✗ 在职 + 2025-12-31 入职（去年）→ 不计入
          ✗ 在途Offer + 2026-05-01（status≠在职）→ 不计入
          ✗ 在职 + 2026-06-01 但 bu='三到BG'（rule bu=能电BG，rule_matches 失败）→ 不计入
          ✗ 在职 + 2026-04-01 但 sex='女'（indicator 命中失败）→ 不计入
        期望 rollActual = 1。
        """
        from datetime import date
        rule = self._rule(rollover_enabled=True, monthly_targets=[10] * 12)
        persons = [
            {'bu': '能电BG', 'sex': '男', 'counted': True, 'status': '在职',
             'actual_entry_date': '2026-03-15', 'expected_entry_date': None,
             'month': '3月'},
            {'bu': '能电BG', 'sex': '男', 'counted': True, 'status': '在职',
             'actual_entry_date': '2026-09-01', 'expected_entry_date': None,
             'month': '9月'},
            {'bu': '能电BG', 'sex': '男', 'counted': True, 'status': '在职',
             'actual_entry_date': '2025-12-31', 'expected_entry_date': None,
             'month': '12月'},
            {'bu': '能电BG', 'sex': '男', 'counted': True, 'status': '在途Offer',
             'actual_entry_date': None, 'expected_entry_date': '2026-05-01',
             'month': '5月'},
            {'bu': '三到BG', 'sex': '男', 'counted': True, 'status': '在职',
             'actual_entry_date': '2026-06-01', 'expected_entry_date': None,
             'month': '6月'},
            {'bu': '能电BG', 'sex': '女', 'counted': True, 'status': '在职',
             'actual_entry_date': '2026-04-01', 'expected_entry_date': None,
             'month': '4月'},
        ]
        result = compute_rollover_target(rule, persons, today=date(2026, 9, 15))
        # rollBase = Σ[10]*7 = 70
        assert result[0] == 70, f'rollBase 应为 70，实得 {result[0]}'
        assert result[1] == 1, f'rollActual 应为 1（仅第 1 条命中），实得 {result[1]}'
        assert result[2] == 69, f'rollover 应为 70-1=69，实得 {result[2]}'

    def test_rollover_negative_clipped_to_zero(self):
        """Q6-B：B5 边界 — rollBase < rollActual → rollover=0（负数裁 0）。"""
        from datetime import date
        rule = self._rule(rollover_enabled=True, monthly_targets=[10] * 12)  # rollBase=70
        persons = [
            # 远超 rollBase 的人数
            *[{
                'bu': '能电BG', 'sex': '男', 'counted': True, 'status': '在职',
                'actual_entry_date': '2026-03-15', 'expected_entry_date': None,
                'month': '3月',
            } for _ in range(100)],
        ]
        result = compute_rollover_target(rule, persons, today=date(2026, 9, 15))
        assert result[0] == 70, f'rollBase 应为 70，实得 {result[0]}'
        assert result[1] == 100, f'rollActual 应为 100，实得 {result[1]}'
        # 70 - 100 = -30 → 裁为 0
        assert result[2] == 0, f'rollover 负数应裁 0，实得 {result[2]}'
        assert result[3] == 0, f'monthRollover 应为 0，实得 {result[3]}'

    def test_roll_actual_skips_unscoped_or_indicator_miss(self):
        """复用 calc.py 谓词的边界：rule_matches 与 _indicator_filter 必须真正生效。"""
        from datetime import date
        rule = self._rule(
            rollover_enabled=True, bu='能电BG',
            monthly_targets=[12] * 12,
        )
        # 三条人员：bu/sex 全部不命中 / 部分不命中
        persons = [
            {'bu': '三到BG', 'sex': '男', 'counted': True, 'status': '在职',
             'actual_entry_date': '2026-05-01', 'expected_entry_date': None,
             'month': '5月'},
            {'bu': '能电BG', 'sex': '女', 'counted': True, 'status': '在职',
             'actual_entry_date': '2026-05-01', 'expected_entry_date': None,
             'month': '5月'},
            {'bu': '能电BG', 'sex': '男', 'counted': True, 'status': '在职',
             'actual_entry_date': '2026-05-01', 'expected_entry_date': None,
             'month': '5月'},  # 唯一命中
        ]
        result = compute_rollover_target(rule, persons, today=date(2026, 9, 15))
        assert result[1] == 1, f'rollActual 应为 1（仅第 3 条命中），实得 {result[1]}'


# ============================ §9 断言（适用范围自带，人数目标在规则上） ============================
class TestPrdAssertions:
    def setup_method(self):
        self.persons = SAMPLE_PERSONS
        self.rules = build_rules(2026)
        self.ratio = compute_ratio(self.persons, self.rules)
        self.rows = {(_scope_key(r), r['dimension'], r['indicator']): r for r in self.ratio['rows']}

    def test_total_population(self):
        assert self.ratio['total'] == 31

    def test_gender_male_ratio_dept(self):
        r = self.rows[(('能电BG', '', ''), '性别', '男')]
        exp = _cnt(self.persons, bu='能电BG', sex='男') / _cnt(self.persons, bu='能电BG')
        assert abs(float(r['ratio']) - exp) < 1e-3
        assert r['status'] == RATIO_ABOVE
        assert r['strength'] == '硬约束'

    def test_school_985_ratio_global(self):
        r = self.rows[(('', '', ''), '院校标签', '985')]
        exp = _cnt(self.persons, school='985') / _cnt(self.persons)
        assert abs(float(r['ratio']) - exp) < 1e-3

    def test_dimension_sums_eq_100(self):
        g = check_dimension_sums(self.rules, ('', '', ''), 2026)
        assert all(s['ok'] for s in g), g
        ne = check_dimension_sums(self.rules, ('能电BG', '', ''), 2026)
        assert all(s['ok'] for s in ne), ne

    def test_simulate_block_when_any_met(self):
        # v2.7：任意规则「本月实际 >= 本月目标」→ 阻断（配额已满，不可再加）。
        # SAMPLE 中 985 人员 status='在职'（在 _COUNTED_STATUSES），计入核算；
        # 加上 tmp（status='在途待入职', school=985）一并计入 → actual = SAMPLE_985 + 1。
        # 自定义 985 规则 monthly=[1]*12 → actual(=SAMPLE_985+1) >= target=1 → MET → 阻断。
        # 占比不再参与 verdict；checks 不含 ratio/ratioStatus/strength。
        custom_rules = [{
            'bu': '', 'position': '', 'level': '',
            'dimension': '院校标签', 'indicator': '985',
            'year': 2026, 'annual_target': 12,
            'monthly_targets': [1] * 12,
        }]
        draft = {'bu': '能电BG', 'school': '985', 'sex': '男', 'major': '工学', 'month': '8月'}
        v = simulate(draft, custom_rules, self.persons, 2026, month='8月')
        assert v['verdict'] == VERDICT_BLOCK, v
        r985 = v['checks'][0]
        assert r985['dimension'] == '院校标签' and r985['indicator'] == '985', r985
        assert r985['countStatus'] == '本月达标' and r985['monthActual'] == _cnt(self.persons, school='985') + 1 and r985['monthTarget'] == 1, r985
        # checks 不再含 ratio / ratioStatus / strength
        for c in v['checks']:
            assert 'ratio' not in c
            assert 'ratioStatus' not in c
            assert 'strength' not in c
            assert {'dimension', 'indicator', 'monthActual', 'monthTarget', 'countStatus'} <= set(c.keys())

    def test_simulate_warn_when_all_gap(self):
        # v2.7：所有命中规则的「本月实际 < 本月目标」→ 警告（未达配额，但允许提交）。
        # 自定义 1 条 985 全局规则、月度目标 50（远高于 SAMPLE 实际人数），必然 GAP。
        custom_rules = [{
            'bu': '', 'position': '', 'level': '',
            'dimension': '院校标签', 'indicator': '985',
            'year': 2026, 'annual_target': 600,
            'monthly_targets': [50] * 12,
        }]
        draft = {'bu': '能电BG', 'school': '985', 'sex': '男', 'major': '工学', 'month': '8月'}
        v = simulate(draft, custom_rules, self.persons, 2026, month='8月')
        assert v['verdict'] == VERDICT_WARN, v
        assert all(c['countStatus'] == '缺口未达成' for c in v['checks']), v


# ============================ 100% 加和硬校验 ============================
@pytest.mark.django_db
class TestSum100Validation:
    def _mk_dim_ind(self, hr_user):
        dim = ControlDimension.objects.create(name='性别', created_by=hr_user, updated_by=hr_user)
        i_m = ControlIndicator.objects.create(dimension=dim, name='男', created_by=hr_user, updated_by=hr_user)
        i_f = ControlIndicator.objects.create(dimension=dim, name='女', created_by=hr_user, updated_by=hr_user)
        return dim, i_m, i_f

    def test_valid_100_sum_ok(self, hr_user):
        dim, i_m, i_f = self._mk_dim_ind(hr_user)
        ser = ControlRuleSerializer(data={
            'bu': '能电BG', 'dimension': dim.id, 'indicator': i_m.id,
            'target': 0.6, 'strength': '硬约束',
        })
        assert ser.is_valid(), ser.errors
        ser.save(created_by=hr_user, updated_by=hr_user)
        ser2 = ControlRuleSerializer(data={
            'bu': '能电BG', 'dimension': dim.id, 'indicator': i_f.id,
            'target': 0.4, 'strength': '软约束',
        })
        assert ser2.is_valid(), ser2.errors  # 0.6 + 0.4 = 100% OK

    def test_per_rule_overflow_blocked(self, hr_user):
        """v2.9 扁平模型：已删除「占比加和不得超过 100%」校验，每条规则 target 可独立设置。

        此处保留测试结构，但语义反转：传 target=0.5 + 已有 target=0.6 都应通过
        （扁平模型下 target 恒为 1.0，前端不再传其他值；后端仅校验 0~1 范围）。
        """
        dim, i_m, i_f = self._mk_dim_ind(hr_user)
        ControlRule.objects.create(
            bu='能电BG', dimension=dim, indicator=i_m,
            target=Decimal('1.0'), strength='硬约束',
            created_by=hr_user, updated_by=hr_user,
        )
        ser = ControlRuleSerializer(data={
            'bu': '能电BG', 'dimension': dim.id, 'indicator': i_f.id,
            'target': 1.0, 'strength': '软约束',
        })
        assert ser.is_valid(), ser.errors
        # 越界值（>1 或 <0）仍被拦截
        ser_bad = ControlRuleSerializer(data={
            'bu': '综合BG', 'dimension': dim.id, 'indicator': i_f.id,
            'target': 1.5, 'strength': '软约束',
        })
        assert not ser_bad.is_valid()
        assert any('0~1' in str(v) or '目标占比' in str(v)
                   for vals in ser_bad.errors.values()
                   for v in (vals if isinstance(vals, list) else [vals]))


# ============================ API 端点 ============================
@pytest.mark.django_db
class TestApiEndpoints:
    def _build_minimal_scheme(self, api_client):
        d = api_client.post('/api/v1/campus/dimensions/', {'name': '性别'}, format='json').json()
        dim_id = d['id']
        im = api_client.post('/api/v1/campus/indicators/', {'dimension': dim_id, 'name': '男'}, format='json').json()
        ifm = api_client.post('/api/v1/campus/indicators/', {'dimension': dim_id, 'name': '女'}, format='json').json()
        api_client.post('/api/v1/campus/rules/', {'bu': '能电BG', 'dimension': dim_id, 'indicator': im['id'], 'target': 0.6, 'strength': '硬约束'}, format='json')
        api_client.post('/api/v1/campus/rules/', {'bu': '能电BG', 'dimension': dim_id, 'indicator': ifm['id'], 'target': 0.4, 'strength': '软约束'}, format='json')
        api_client.post('/api/v1/campus/persons/', {'code': 'A001', 'name': '甲', 'bu': '能电BG', 'school': '985', 'sex': '男', 'major': '工学', 'month': '8月', 'status': '在职', 'counted': True}, format='json')

    def test_ratio_endpoint(self, api_client):
        self._build_minimal_scheme(api_client)
        resp = api_client.get('/api/v1/campus/rules/ratio/?bu=能电BG')
        assert resp.status_code == 200, resp.json()
        data = resp.json()['data']
        male = next(r for r in data['rows'] if r['dimension'] == '性别' and r['indicator'] == '男')
        assert abs(male['ratio'] - 1.0) < 1e-3  # 仅 1 名男性
        assert male['status'] == '高于上限'
        # v2.9 扁平模型：ratio 端点不再返回 sumChecks（每条规则 target 恒 1.0，无「占比之和=100%」语义）。
        assert 'sumChecks' not in data
        # v2.10：默认 rollover_enabled=False → monthRollover=0 且 monthAvailableTarget==monthTarget（v2.4 看板零回归）
        assert male['monthRollover'] == 0
        assert male['monthAvailableTarget'] == male['monthTarget']
        assert 'monthRollBase' in male and 'monthRollActual' in male

    def test_plan_endpoint_gone(self, api_client):
        """v2.8 真删：plan 端点已移除，任何请求应 404。"""
        self._build_minimal_scheme(api_client)
        resp = api_client.get('/api/v1/campus/rules/plan/?bu=能电BG&year=2026&month=8月')
        assert resp.status_code == 404, resp.content

    def test_validate_endpoint_headcount_only(self, api_client):
        # v2.7：录入校验 API 仅按人数判定（不按占比）。
        # 本 scheme 规则未设月度人数目标（monthly_targets 默认全 0），
        # 命中规则均为「未设目标」→ 不阻断、不警告 → 通过。
        self._build_minimal_scheme(api_client)
        resp = api_client.post(
            '/api/v1/campus/rules/validate/?year=2026',
            {'bu': '能电BG', 'school': '211', 'sex': '男', 'major': '工学', 'month': '8月'},
            format='json',
        )
        assert resp.status_code == 200, resp.json()
        data = resp.json()['data']
        assert data['verdict'] == VERDICT_PASS, data
        # checks 不再含 ratio / ratioStatus / strength
        for c in data['checks']:
            assert 'ratio' not in c
            assert 'ratioStatus' not in c
            assert 'strength' not in c

    def test_rule_100_block_via_api(self, api_client):
        """v2.9 扁平模型：单条规则 target=1.0 创建 OK；不再校验「同组占比加和」。

        语义反转：扁平模型下「男」「女」是两条独立规则，target 各自 = 1.0 都通过。
        """
        d = api_client.post('/api/v1/campus/dimensions/', {'name': '性别'}, format='json').json()
        dim_id = d['id']
        im = api_client.post('/api/v1/campus/indicators/', {'dimension': dim_id, 'name': '男'}, format='json').json()
        ifm = api_client.post('/api/v1/campus/indicators/', {'dimension': dim_id, 'name': '女'}, format='json').json()
        r1 = api_client.post('/api/v1/campus/rules/', {'bu': '三到BG', 'dimension': dim_id, 'indicator': im['id'], 'target': 1.0, 'strength': '硬约束'}, format='json')
        assert r1.status_code == 201, r1.json()
        r2 = api_client.post('/api/v1/campus/rules/', {'bu': '三到BG', 'dimension': dim_id, 'indicator': ifm['id'], 'target': 1.0, 'strength': '软约束'}, format='json')
        assert r2.status_code == 201, r2.json()
        # 但同 (bu, dimension, indicator, year) 已存在 → 重复拦截
        r3 = api_client.post('/api/v1/campus/rules/', {'bu': '三到BG', 'dimension': dim_id, 'indicator': im['id'], 'target': 1.0, 'strength': '硬约束'}, format='json')
        assert r3.status_code == 400, r3.json()

    def test_batch_100_ok(self, api_client):
        d = api_client.post('/api/v1/campus/dimensions/', {'name': '性别'}, format='json').json()
        im = api_client.post('/api/v1/campus/indicators/', {'dimension': d['id'], 'name': '男'}, format='json').json()
        ifm = api_client.post('/api/v1/campus/indicators/', {'dimension': d['id'], 'name': '女'}, format='json').json()
        resp = api_client.post('/api/v1/campus/rules/batch/', {
            'bu': '能电BG', 'dimension': d['id'],
            'rules': [
                {'indicator': im['id'], 'target': 0.6, 'strength': '硬约束'},
                {'indicator': ifm['id'], 'target': 0.4, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp.status_code == 200, resp.json()
        assert resp.json()['data']['saved'] == 2

    def test_batch_not_100_blocked(self, api_client):
        """v2.9 扁平模型：set_rules/batch 不再校验「占比加和=100%」，单条规则 target 可独立设置。

        传 target=0.6 应成功（扁平模型下 target 通常 = 1.0，但任意 0~1 都允许）。
        """
        d = api_client.post('/api/v1/campus/dimensions/', {'name': '性别'}, format='json').json()
        im = api_client.post('/api/v1/campus/indicators/', {'dimension': d['id'], 'name': '男'}, format='json').json()
        api_client.post('/api/v1/campus/indicators/', {'dimension': d['id'], 'name': '女'}, format='json').json()
        resp = api_client.post('/api/v1/campus/rules/batch/', {
            'bu': '能电BG', 'dimension': d['id'],
            'rules': [{'indicator': im['id'], 'target': 1.0, 'strength': '硬约束'}],
        }, format='json')
        assert resp.status_code == 200, resp.json()
        assert resp.json()['data']['saved'] == 1
        # 越界 target（>1）应被拦截
        resp_bad = api_client.post('/api/v1/campus/rules/batch/', {
            'bu': '三到BG', 'dimension': d['id'],
            'rules': [{'indicator': im['id'], 'target': 1.5, 'strength': '硬约束'}],
        }, format='json')
        assert resp_bad.status_code == 400, resp_bad.json()

    def test_requires_auth(self):
        from rest_framework.test import APIClient
        client = APIClient()
        resp = client.get('/api/v1/campus/dimensions/')
        assert resp.status_code in (401, 403)


class TestBatchConfigWithTargets:
    """POST /rules/with-targets/ 端点：批量配置规则 + 人数目标（原子写入，目标承载于规则）。

    契约：
    - 占比加和须 == 100%，否则 400
    - indicator 必须属于 dimension，否则 400
    - 年度人数 = round(totalTarget × target)，直接写入规则的 annual_target
    - 事务内：删除该(适用范围, 维度, 年度)旧规则 → 创建新规则（含人数目标）
    """

    def _setup_scheme(self, api_client):
        s = api_client.post('/api/v1/campus/dimensions/', {'name': '测试维度WT'}, format='json')
        assert s.status_code == 201, s.json()
        dim_id = s.json()['id']
        i1 = api_client.post('/api/v1/campus/indicators/', {'dimension': dim_id, 'name': 'A'}, format='json').json()
        i2 = api_client.post('/api/v1/campus/indicators/', {'dimension': dim_id, 'name': 'B'}, format='json').json()
        return dim_id, i1['id'], i2['id']

    def test_with_targets_100_ok(self, api_client):
        """占比加和 = 100% → 规则创建成功且 annual_target = round(totalTarget×target)。"""
        dim_id, i1, i2 = self._setup_scheme(api_client)
        resp = api_client.post('/api/v1/campus/rules/with-targets/', {
            'bu': '', 'position': '', 'level': '',
            'dimension': dim_id, 'year': 2026, 'totalTarget': 100,
            'rules': [
                {'indicator': i1, 'target': 0.6, 'strength': '硬约束'},
                {'indicator': i2, 'target': 0.4, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp.status_code == 200, f"got {resp.status_code}: {resp.content!r}"
        body = resp.json()['data']
        assert body['saved'] == 2
        assert body['totalTarget'] == 100

        # 规则被创建
        rules = api_client.get('/api/v1/campus/rules/', {'params': {'page_size': 200}}).json()['data']
        dim_rules = [r for r in rules if r['dimension'] == dim_id]
        assert len(dim_rules) == 2
        targets = sorted(float(r['target']) for r in dim_rules)
        assert abs(targets[0] - 0.4) < 0.001 and abs(targets[1] - 0.6) < 0.001

        # 最大余数法：totalTarget=100，权重 [0.6,0.4] → exact=[60,40]，无余数 → annual = [60,40]
        annuals = sorted(r['annualTarget'] for r in dim_rules)
        assert annuals == [40, 60]

    def test_with_targets_not_100_blocked(self, api_client):
        """v2.9 扁平模型：with-targets 不再校验「占比加和=100%」，target 越界（>1）才被拦截。

        传 target 1.0 + 1.0 = 200%（旧模型应拦截）→ 现扁平模型通过；target=1.5 越界 → 400。
        """
        dim_id, i1, i2 = self._setup_scheme(api_client)
        # 200% 在扁平模型下合法（每条规则独立 target）
        resp_ok = api_client.post('/api/v1/campus/rules/with-targets/', {
            'bu': '', 'position': '', 'level': '',
            'dimension': dim_id, 'year': 2026, 'totalTarget': 50,
            'rules': [
                {'indicator': i1, 'target': 1.0, 'strength': '硬约束'},
                {'indicator': i2, 'target': 1.0, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp_ok.status_code == 200, resp_ok.json()
        # target 越界 → 400
        resp_bad = api_client.post('/api/v1/campus/rules/with-targets/', {
            'bu': '能电BG', 'position': '', 'level': '',
            'dimension': dim_id, 'year': 2026, 'totalTarget': 50,
            'rules': [
                {'indicator': i1, 'target': 1.5, 'strength': '硬约束'},
            ],
        }, format='json')
        assert resp_bad.status_code == 400, resp_bad.json()

    def test_with_targets_indicator_not_in_dim_blocked(self, api_client):
        """indicator 不属于 dimension → 400。"""
        dim_id, i1, i2 = self._setup_scheme(api_client)
        s2 = api_client.post('/api/v1/campus/dimensions/', {'name': '其他维度WT'}, format='json').json()
        i_other = api_client.post('/api/v1/campus/indicators/', {'dimension': s2['id'], 'name': 'X'}, format='json').json()
        resp = api_client.post('/api/v1/campus/rules/with-targets/', {
            'bu': '', 'position': '', 'level': '',
            'dimension': dim_id, 'year': 2026, 'totalTarget': 100,
            'rules': [
                {'indicator': i1, 'target': 0.5, 'strength': '硬约束'},
                {'indicator': i_other['id'], 'target': 0.5, 'strength': '硬约束'},
            ],
        }, format='json')
        assert resp.status_code == 400
        assert '不属于' in resp.json().get('detail', '')

    def test_with_targets_atomic_replaces_old_rules(self, api_client):
        """事务原子：with-targets 调用后该 (适用范围, 维度, 年度) 下旧规则被替换。"""
        dim_id, i1, i2 = self._setup_scheme(api_client)
        # 先创建旧规则
        api_client.post('/api/v1/campus/rules/', {
            'bu': '', 'dimension': dim_id, 'indicator': i1, 'target': 0.5, 'strength': '硬约束',
        }, format='json')
        # with-targets
        resp = api_client.post('/api/v1/campus/rules/with-targets/', {
            'bu': '', 'position': '', 'level': '',
            'dimension': dim_id, 'year': 2026, 'totalTarget': 200,
            'rules': [
                {'indicator': i1, 'target': 0.7, 'strength': '硬约束'},
                {'indicator': i2, 'target': 0.3, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp.status_code == 200
        # 验证只有 2 条规则（旧被替换）
        rules = api_client.get('/api/v1/campus/rules/', {'params': {'page_size': 200}}).json()['data']
        dim_rules = [r for r in rules if r['dimension'] == dim_id]
        assert len(dim_rules) == 2
        # annual_target = round(200 × 0.7) = 140 / round(200 × 0.3) = 60
        annuals = sorted(r['annualTarget'] for r in dim_rules)
        assert annuals == [60, 140]

    def test_with_targets_largest_remainder_allocation(self, api_client):
        """最大余数法：维度总人数按占比精确分配，Σannual_target == totalTarget（无加和漂移）。

        用 3 指标 + totalTarget=10 + 占比 [0.34, 0.33, 0.33]（和=100%）制造真实余数：
          exact = [3.4, 3.3, 3.3] → floors=[3,3,3] → remainder=1 → 最大余数项(0.4) +1 → [4,3,3]（和=10）。
        """
        dim_id, i1, i2 = self._setup_scheme(api_client)
        i3 = api_client.post('/api/v1/campus/indicators/', {'dimension': dim_id, 'name': 'C'}, format='json').json()['id']
        resp = api_client.post('/api/v1/campus/rules/with-targets/', {
            'bu': '', 'position': '', 'level': '',
            'dimension': dim_id, 'year': 2026, 'totalTarget': 10,
            'rules': [
                {'indicator': i1, 'target': 0.34, 'strength': '硬约束'},
                {'indicator': i2, 'target': 0.33, 'strength': '软约束'},
                {'indicator': i3, 'target': 0.33, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp.status_code == 200, f"got {resp.status_code}: {resp.content!r}"
        assert resp.json()['data']['saved'] == 3
        rules = api_client.get('/api/v1/campus/rules/', {'params': {'page_size': 200}}).json()['data']
        dim_rules = [r for r in rules if r['dimension'] == dim_id]
        annuals = sorted(r['annualTarget'] for r in dim_rules)
        # 最大余数法不变量：加和严格 == totalTarget
        assert sum(annuals) == 10, annuals
        # 余数分配结果：[4, 3, 3]（i1 占比 0.34 余数 0.4 最大，得 +1）
        assert annuals == [3, 3, 4], annuals

    def test_with_targets_total_target_allocation_sum_invariant(self, api_client):
        """不变量回归：任意 totalTarget 下 Σannual_target 恒等于 totalTarget（杜绝 round 漂移）。"""
        dim_id, i1, i2 = self._setup_scheme(api_client)
        for total in (7, 13, 99, 1000):
            resp = api_client.post('/api/v1/campus/rules/with-targets/', {
                'bu': '', 'position': '', 'level': '',
                'dimension': dim_id, 'year': 2026, 'totalTarget': total,
                'rules': [
                    {'indicator': i1, 'target': 0.6, 'strength': '硬约束'},
                    {'indicator': i2, 'target': 0.4, 'strength': '软约束'},
                ],
            }, format='json')
            assert resp.status_code == 200, f"total={total}: {resp.content!r}"
            rules = api_client.get('/api/v1/campus/rules/', {'params': {'page_size': 200}}).json()['data']
            dim_rules = [r for r in rules if r['dimension'] == dim_id]
            assert sum(r['annualTarget'] for r in dim_rules) == total, f"total={total}: {dim_rules}"


class TestDimensionSetRules:
    """PUT /api/v1/campus/dimensions/{id}/rules/ 端点（维度规则集编辑面保存路径）。

    契约：
    - 原子替换该 (适用范围, 维度, 年度) 下全部规则
    - 占比加和须 == 100%，否则 400（与 /rules/batch/ 同源硬校验）
    - indicator 必须属于该维度，否则 400
    - 重复 indicator 提交 → 400
    - **保留既有的年度/月度人数目标**（仅更新 target/strength）
    """

    def _setup_scheme(self, api_client, bu='', position='', level='', year=2026):
        s = api_client.post('/api/v1/campus/dimensions/', {'name': '维度SR'}, format='json')
        assert s.status_code == 201, s.json()
        dim_id = s.json()['id']
        i1 = api_client.post('/api/v1/campus/indicators/', {'dimension': dim_id, 'name': 'A'}, format='json').json()
        i2 = api_client.post('/api/v1/campus/indicators/', {'dimension': dim_id, 'name': 'B'}, format='json').json()
        return dim_id, i1['id'], i2['id'], bu, position, level, year

    def test_set_rules_100_ok(self, api_client):
        dim_id, i1, i2, bu, pos, lvl, year = self._setup_scheme(api_client)
        resp = api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': bu, 'position': pos, 'level': lvl, 'year': year,
            'rules': [
                {'indicator': i1, 'target': 0.6, 'strength': '硬约束'},
                {'indicator': i2, 'target': 0.4, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp.status_code == 200, f"got {resp.status_code}: {resp.content!r}"
        assert resp.json()['data']['saved'] == 2

    def test_set_rules_below_100_blocked(self, api_client):
        """v2.9 扁平模型：set_rules 不再校验「占比加和=100%」，单条规则 target 可独立设置。

        原语义「<100% 应被拦截」反转：扁平模型下 target=0.6 创建 OK（每条独占组合）。
        """
        dim_id, i1, i2, bu, pos, lvl, year = self._setup_scheme(api_client)
        resp = api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': bu, 'position': pos, 'level': lvl, 'year': year,
            'rules': [{'indicator': i1, 'target': 1.0, 'strength': '硬约束'}],
        }, format='json')
        assert resp.status_code == 200, resp.json()
        assert resp.json()['data']['saved'] == 1

    def test_set_rules_above_100_blocked(self, api_client):
        """v2.9 扁平模型：target 越界（>1）才被拦截；200% 在扁平模型下合法（每条独立）。"""
        dim_id, i1, i2, bu, pos, lvl, year = self._setup_scheme(api_client)
        # 200% 扁平模型 OK
        resp_ok = api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': bu, 'position': pos, 'level': lvl, 'year': year,
            'rules': [
                {'indicator': i1, 'target': 1.0, 'strength': '硬约束'},
                {'indicator': i2, 'target': 1.0, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp_ok.status_code == 200, resp_ok.json()
        # target 越界 → 400
        resp_bad = api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': '综合BG', 'position': pos, 'level': lvl, 'year': year,
            'rules': [
                {'indicator': i1, 'target': 1.5, 'strength': '硬约束'},
            ],
        }, format='json')
        assert resp_bad.status_code == 400, resp_bad.json()

    def test_set_rules_duplicate_indicator_blocked(self, api_client):
        dim_id, i1, i2, bu, pos, lvl, year = self._setup_scheme(api_client)
        resp = api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': bu, 'position': pos, 'level': lvl, 'year': year,
            'rules': [
                {'indicator': i1, 'target': 0.6, 'strength': '硬约束'},
                {'indicator': i1, 'target': 0.4, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp.status_code == 400

    def test_set_rules_indicator_not_in_dim_blocked(self, api_client):
        dim_id, i1, i2, bu, pos, lvl, year = self._setup_scheme(api_client)
        s2 = api_client.post('/api/v1/campus/dimensions/', {'name': '其他维度SR'}, format='json').json()
        i_other = api_client.post('/api/v1/campus/indicators/', {'dimension': s2['id'], 'name': 'X'}, format='json').json()
        resp = api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': bu, 'position': pos, 'level': lvl, 'year': year,
            'rules': [
                {'indicator': i1, 'target': 0.5, 'strength': '硬约束'},
                {'indicator': i_other['id'], 'target': 0.5, 'strength': '硬约束'},
            ],
        }, format='json')
        assert resp.status_code == 400
        assert '不属于' in resp.json().get('detail', '')

    def test_set_rules_preserves_headcount(self, api_client):
        """重平衡规则集时，既有年度/月度人数目标应被继承而非清空（v2.9 扁平模型：target=1.0）。"""
        dim_id, i1, i2, bu, pos, lvl, year = self._setup_scheme(api_client)
        # 月度加和 = 140（11*12 + 8 = 140；前 8 月=12，后 4 月=11）
        monthly_140 = [12, 12, 12, 12, 12, 12, 12, 12, 11, 11, 11, 11]
        # 先创建带人数目标的旧规则（仅 i1，target=1.0 扁平模型合法）
        old = api_client.post('/api/v1/campus/rules/', {
            'bu': bu, 'position': pos, 'level': lvl, 'dimension': dim_id,
            'indicator': i1, 'target': 1.0, 'strength': '硬约束',
            'annual_target': 140, 'monthly_targets': monthly_140,
        }, format='json')
        assert old.status_code == 201, old.json()

        # 维度规则集编辑面重平衡：i1 target=1.0 保留，i2 新增 target=1.0
        resp = api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': bu, 'position': pos, 'level': lvl, 'year': year,
            'rules': [
                {'indicator': i1, 'target': 1.0, 'strength': '硬约束'},
                {'indicator': i2, 'target': 1.0, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp.status_code == 200, f"got {resp.status_code}: {resp.content!r}"

        rules = api_client.get('/api/v1/campus/rules/', {'params': {'page_size': 200}}).json()['data']
        dim_rules = [r for r in rules if r['dimension'] == dim_id]
        assert len(dim_rules) == 2  # 原子替换
        i1_rule = next(r for r in dim_rules if r['indicator'] == i1)
        # 人数目标应继承旧值
        assert i1_rule['annualTarget'] == 140
        assert i1_rule['monthlyTargets'] == monthly_140
        # 新指标无旧目标 → 0
        i2_rule = next(r for r in dim_rules if r['indicator'] == i2)
        assert i2_rule['annualTarget'] == 0

    def test_set_rules_atomic_delete_omitted(self, api_client):
        """未出现在 rules 中的指标即视为删除（原子替换语义）。"""
        dim_id, i1, i2, bu, pos, lvl, year = self._setup_scheme(api_client)
        api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': bu, 'position': pos, 'level': lvl, 'year': year,
            'rules': [
                {'indicator': i1, 'target': 0.6, 'strength': '硬约束'},
                {'indicator': i2, 'target': 0.4, 'strength': '软约束'},
            ],
        }, format='json')
        # 仅保留 i1（和=100% 需另一指标，故这里用单指标 1.0 表示「只保留 i1」）
        resp = api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': bu, 'position': pos, 'level': lvl, 'year': year,
            'rules': [{'indicator': i1, 'target': 1.0, 'strength': '硬约束'}],
        }, format='json')
        assert resp.status_code == 200, f"got {resp.status_code}: {resp.content!r}"
        rules = api_client.get('/api/v1/campus/rules/', {'params': {'page_size': 200}}).json()['data']
        dim_rules = [r for r in rules if r['dimension'] == dim_id]
        assert len(dim_rules) == 1
        assert dim_rules[0]['indicator'] == i1

    def test_set_rules_accepts_explicit_annual_and_monthly(self, api_client):
        """前端明确传入 annualTarget+monthlyTargets 时，后端应写入前端传值（而非继承旧值）。"""
        dim_id, i1, i2, bu, pos, lvl, year = self._setup_scheme(api_client)
        # 创建仅 i1（target 1.0）带旧 annual=140, monthly=[10]*12
        api_client.post('/api/v1/campus/rules/', {
            'bu': bu, 'position': pos, 'level': lvl, 'dimension': dim_id,
            'indicator': i1, 'target': 1.0, 'strength': '硬约束',
            'annual_target': 140, 'monthly_targets': [10] * 12,
        }, format='json')
        # 维度规则集：覆盖 i1（annual=24, monthly 加和=24），并加 i2（annual=0）
        new_monthly = [0, 1, 1, 2, 2, 2, 3, 3, 3, 3, 2, 2]  # sum = 24
        resp = api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': bu, 'position': pos, 'level': lvl, 'year': year,
            'rules': [
                {'indicator': i1, 'target': 0.6, 'strength': '硬约束',
                 'annualTarget': 24, 'monthlyTargets': new_monthly},
                {'indicator': i2, 'target': 0.4, 'strength': '软约束',
                 'annualTarget': 16, 'monthlyTargets': [1, 1, 1, 2, 2, 1, 1, 2, 2, 1, 1, 1]},
            ],
        }, format='json')
        assert resp.status_code == 200, f"got {resp.status_code}: {resp.content!r}"

        rules = api_client.get('/api/v1/campus/rules/', {'params': {'page_size': 200}}).json()['data']
        dim_rules = [r for r in rules if r['dimension'] == dim_id]
        i1_rule = next(r for r in dim_rules if r['indicator'] == i1)
        # 用前端传入的值覆盖（旧值 140/10*12 不应生效）
        assert i1_rule['annualTarget'] == 24
        assert i1_rule['monthlyTargets'] == new_monthly
        i2_rule = next(r for r in dim_rules if r['indicator'] == i2)
        assert i2_rule['annualTarget'] == 16

    def test_set_rules_missing_annual_only_blocked(self, api_client):
        """只传 annualTarget 不传 monthlyTargets（成对缺失之一）→ 400。"""
        dim_id, i1, i2, bu, pos, lvl, year = self._setup_scheme(api_client)
        resp = api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': bu, 'position': pos, 'level': lvl, 'year': year,
            'rules': [
                {'indicator': i1, 'target': 0.6, 'strength': '硬约束', 'annualTarget': 24},
                {'indicator': i2, 'target': 0.4, 'strength': '软约束', 'annualTarget': 16,
                 'monthlyTargets': [1] * 12},
            ],
        }, format='json')
        assert resp.status_code == 400
        detail = resp.json().get('detail', '')
        # DRF camel-case renderer 把后端 snake_case 响应转回 camelCase，最终在前端看到 annualTarget
        assert 'annual_target' in detail and 'monthly_targets' in detail
        # 双向都得命中（camelCase 渲染反转）
        assert 'annualTarget' in detail or 'annual_target' in detail
        assert 'monthlyTargets' in detail or 'monthly_targets' in detail

    def test_set_rules_monthly_sum_mismatch_blocked(self, api_client):
        """前端传的 monthly_targets 之和 != annualTarget → 400。"""
        dim_id, i1, i2, bu, pos, lvl, year = self._setup_scheme(api_client)
        resp = api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': bu, 'position': pos, 'level': lvl, 'year': year,
            'rules': [
                {'indicator': i1, 'target': 0.6, 'strength': '硬约束',
                 'annualTarget': 24, 'monthlyTargets': [1] * 12},  # sum=12, !=24
                {'indicator': i2, 'target': 0.4, 'strength': '软约束',
                 'annualTarget': 16, 'monthlyTargets': [1, 1, 1, 2, 2, 1, 1, 2, 2, 1, 1, 1]},
            ],
        }, format='json')
        assert resp.status_code == 400
        detail = resp.json().get('detail', '')
        assert '12 个月度之和' in detail and '24' in detail

    def test_set_rules_relocate_moves_to_new_scope(self, api_client):
        """编辑态改适用范围（重定位）：原 scope 规则集被删，新 scope 重建，无孤儿。"""
        dim_id, i1, i2, _, _, _, year = self._setup_scheme(api_client)  # A = 全局
        # 先在全局 scope 建规则集
        resp = api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': '', 'position': '', 'level': '', 'year': year,
            'rules': [
                {'indicator': i1, 'target': 0.6, 'strength': '硬约束'},
                {'indicator': i2, 'target': 0.4, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp.status_code == 200, resp.content
        # 重定位到 bu='能电BG'（原 scope 通过 original 告知后端）
        resp = api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': '能电BG', 'position': '', 'level': '', 'year': year,
            'original': {'bu': '', 'position': '', 'level': '', 'year': year},
            'rules': [
                {'indicator': i1, 'target': 0.6, 'strength': '硬约束'},
                {'indicator': i2, 'target': 0.4, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp.status_code == 200, f"got {resp.status_code}: {resp.content!r}"
        assert resp.json()['data']['saved'] == 2
        rules = api_client.get('/api/v1/campus/rules/', {'params': {'page_size': 200}}).json()['data']
        dim_rules = [r for r in rules if r['dimension'] == dim_id]
        # 全局 scope 应被清空（孤儿删除），能电BG 应有 2 条
        assert len(dim_rules) == 2
        assert all(r['bu'] == '能电BG' for r in dim_rules)

    def test_set_rules_specific_deletes_global(self, api_client):
        """保存指定范围规则集时，删除该 (dimension, year) 下的全局规则（互斥从拦截改为替换）。

        同一 (dimension, year) 下不可同时存在全局与指定范围。保存指定范围时自动清理全局规则。
        """
        dim_id, i1, i2, _, _, _, year = self._setup_scheme(api_client)
        # 全局 scope 建规则集
        resp = api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': '', 'position': '', 'level': '', 'year': year,
            'rules': [
                {'indicator': i1, 'target': 0.6, 'strength': '硬约束'},
                {'indicator': i2, 'target': 0.4, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp.status_code == 200, resp.content
        # 保存 能电BG 指定范围 → 全局规则应被自动删除
        resp = api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': '能电BG', 'position': '', 'level': '', 'year': year,
            'rules': [
                {'indicator': i1, 'target': 0.7, 'strength': '硬约束'},
                {'indicator': i2, 'target': 0.3, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp.status_code == 200, f"got {resp.status_code}: {resp.content!r}"
        rules = api_client.get('/api/v1/campus/rules/', {'params': {'page_size': 200}}).json()['data']
        dim_rules = [r for r in rules if r['dimension'] == dim_id]
        # 全局已删、能电BG 重建（2 条，新占比）
        assert len(dim_rules) == 2
        assert all(r['bu'] == '能电BG' for r in dim_rules)
        # rules 列表接口的 target 序列化为字符串（如 '0.7000'），断言需转 float
        assert any(float(r['target']) == 0.7 for r in dim_rules), f"targets: {[r['target'] for r in dim_rules]}"

    def test_set_rules_global_blocked_when_specific_exists(self, api_client):
        """保存全局规则集时，若已存在指定范围规则，则拦截（避免静默清空用户指定范围配置）。

        同一 (dimension, year) 下不可同时存在全局与指定范围。保存全局不会自动删除指定范围，
        而是返回 400，由用户显式删除指定范围后再保存全局（其他指定范围无需调整）。
        """
        dim_id, i1, i2, _, _, _, year = self._setup_scheme(api_client)
        # 能电BG 指定范围建规则集
        resp = api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': '能电BG', 'position': '', 'level': '', 'year': year,
            'rules': [
                {'indicator': i1, 'target': 0.6, 'strength': '硬约束'},
                {'indicator': i2, 'target': 0.4, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp.status_code == 200, resp.content
        # 保存全局 → 应被拦截（能电BG 仍存在，不会被静默删除）
        resp = api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': '', 'position': '', 'level': '', 'year': year,
            'rules': [
                {'indicator': i1, 'target': 0.6, 'strength': '硬约束'},
                {'indicator': i2, 'target': 0.4, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp.status_code == 400, f"got {resp.status_code}: {resp.content!r}"
        # 能电BG 仍保留
        rules = api_client.get('/api/v1/campus/rules/', {'params': {'page_size': 200}}).json()['data']
        dim_rules = [r for r in rules if r['dimension'] == dim_id]
        assert len(dim_rules) == 2
        assert all(r['bu'] == '能电BG' for r in dim_rules)

    def test_set_rules_relocate_specific_to_global_allowed(self, api_client):
        """重定位「指定范围 → 全局」时，原始指定范围被同事务删除，故允许（不判冲突）。

        用户把能电BG 规则集改存为全局：原能电BG 消失、全局重建；不应被「全局被拦截」逻辑挡住。
        """
        dim_id, i1, i2, _, _, _, year = self._setup_scheme(api_client)
        # 能电BG 指定范围建规则集
        resp = api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': '能电BG', 'position': '', 'level': '', 'year': year,
            'rules': [
                {'indicator': i1, 'target': 0.6, 'strength': '硬约束'},
                {'indicator': i2, 'target': 0.4, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp.status_code == 200, resp.content
        # 重定位到全局（original 告知后端删原能电BG）→ 应允许
        resp = api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': '', 'position': '', 'level': '', 'year': year,
            'original': {'bu': '能电BG', 'position': '', 'level': '', 'year': year},
            'rules': [
                {'indicator': i1, 'target': 0.6, 'strength': '硬约束'},
                {'indicator': i2, 'target': 0.4, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp.status_code == 200, f"got {resp.status_code}: {resp.content!r}"
        rules = api_client.get('/api/v1/campus/rules/', {'params': {'page_size': 200}}).json()['data']
        dim_rules = [r for r in rules if r['dimension'] == dim_id]
        # 能电BG 已删，全局重建（2 条）
        assert len(dim_rules) == 2
        assert all(r['bu'] == '' for r in dim_rules)

    def test_set_rules_specific_keeps_other_specific(self, api_client):
        """保存指定范围时，其他指定范围不调整（用户确认：无需删除其他指定范围）。

        多个指定范围可以共存于同一 (dimension, year)，互斥仅约束「全局 vs 指定范围」。
        """
        dim_id, i1, i2, _, _, _, year = self._setup_scheme(api_client)
        # 能电BG
        resp = api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': '能电BG', 'position': '', 'level': '', 'year': year,
            'rules': [
                {'indicator': i1, 'target': 0.6, 'strength': '硬约束'},
                {'indicator': i2, 'target': 0.4, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp.status_code == 200, resp.content
        # 校招BU（与能电BG 共存）
        resp = api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': '校招BU', 'position': '', 'level': '', 'year': year,
            'rules': [
                {'indicator': i1, 'target': 0.5, 'strength': '硬约束'},
                {'indicator': i2, 'target': 0.5, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp.status_code == 200, resp.content
        # 更新 能电BG（占比改为 0.7/0.3）→ 校招BU 应保持不变
        resp = api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': '能电BG', 'position': '', 'level': '', 'year': year,
            'rules': [
                {'indicator': i1, 'target': 0.7, 'strength': '硬约束'},
                {'indicator': i2, 'target': 0.3, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp.status_code == 200, f"got {resp.status_code}: {resp.content!r}"
        rules = api_client.get('/api/v1/campus/rules/', {'params': {'page_size': 200}}).json()['data']
        dim_rules = [r for r in rules if r['dimension'] == dim_id]
        # 能电BG 2 条（新占比）+ 校招BU 2 条（原占比）= 4 条
        assert len(dim_rules) == 4
        ndg_rules = [r for r in dim_rules if r['bu'] == '能电BG']
        assert len(ndg_rules) == 2
        assert any(float(r['target']) == 0.7 for r in ndg_rules)
        xz_rules = [r for r in dim_rules if r['bu'] == '校招BU']
        assert len(xz_rules) == 2
        assert any(float(r['target']) == 0.5 for r in xz_rules)

    def test_set_rules_scope_mutex_relocate_global_to_specific_allowed(self, api_client):
        """重定位全局→指定范围（中间无其他 scope 规则集）→ 允许（原全局同事务被删，豁免检查）。"""
        dim_id, i1, i2, _, _, _, year = self._setup_scheme(api_client)
        # 全局 scope 建规则集
        resp = api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': '', 'position': '', 'level': '', 'year': year,
            'rules': [
                {'indicator': i1, 'target': 0.6, 'strength': '硬约束'},
                {'indicator': i2, 'target': 0.4, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp.status_code == 200, resp.content
        # 重定位到能电BG（original 告知后端删原全局）→ 豁免检查，应允许
        resp = api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': '能电BG', 'position': '', 'level': '', 'year': year,
            'original': {'bu': '', 'position': '', 'level': '', 'year': year},
            'rules': [
                {'indicator': i1, 'target': 0.6, 'strength': '硬约束'},
                {'indicator': i2, 'target': 0.4, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp.status_code == 200, f"got {resp.status_code}: {resp.content!r}"
        rules = api_client.get('/api/v1/campus/rules/', {'params': {'page_size': 200}}).json()['data']
        dim_rules = [r for r in rules if r['dimension'] == dim_id]
        # 全局已删、能电BG 重建（2 条）
        assert len(dim_rules) == 2
        assert all(r['bu'] == '能电BG' for r in dim_rules)

    def test_set_rules_relocate_between_specified_scopes_allowed(self, api_client):
        """纯指定范围世界下，重定位一个指定 scope → 另一个指定 scope 应允许，且不破坏其他指定 scope。

        互斥约束仅禁止「全局 + 指定」混合；同为建设指定 scope 之间可自由重定位。
        """
        dim_id, i1, i2, _, _, _, year = self._setup_scheme(api_client)
        # 校招BU 指定范围
        resp = api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': '校招BU', 'position': '', 'level': '', 'year': year,
            'rules': [
                {'indicator': i1, 'target': 0.6, 'strength': '硬约束'},
                {'indicator': i2, 'target': 0.4, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp.status_code == 200, resp.content
        # 能电BG 指定范围（与校招BU 并存不违反互斥）
        resp = api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': '能电BG', 'position': '', 'level': '', 'year': year,
            'rules': [
                {'indicator': i1, 'target': 0.6, 'strength': '硬约束'},
                {'indicator': i2, 'target': 0.4, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp.status_code == 200, resp.content
        # 重定位 校招BU → 新指定范围 Z部门（original=校招BU 豁免）
        resp = api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': 'Z部门', 'position': '', 'level': '', 'year': year,
            'original': {'bu': '校招BU', 'position': '', 'level': '', 'year': year},
            'rules': [
                {'indicator': i1, 'target': 0.6, 'strength': '硬约束'},
                {'indicator': i2, 'target': 0.4, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp.status_code == 200, f"got {resp.status_code}: {resp.content!r}"
        rules = api_client.get('/api/v1/campus/rules/', {'params': {'page_size': 200}}).json()['data']
        dim_rules = [r for r in rules if r['dimension'] == dim_id]
        # 校招BU 已迁走（删除），Z部门 重建 2 条，能电BG 仍在 2 条
        assert len(dim_rules) == 4
        assert any(r['bu'] == 'Z部门' for r in dim_rules)
        assert any(r['bu'] == '能电BG' for r in dim_rules)
        assert not any(r['bu'] == '校招BU' for r in dim_rules)

    def test_set_rules_empty_array_clears(self, api_client):
        """G5 方案 A：rules 为空数组 = 显式清空该 (适用范围, 维度, 年度) 规则集。

        清空分支跳过 100% 校验与互斥守卫，直接删除当前 scope 规则并写审计，返回 cleared=True/saved=0。
        """
        dim_id, i1, i2, bu, pos, lvl, year = self._setup_scheme(api_client)
        # 先建立一套规则
        resp = api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': bu, 'position': pos, 'level': lvl, 'year': year,
            'rules': [
                {'indicator': i1, 'target': 0.6, 'strength': '硬约束'},
                {'indicator': i2, 'target': 0.4, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp.status_code == 200, resp.content
        # 清空
        resp = api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': bu, 'position': pos, 'level': lvl, 'year': year,
            'rules': [],
        }, format='json')
        assert resp.status_code == 200, f"got {resp.status_code}: {resp.content!r}"
        body = resp.json()['data']
        assert body['saved'] == 0
        assert body.get('cleared') is True
        # 该 scope 下规则应被清空
        rules = api_client.get('/api/v1/campus/rules/', {'params': {'page_size': 200}}).json()['data']
        dim_rules = [r for r in rules if r['dimension'] == dim_id]
        assert len(dim_rules) == 0, dim_rules

    def test_set_rules_empty_array_clear_skips_100_check(self, api_client):
        """清空分支即使「占比加和不满足 100%」也不应被拦截（直接删，无需校验）。"""
        dim_id, i1, i2, bu, pos, lvl, year = self._setup_scheme(api_client)
        resp = api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': bu, 'position': pos, 'level': lvl, 'year': year,
            'rules': [],
        }, format='json')
        assert resp.status_code == 200, f"got {resp.status_code}: {resp.content!r}"
        assert resp.json()['data'].get('cleared') is True

    def test_set_rules_annual_sum_must_equal_total_target_blocked(self, api_client):
        """G7-② 硬拦：Σ(各规则 annualTarget) ≠ totalTarget → 400（不允许加和不一致的脏数据入库）。"""
        dim_id, i1, i2, bu, pos, lvl, year = self._setup_scheme(api_client)
        resp = api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': bu, 'position': pos, 'level': lvl, 'year': year,
            'totalTarget': 100,
            'rules': [
                {'indicator': i1, 'target': 0.6, 'strength': '硬约束',
                 'annualTarget': 24, 'monthlyTargets': [2] * 12},  # 月度之和=24=annual ✓
                {'indicator': i2, 'target': 0.4, 'strength': '软约束',
                 'annualTarget': 16, 'monthlyTargets': [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 5]},  # 和=16=annual ✓
            ],
        }, format='json')
        # 100% 校验已通过（0.6+0.4），但 Σannual=40 ≠ 100 → 硬拦
        assert resp.status_code == 400, f"got {resp.status_code}: {resp.content!r}"
        detail = resp.json().get('detail', '')
        assert '维度年度管控人数' in detail
        assert '40' in detail and '100' in detail

    def test_set_rules_annual_sum_equals_total_target_ok(self, api_client):
        """G7-② 正向：Σ(各规则 annualTarget) == totalTarget → 成功落库。"""
        dim_id, i1, i2, bu, pos, lvl, year = self._setup_scheme(api_client)
        resp = api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': bu, 'position': pos, 'level': lvl, 'year': year,
            'totalTarget': 100,
            'rules': [
                {'indicator': i1, 'target': 0.6, 'strength': '硬约束',
                 'annualTarget': 60, 'monthlyTargets': [5] * 12},  # 和=60=annual ✓
                {'indicator': i2, 'target': 0.4, 'strength': '软约束',
                 'annualTarget': 40, 'monthlyTargets': [4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 0, 0]},  # 和=40=annual ✓
            ],
        }, format='json')
        assert resp.status_code == 200, f"got {resp.status_code}: {resp.content!r}"
        assert resp.json()['data']['saved'] == 2
        rules = api_client.get('/api/v1/campus/rules/', {'params': {'page_size': 200}}).json()['data']
        dim_rules = [r for r in rules if r['dimension'] == dim_id]
        assert sum(r['annualTarget'] for r in dim_rules) == 100, dim_rules


class TestImportScopeMutex:
    """导入入口（batch / with-targets / import_xlsx→_import_group）的「全局/指定范围」互斥校验。

    与 set_rules 一致采用非对称策略：
      - 导入【指定范围】→ 删除该 (dimension, year) 下全局规则（其他指定范围保留）
      - 导入【全局】→ 若已存在其他指定范围规则则【拦截 400】，避免静默清空
    （拦截/自动删除的最终取舍待产品次日确认，此处锁定当前行为，便于回归。）
    """

    def _setup_scheme(self, api_client, year=2026):
        s = api_client.post('/api/v1/campus/dimensions/', {'name': '维度IMP'}, format='json')
        assert s.status_code == 201, s.json()
        dim_id = s.json()['id']
        i1 = api_client.post('/api/v1/campus/indicators/', {'dimension': dim_id, 'name': 'A'}, format='json').json()
        i2 = api_client.post('/api/v1/campus/indicators/', {'dimension': dim_id, 'name': 'B'}, format='json').json()
        return dim_id, i1['id'], i2['id'], year

    def _seed_global(self, api_client, dim_id, i1, i2, year=2026):
        resp = api_client.post('/api/v1/campus/rules/batch/', {
            'bu': '', 'position': '', 'level': '', 'dimension': dim_id, 'year': year,
            'rules': [
                {'indicator': i1, 'target': 0.6, 'strength': '硬约束'},
                {'indicator': i2, 'target': 0.4, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp.status_code == 200, resp.content

    def _seed_specific(self, api_client, dim_id, i1, i2, bu='能电BG', year=2026):
        resp = api_client.post('/api/v1/campus/rules/batch/', {
            'bu': bu, 'position': '', 'level': '', 'dimension': dim_id, 'year': year,
            'rules': [
                {'indicator': i1, 'target': 0.6, 'strength': '硬约束'},
                {'indicator': i2, 'target': 0.4, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp.status_code == 200, resp.content

    def _dim_rules(self, api_client, dim_id):
        rules = api_client.get('/api/v1/campus/rules/', {'params': {'page_size': 200}}).json()['data']
        return [r for r in rules if r['dimension'] == dim_id]

    # ---------- batch ----------
    def test_batch_specific_deletes_global(self, api_client):
        """batch 导入指定范围 → 删除该维度年度下全局规则（互斥非对称）。"""
        dim_id, i1, i2, year = self._setup_scheme(api_client)
        self._seed_global(api_client, dim_id, i1, i2, year)
        resp = api_client.post('/api/v1/campus/rules/batch/', {
            'bu': '能电BG', 'position': '', 'level': '', 'dimension': dim_id, 'year': year,
            'rules': [
                {'indicator': i1, 'target': 0.7, 'strength': '硬约束'},
                {'indicator': i2, 'target': 0.3, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp.status_code == 200, f"got {resp.status_code}: {resp.content!r}"
        dim_rules = self._dim_rules(api_client, dim_id)
        assert len(dim_rules) == 2
        assert all(r['bu'] == '能电BG' for r in dim_rules)
        assert any(float(r['target']) == 0.7 for r in dim_rules)

    def test_batch_global_blocked_when_specific_exists(self, api_client):
        """batch 导入全局，但已存在指定范围 → 拦截 400（不静默清空）。"""
        dim_id, i1, i2, year = self._setup_scheme(api_client)
        self._seed_specific(api_client, dim_id, i1, i2, bu='能电BG', year=year)
        resp = api_client.post('/api/v1/campus/rules/batch/', {
            'bu': '', 'position': '', 'level': '', 'dimension': dim_id, 'year': year,
            'rules': [
                {'indicator': i1, 'target': 0.6, 'strength': '硬约束'},
                {'indicator': i2, 'target': 0.4, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp.status_code == 400, f"got {resp.status_code}: {resp.content!r}"
        # 能电BG 仍保留
        dim_rules = self._dim_rules(api_client, dim_id)
        assert all(r['bu'] == '能电BG' for r in dim_rules)

    # ---------- with-targets ----------
    def test_with_targets_specific_deletes_global(self, api_client):
        """with-targets 导入指定范围 → 删除全局规则。"""
        dim_id, i1, i2, year = self._setup_scheme(api_client)
        self._seed_global(api_client, dim_id, i1, i2, year)
        resp = api_client.post('/api/v1/campus/rules/with-targets/', {
            'bu': '能电BG', 'position': '', 'level': '', 'dimension': dim_id, 'year': year,
            'totalTarget': 100,
            'rules': [
                {'indicator': i1, 'target': 0.7, 'strength': '硬约束'},
                {'indicator': i2, 'target': 0.3, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp.status_code == 200, f"got {resp.status_code}: {resp.content!r}"
        dim_rules = self._dim_rules(api_client, dim_id)
        assert len(dim_rules) == 2
        assert all(r['bu'] == '能电BG' for r in dim_rules)

    def test_with_targets_global_blocked_when_specific_exists(self, api_client):
        """with-targets 导入全局，但已存在指定范围 → 拦截 400。"""
        dim_id, i1, i2, year = self._setup_scheme(api_client)
        self._seed_specific(api_client, dim_id, i1, i2, bu='能电BG', year=year)
        resp = api_client.post('/api/v1/campus/rules/with-targets/', {
            'bu': '', 'position': '', 'level': '', 'dimension': dim_id, 'year': year,
            'totalTarget': 100,
            'rules': [
                {'indicator': i1, 'target': 0.6, 'strength': '硬约束'},
                {'indicator': i2, 'target': 0.4, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp.status_code == 400, f"got {resp.status_code}: {resp.content!r}"
        dim_rules = self._dim_rules(api_client, dim_id)
        assert all(r['bu'] == '能电BG' for r in dim_rules)

    # ---------- import_xlsx → _import_group（此前完全无互斥校验） ----------
    def _seed_via_set_rules(self, api_client, dim_id, i1, i2, bu='', year=2026):
        resp = api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': bu, 'position': '', 'level': '', 'year': year,
            'rules': [
                {'indicator': i1, 'target': 0.6, 'strength': '硬约束'},
                {'indicator': i2, 'target': 0.4, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp.status_code == 200, resp.content

    def test_import_group_specific_deletes_global(self, api_client, hr_user):
        """_import_group 导入指定范围 → 删除全局规则（修复静默混合漏洞）。"""
        dim_id, i1, i2, year = self._setup_scheme(api_client)
        self._seed_via_set_rules(api_client, dim_id, i1, i2, bu='', year=year)  # 全局
        from ..views import ControlRuleViewSet
        group = {
            'bu': '能电BG', 'position': '', 'level': '',
            'dimension': '维度IMP', 'year': year,
            'total_target': 100,
            'rules': [
                {'indicator': 'A', 'target': 0.7, 'strength': '硬约束', 'monthly_targets': [1] * 12},
                {'indicator': 'B', 'target': 0.3, 'strength': '软约束', 'monthly_targets': [1] * 12},
            ],
        }
        ok, msg, n = ControlRuleViewSet()._import_group(group, hr_user)
        assert ok is True, msg
        assert n == 2
        dim_rules = self._dim_rules(api_client, dim_id)
        assert len(dim_rules) == 2
        assert all(r['bu'] == '能电BG' for r in dim_rules)

    def test_import_group_global_blocked_when_specific_exists(self, api_client, hr_user):
        """_import_group 导入全局，但已存在指定范围 → 拦截（返回 False + 冲突文案）。"""
        dim_id, i1, i2, year = self._setup_scheme(api_client)
        self._seed_via_set_rules(api_client, dim_id, i1, i2, bu='能电BG', year=year)  # 指定范围
        from ..views import ControlRuleViewSet
        group = {
            'bu': '', 'position': '', 'level': '',
            'dimension': '维度IMP', 'year': year,
            'total_target': 100,
            'rules': [
                {'indicator': 'A', 'target': 0.6, 'strength': '硬约束', 'monthly_targets': [1] * 12},
                {'indicator': 'B', 'target': 0.4, 'strength': '软约束', 'monthly_targets': [1] * 12},
            ],
        }
        ok, msg, n = ControlRuleViewSet()._import_group(group, hr_user)
        assert ok is False, f"应被拦截，但返回 ok={ok}, msg={msg!r}"
        assert '指定范围' in msg
        # 能电BG 仍保留，未被静默清空
        dim_rules = self._dim_rules(api_client, dim_id)
        assert all(r['bu'] == '能电BG' for r in dim_rules)
