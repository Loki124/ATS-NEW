"""校招管控 v2.4 — 计算引擎与 API 端点测试。

覆盖：
  - 纯函数：count / rule_matches / persons_for_rule / count_rule / denom_rule /
    ratio_of / ratio_status / count_status / compute_ratio / compute_count / kpi /
    simulate / check_dimension_sums（适用范围由规则自带，人数目标承载于规则）
  - §9 断言（基于 §9.0 样例数据）
  - 100% 加和硬校验（序列化器 + API 双路径，按(适用范围, 年度)分组）
  - API 端点（dimensions/indicators/rules+ratio/plan/validate/batch/with-targets/persons）
"""
import pytest
from decimal import Decimal

from ..sample_data import SAMPLE_PERSONS, build_rules
from ..calc import (
    count, rule_matches, persons_for_rule, count_rule, denom_rule,
    ratio_of, ratio_status, count_status,
    compute_ratio, compute_count, kpi, simulate, check_dimension_sums, _scope_key,
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

    def test_count_plan(self):
        rows = compute_count(self.persons, self.rules, 2026, '8月')
        hc = {(_scope_key(c), c['dimension'], c['indicator']): c for c in rows}
        c985 = hc[(('', '', ''), '院校标签', '985')]
        assert c985['onjob'] == _cnt(self.persons, school='985')
        assert c985['annualTarget'] == 40

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
        dim, i_m, i_f = self._mk_dim_ind(hr_user)
        ControlRule.objects.create(
            bu='能电BG', dimension=dim, indicator=i_m,
            target=Decimal('0.6'), strength='硬约束',
            created_by=hr_user, updated_by=hr_user,
        )
        ser = ControlRuleSerializer(data={
            'bu': '能电BG', 'dimension': dim.id, 'indicator': i_f.id,
            'target': 0.5, 'strength': '软约束',
        })
        assert not ser.is_valid()
        assert any('100%' in str(v) for vals in ser.errors.values() for v in (vals if isinstance(vals, list) else [vals]))


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
        assert all(s['ok'] for s in data['sumChecks'])

    def test_plan_endpoint(self, api_client):
        self._build_minimal_scheme(api_client)
        resp = api_client.get('/api/v1/campus/rules/plan/?bu=能电BG&year=2026&month=8月')
        assert resp.status_code == 200, resp.json()
        assert resp.json()['data']['rows']

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
        d = api_client.post('/api/v1/campus/dimensions/', {'name': '性别'}, format='json').json()
        dim_id = d['id']
        im = api_client.post('/api/v1/campus/indicators/', {'dimension': dim_id, 'name': '男'}, format='json').json()
        ifm = api_client.post('/api/v1/campus/indicators/', {'dimension': dim_id, 'name': '女'}, format='json').json()
        r1 = api_client.post('/api/v1/campus/rules/', {'bu': '三到BG', 'dimension': dim_id, 'indicator': im['id'], 'target': 0.6, 'strength': '硬约束'}, format='json')
        assert r1.status_code == 201, r1.json()
        r2 = api_client.post('/api/v1/campus/rules/', {'bu': '三到BG', 'dimension': dim_id, 'indicator': ifm['id'], 'target': 0.5, 'strength': '软约束'}, format='json')
        assert r2.status_code == 400, r2.json()

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
        d = api_client.post('/api/v1/campus/dimensions/', {'name': '性别'}, format='json').json()
        im = api_client.post('/api/v1/campus/indicators/', {'dimension': d['id'], 'name': '男'}, format='json').json()
        api_client.post('/api/v1/campus/indicators/', {'dimension': d['id'], 'name': '女'}, format='json').json()
        resp = api_client.post('/api/v1/campus/rules/batch/', {
            'bu': '能电BG', 'dimension': d['id'],
            'rules': [{'indicator': im['id'], 'target': 0.6, 'strength': '硬约束'}],
        }, format='json')
        assert resp.status_code == 400, resp.json()
        assert '100%' in resp.json()['detail']

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

        # annual_target = round(100 × 0.6) = 60 / round(100 × 0.4) = 40
        annuals = sorted(r['annualTarget'] for r in dim_rules)
        assert annuals == [40, 60]

    def test_with_targets_not_100_blocked(self, api_client):
        """占比加和 ≠ 100% → 400。"""
        dim_id, i1, i2 = self._setup_scheme(api_client)
        resp = api_client.post('/api/v1/campus/rules/with-targets/', {
            'bu': '', 'position': '', 'level': '',
            'dimension': dim_id, 'year': 2026, 'totalTarget': 50,
            'rules': [
                {'indicator': i1, 'target': 0.6, 'strength': '硬约束'},
                {'indicator': i2, 'target': 0.5, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp.status_code == 400
        assert '100%' in resp.json().get('detail', '')

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
        dim_id, i1, i2, bu, pos, lvl, year = self._setup_scheme(api_client)
        resp = api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': bu, 'position': pos, 'level': lvl, 'year': year,
            'rules': [{'indicator': i1, 'target': 0.6, 'strength': '硬约束'}],
        }, format='json')
        assert resp.status_code == 400
        assert '100%' in resp.json().get('detail', '')

    def test_set_rules_above_100_blocked(self, api_client):
        dim_id, i1, i2, bu, pos, lvl, year = self._setup_scheme(api_client)
        resp = api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': bu, 'position': pos, 'level': lvl, 'year': year,
            'rules': [
                {'indicator': i1, 'target': 0.7, 'strength': '硬约束'},
                {'indicator': i2, 'target': 0.5, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp.status_code == 400
        assert '100%' in resp.json().get('detail', '')

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
        """重平衡占比时，既有年度/月度人数目标应被继承而非清空。"""
        dim_id, i1, i2, bu, pos, lvl, year = self._setup_scheme(api_client)
        # 先创建带人数目标的旧规则（仅 i1，target=0.6 ≤100% 合法）
        old = api_client.post('/api/v1/campus/rules/', {
            'bu': bu, 'position': pos, 'level': lvl, 'dimension': dim_id,
            'indicator': i1, 'target': 0.6, 'strength': '硬约束',
            'annual_target': 140, 'monthly_targets': [10] * 12,
        }, format='json')
        assert old.status_code == 201, old.json()

        # 维度规则集编辑面重平衡：i1 0.6→0.55，i2 新增 0.45（和=100%）
        resp = api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': bu, 'position': pos, 'level': lvl, 'year': year,
            'rules': [
                {'indicator': i1, 'target': 0.55, 'strength': '硬约束'},
                {'indicator': i2, 'target': 0.45, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp.status_code == 200, f"got {resp.status_code}: {resp.content!r}"

        rules = api_client.get('/api/v1/campus/rules/', {'params': {'page_size': 200}}).json()['data']
        dim_rules = [r for r in rules if r['dimension'] == dim_id]
        assert len(dim_rules) == 2  # 原子替换
        i1_rule = next(r for r in dim_rules if r['indicator'] == i1)
        # 人数目标应继承旧值
        assert i1_rule['annualTarget'] == 140
        assert i1_rule['monthlyTargets'] == [10] * 12
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

    def test_set_rules_relocate_conflict_blocked(self, api_client):
        """重定位目标 scope 已存在规则集 → 400 拦截（避免覆盖），原 scope 不动。"""
        dim_id, i1, i2, _, _, _, year = self._setup_scheme(api_client)
        # 全局 scope 建规则集
        api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': '', 'position': '', 'level': '', 'year': year,
            'rules': [
                {'indicator': i1, 'target': 0.6, 'strength': '硬约束'},
                {'indicator': i2, 'target': 0.4, 'strength': '软约束'},
            ],
        }, format='json')
        # 能电BG scope 也已存在规则集
        api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': '能电BG', 'position': '', 'level': '', 'year': year,
            'rules': [
                {'indicator': i1, 'target': 0.6, 'strength': '硬约束'},
                {'indicator': i2, 'target': 0.4, 'strength': '软约束'},
            ],
        }, format='json')
        # 试图从全局重定位到能电BG（已存在）→ 拦截
        resp = api_client.put(f'/api/v1/campus/dimensions/{dim_id}/rules/', {
            'bu': '能电BG', 'position': '', 'level': '', 'year': year,
            'original': {'bu': '', 'position': '', 'level': '', 'year': year},
            'rules': [
                {'indicator': i1, 'target': 0.6, 'strength': '硬约束'},
                {'indicator': i2, 'target': 0.4, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp.status_code == 400
        assert '已存在' in resp.json().get('detail', '')
        # 原全局 scope 与能电BG scope 规则均应仍在（未被删）
        rules = api_client.get('/api/v1/campus/rules/', {'params': {'page_size': 200}}).json()['data']
        dim_rules = [r for r in rules if r['dimension'] == dim_id]
        assert len(dim_rules) == 4
