"""校招管控 v2.1 — 计算引擎与 API 端点测试。

覆盖：
  - 纯函数：count / rule_matches / persons_for_rule / count_rule / denom_rule /
    ratio_of / ratio_status / count_status / compute_ratio / compute_count / kpi /
    simulate / check_dimension_sums（适用范围由规则自带）
  - §9 断言（基于 §9.0 样例数据）
  - 100% 加和硬校验（序列化器 + API 双路径，按适用范围分组）
  - API 端点（dimensions/indicators/rules+ratio/plan/validate/batch/headcounts/persons）
"""
import pytest
from decimal import Decimal

from ..sample_data import SAMPLE_PERSONS, build_rules, build_headcounts
from ..calc import (
    count, rule_matches, persons_for_rule, count_rule, denom_rule,
    ratio_of, ratio_status, count_status,
    compute_ratio, compute_count, kpi, simulate, check_dimension_sums, _scope_key,
)
from ..constants import (
    RATIO_NORMAL, RATIO_BELOW, RATIO_ABOVE, COUNT_MET, COUNT_GAP,
    VERDICT_BLOCK, VERDICT_WARN, VERDICT_PASS,
)
from ..models import (
    ControlDimension, ControlIndicator, ControlRule, ControlHeadcount, Person,
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
        # 全局规则匹配所有人
        rule = {'bu': '', 'position': '', 'level': ''}
        assert rule_matches({'bu': '能电BG', 'position': '', 'level': ''}, rule)
        # 指定部门
        rule_bu = {'bu': '能电BG', 'position': '', 'level': ''}
        assert rule_matches({'bu': '能电BG'}, rule_bu)
        assert not rule_matches({'bu': '三到BG'}, rule_bu)
        # 指定部门+职务
        rule_pos = {'bu': '能电BG', 'position': '技术研发', 'level': ''}
        assert rule_matches({'bu': '能电BG', 'position': '技术研发'}, rule_pos)
        assert not rule_matches({'bu': '能电BG', 'position': ''}, rule_pos)

    def test_denom_rule_is_scope_count(self):
        persons = [
            {'bu': '能电BG', 'sex': '男', 'counted': True},
            {'bu': '能电BG', 'sex': '女', 'counted': True},
            {'bu': '三到BG', 'sex': '男', 'counted': True},
        ]
        rule_bu = {'bu': '能电BG', 'position': '', 'level': '', 'dimension': '性别', 'indicator': '男'}
        assert denom_rule(rule_bu, persons) == 2  # 能电BG 2 人
        rule_global = {'bu': '', 'position': '', 'level': '', 'dimension': '性别', 'indicator': '男'}
        assert denom_rule(rule_global, persons) == 3  # 全局 3 人

    def test_ratio_of_zero_denom_returns_zero(self):
        rule = {'bu': 'X', 'position': '', 'level': '', 'dimension': '性别', 'indicator': '男'}
        assert ratio_of(rule, []) == Decimal('0')

    def test_ratio_status_closed_interval(self):
        rule = {'lo': Decimal('0.3'), 'hi': Decimal('0.7')}
        assert ratio_status(Decimal('0.3'), rule) == RATIO_NORMAL
        assert ratio_status(Decimal('0.7'), rule) == RATIO_NORMAL
        assert ratio_status(Decimal('0.2'), rule) == RATIO_BELOW
        assert ratio_status(Decimal('0.8'), rule) == RATIO_ABOVE

    def test_count_status(self):
        assert count_status(10, 10) == COUNT_MET
        assert count_status(9, 10) == COUNT_GAP
        assert count_status(5, None) == '未设目标'


# ============================ §9 断言（适用范围自带） ============================
class TestPrdAssertions:
    def setup_method(self):
        self.persons = SAMPLE_PERSONS
        self.rules = build_rules()
        self.headcounts = build_headcounts(2026)
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
        g = check_dimension_sums(self.rules, ('', '', ''))
        assert all(s['ok'] for s in g), g
        ne = check_dimension_sums(self.rules, ('能电BG', '', ''))
        assert all(s['ok'] for s in ne), ne

    def test_count_plan(self):
        rows = compute_count(self.persons, self.rules, self.headcounts, 2026, '8月')
        hc = {(_scope_key(c), c['dimension'], c['indicator']): c for c in rows}
        c985 = hc[(('', '', ''), '院校标签', '985')]
        assert c985['onjob'] == _cnt(self.persons, school='985')
        assert c985['annualTarget'] == 40

    def test_simulate_block(self):
        draft = {'bu': '能电BG', 'school': '211', 'sex': '男', 'major': '工学', 'month': '8月'}
        v = simulate(draft, self.rules, self.persons, self.headcounts, 2026, month='8月')
        assert v['verdict'] == VERDICT_BLOCK
        c = next(ch for ch in v['checks'] if ch['dimension'] == '性别' and ch['indicator'] == '男' and ch['bu'] == '能电BG')
        assert c['ratioStatus'] == RATIO_ABOVE
        assert c['strength'] == '硬约束'


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
            'target': 0.6, 'lo': 0.5, 'hi': 0.7, 'strength': '硬约束',
        })
        assert ser.is_valid(), ser.errors
        ser.save(created_by=hr_user, updated_by=hr_user)
        ser2 = ControlRuleSerializer(data={
            'bu': '能电BG', 'dimension': dim.id, 'indicator': i_f.id,
            'target': 0.4, 'lo': 0.3, 'hi': 0.5, 'strength': '软约束',
        })
        assert ser2.is_valid(), ser2.errors  # 0.6 + 0.4 = 100% OK

    def test_per_rule_overflow_blocked(self, hr_user):
        dim, i_m, i_f = self._mk_dim_ind(hr_user)
        ControlRule.objects.create(
            bu='能电BG', dimension=dim, indicator=i_m,
            target=Decimal('0.6'), lo=Decimal('0.5'), hi=Decimal('0.7'), strength='硬约束',
            created_by=hr_user, updated_by=hr_user,
        )
        ser = ControlRuleSerializer(data={
            'bu': '能电BG', 'dimension': dim.id, 'indicator': i_f.id,
            'target': 0.5, 'lo': 0.3, 'hi': 0.6, 'strength': '软约束',
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
        api_client.post('/api/v1/campus/rules/', {'bu': '能电BG', 'dimension': dim_id, 'indicator': im['id'], 'target': 0.6, 'lo': 0.5, 'hi': 0.7, 'strength': '硬约束'}, format='json')
        api_client.post('/api/v1/campus/rules/', {'bu': '能电BG', 'dimension': dim_id, 'indicator': ifm['id'], 'target': 0.4, 'lo': 0.3, 'hi': 0.5, 'strength': '软约束'}, format='json')
        api_client.post('/api/v1/campus/headcounts/', {'bu': '能电BG', 'indicator': im['id'], 'year': 2026, 'annual_target': 10, 'monthly_targets': [1] * 12}, format='json')
        api_client.post('/api/v1/campus/headcounts/', {'bu': '能电BG', 'indicator': ifm['id'], 'year': 2026, 'annual_target': 10, 'monthly_targets': [1] * 12}, format='json')
        api_client.post('/api/v1/campus/persons/', {'code': 'A001', 'name': '甲', 'bu': '能电BG', 'school': '985', 'sex': '男', 'major': '工学', 'month': '8月', 'status': '已入职', 'counted': True}, format='json')

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

    def test_validate_endpoint_block(self, api_client):
        self._build_minimal_scheme(api_client)
        resp = api_client.post(
            '/api/v1/campus/rules/validate/?year=2026',
            {'bu': '能电BG', 'school': '211', 'sex': '男', 'major': '工学', 'month': '8月'},
            format='json',
        )
        assert resp.status_code == 200, resp.json()
        assert resp.json()['data']['verdict'] == VERDICT_BLOCK

    def test_rule_100_block_via_api(self, api_client):
        d = api_client.post('/api/v1/campus/dimensions/', {'name': '性别'}, format='json').json()
        dim_id = d['id']
        im = api_client.post('/api/v1/campus/indicators/', {'dimension': dim_id, 'name': '男'}, format='json').json()
        ifm = api_client.post('/api/v1/campus/indicators/', {'dimension': dim_id, 'name': '女'}, format='json').json()
        r1 = api_client.post('/api/v1/campus/rules/', {'bu': '三到BG', 'dimension': dim_id, 'indicator': im['id'], 'target': 0.6, 'lo': 0.5, 'hi': 0.7, 'strength': '硬约束'}, format='json')
        assert r1.status_code == 201, r1.json()
        r2 = api_client.post('/api/v1/campus/rules/', {'bu': '三到BG', 'dimension': dim_id, 'indicator': ifm['id'], 'target': 0.5, 'lo': 0.3, 'hi': 0.6, 'strength': '软约束'}, format='json')
        assert r2.status_code == 400, r2.json()

    def test_batch_100_ok(self, api_client):
        d = api_client.post('/api/v1/campus/dimensions/', {'name': '性别'}, format='json').json()
        im = api_client.post('/api/v1/campus/indicators/', {'dimension': d['id'], 'name': '男'}, format='json').json()
        ifm = api_client.post('/api/v1/campus/indicators/', {'dimension': d['id'], 'name': '女'}, format='json').json()
        resp = api_client.post('/api/v1/campus/rules/batch/', {
            'bu': '能电BG', 'dimension': d['id'],
            'rules': [
                {'indicator': im['id'], 'target': 0.6, 'lo': 0.5, 'hi': 0.7, 'strength': '硬约束'},
                {'indicator': ifm['id'], 'target': 0.4, 'lo': 0.3, 'hi': 0.5, 'strength': '软约束'},
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
            'rules': [{'indicator': im['id'], 'target': 0.6, 'lo': 0.5, 'hi': 0.7, 'strength': '硬约束'}],
        }, format='json')
        assert resp.status_code == 400, resp.json()
        assert '100%' in resp.json()['detail']

    def test_requires_auth(self):
        from rest_framework.test import APIClient
        client = APIClient()
        resp = client.get('/api/v1/campus/dimensions/')
        assert resp.status_code in (401, 403)


class TestBatchConfigWithTargets:
    """POST /rules/with-targets/ 端点：批量配置规则 + 人数目标（原子写入）。

    契约：
    - 占比加和须 == 100%，否则 400
    - indicator 必须属于 dimension，否则 400
    - 年度人数 = round(totalTarget × target)
    - 事务内：删除该(适用范围, 维度)旧规则 → 创建新规则 → upsert headcount
    """

    def _setup_scheme(self, api_client):
        s = api_client.post('/api/v1/campus/scopes/' if False else '/api/v1/campus/dimensions/', {'name': '测试维度WT'}, format='json')
        assert s.status_code == 201, s.json()
        dim_id = s.json()['id']
        i1 = api_client.post('/api/v1/campus/indicators/', {'dimension': dim_id, 'name': 'A'}, format='json').json()
        i2 = api_client.post('/api/v1/campus/indicators/', {'dimension': dim_id, 'name': 'B'}, format='json').json()
        return dim_id, i1['id'], i2['id']

    def test_with_targets_100_ok(self, api_client):
        """占比加和 = 100% → 规则与 headcount 创建成功，annual = round(totalTarget×target)。"""
        dim_id, i1, i2 = self._setup_scheme(api_client)
        resp = api_client.post('/api/v1/campus/rules/with-targets/', {
            'bu': '', 'position': '', 'level': '',
            'dimension': dim_id, 'year': 2026, 'totalTarget': 100,
            'rules': [
                {'indicator': i1, 'target': 0.6, 'lo': 0.5, 'hi': 0.7, 'strength': '硬约束'},
                {'indicator': i2, 'target': 0.4, 'lo': 0.3, 'hi': 0.5, 'strength': '软约束'},
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

        # headcount 创建：annual = round(100 × 0.6) = 60 / round(100 × 0.4) = 40
        hcs = api_client.get('/api/v1/campus/headcounts/', {'params': {'page_size': 200, 'year': 2026}}).json()['data']
        dim_hcs = [h for h in hcs if h['dimensionName'] == '测试维度WT']
        assert len(dim_hcs) == 2
        annuals = sorted(h['annualTarget'] for h in dim_hcs)
        assert annuals == [40, 60]

    def test_with_targets_not_100_blocked(self, api_client):
        """占比加和 ≠ 100% → 400。"""
        dim_id, i1, i2 = self._setup_scheme(api_client)
        resp = api_client.post('/api/v1/campus/rules/with-targets/', {
            'bu': '', 'position': '', 'level': '',
            'dimension': dim_id, 'year': 2026, 'totalTarget': 50,
            'rules': [
                {'indicator': i1, 'target': 0.6, 'lo': 0.5, 'hi': 0.7, 'strength': '硬约束'},
                {'indicator': i2, 'target': 0.5, 'lo': 0.3, 'hi': 0.6, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp.status_code == 400
        assert '100%' in resp.json().get('detail', '')

    def test_with_targets_indicator_not_in_dim_blocked(self, api_client):
        """indicator 不属于 dimension → 400。"""
        dim_id, i1, i2 = self._setup_scheme(api_client)
        # 另建一个维度下的指标
        s2 = api_client.post('/api/v1/campus/dimensions/', {'name': '其他维度WT'}, format='json').json()
        i_other = api_client.post('/api/v1/campus/indicators/', {'dimension': s2['id'], 'name': 'X'}, format='json').json()
        resp = api_client.post('/api/v1/campus/rules/with-targets/', {
            'bu': '', 'position': '', 'level': '',
            'dimension': dim_id, 'year': 2026, 'totalTarget': 100,
            'rules': [
                {'indicator': i1, 'target': 0.5, 'lo': 0, 'hi': 1, 'strength': '硬约束'},
                {'indicator': i_other['id'], 'target': 0.5, 'lo': 0, 'hi': 1, 'strength': '硬约束'},
            ],
        }, format='json')
        assert resp.status_code == 400
        assert '不属于' in resp.json().get('detail', '')

    def test_with_targets_atomic_replaces_old_rules(self, api_client):
        """事务原子：with-targets 调用后该 (适用范围, 维度) 下旧规则被替换。"""
        dim_id, i1, i2 = self._setup_scheme(api_client)
        # 先创建旧规则
        api_client.post('/api/v1/campus/rules/', {
            'bu': '', 'dimension': dim_id, 'indicator': i1, 'target': 0.5, 'lo': 0, 'hi': 1, 'strength': '硬约束',
        }, format='json')
        # with-targets
        resp = api_client.post('/api/v1/campus/rules/with-targets/', {
            'bu': '', 'position': '', 'level': '',
            'dimension': dim_id, 'year': 2026, 'totalTarget': 200,
            'rules': [
                {'indicator': i1, 'target': 0.7, 'lo': 0.5, 'hi': 0.9, 'strength': '硬约束'},
                {'indicator': i2, 'target': 0.3, 'lo': 0.1, 'hi': 0.5, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp.status_code == 200
        # 验证只有 2 条规则（旧被替换）
        rules = api_client.get('/api/v1/campus/rules/', {'params': {'page_size': 200}}).json()['data']
        dim_rules = [r for r in rules if r['dimension'] == dim_id]
        assert len(dim_rules) == 2
        # headcount annual = round(200 × 0.7) = 140 / round(200 × 0.3) = 60
        hcs = api_client.get('/api/v1/campus/headcounts/', {'params': {'page_size': 200, 'year': 2026}}).json()['data']
        dim_hcs = sorted([h['annualTarget'] for h in hcs if h['dimensionName'] == '测试维度WT'])
        assert dim_hcs == [60, 140]
