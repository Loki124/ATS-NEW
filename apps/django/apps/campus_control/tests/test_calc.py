"""校招管控 v2 — 计算引擎与 API 端点测试。

覆盖：
  - 纯函数（scope 感知）：count / count_rule / denom_rule / ratio_of / ratio_status /
    count_status / compute_ratio / compute_count / kpi / simulate / check_dimension_sums
  - §9 断言（基于 §9.0 样例数据，scope 感知）
  - 100% 加和硬校验（序列化器 + API 双路径）
  - API 端点（scopes/dimensions/indicators/rules/headcounts + ratio/plan/validate）端到端
"""
import pytest
from decimal import Decimal

from ..sample_data import SAMPLE_PERSONS, build_rules, build_headcounts
from ..calc import (
    count, count_rule, denom_rule, ratio_of, ratio_status, count_status,
    compute_ratio, compute_count, kpi, simulate, check_dimension_sums,
)
from ..constants import (
    RATIO_NORMAL, RATIO_BELOW, RATIO_ABOVE, COUNT_MET, COUNT_GAP,
    VERDICT_BLOCK, VERDICT_WARN, VERDICT_PASS,
)
from ..models import (
    ControlScope, ControlDimension, ControlIndicator, ControlRule, ControlHeadcount, Person,
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

    def test_denom_rule_gender_uses_scope_bu(self):
        persons = [
            {'bu': '能电BG', 'sex': '男'},
            {'bu': '能电BG', 'sex': '女'},
            {'bu': '三到BG', 'sex': '男'},
        ]
        scope = {'bu': '能电BG', 'position': '', 'level': ''}
        rule = {'dimension': '性别', 'indicator': '男'}
        assert denom_rule(rule, persons, scope) == 2  # 仅能电BG 人数
        rule2 = {'dimension': '院校标签', 'indicator': '985'}
        assert denom_rule(rule2, persons, scope) == 3  # 范围内全部

    def test_ratio_of_zero_denom_returns_zero(self):
        scope = {'bu': 'X', 'position': '', 'level': ''}
        rule = {'dimension': '性别', 'indicator': '男'}
        assert ratio_of(rule, [], scope) == Decimal('0')

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


# ============================ §9 断言（scope 感知） ============================
class TestPrdAssertions:
    SCOPE_ID = '能电BG校招'
    BU = '能电BG'

    def setup_method(self):
        self.persons = SAMPLE_PERSONS
        self.rules = build_rules(self.SCOPE_ID)
        self.headcounts = build_headcounts(self.SCOPE_ID, 2026)
        self.scope = {'bu': self.BU, 'position': '', 'level': ''}
        self.ratio = compute_ratio(self.persons, self.rules, self.scope)
        self.rows = {(r['dimension'], r['indicator']): r for r in self.ratio['rows']}

    def test_total_scope_population(self):
        assert self.ratio['total'] == 12  # 能电BG 计入人数

    def test_gender_male_ratio(self):
        r = self.rows[('性别', '男')]
        exp = _cnt(self.persons, bu=self.BU, sex='男') / _cnt(self.persons, bu=self.BU)
        assert abs(float(r['ratio']) - exp) < 1e-3
        assert r['status'] == RATIO_ABOVE
        assert r['strength'] == '硬约束'

    def test_school_985_ratio(self):
        r = self.rows[('院校标签', '985')]
        exp = _cnt(self.persons, bu=self.BU, school='985') / _cnt(self.persons, bu=self.BU)
        assert abs(float(r['ratio']) - exp) < 1e-3

    def test_dimension_sums_eq_100(self):
        sums = check_dimension_sums(self.rules, self.SCOPE_ID)
        assert all(s['ok'] for s in sums), sums

    def test_count_plan(self):
        cnt_rows = compute_count(self.persons, self.rules, self.headcounts, self.scope, 2026, '8月')
        hc = {(c['dimension'], c['indicator']): c for c in cnt_rows}
        c985 = hc[('院校标签', '985')]
        assert c985['onjob'] == _cnt(self.persons, bu=self.BU, school='985')
        assert c985['annualTarget'] == 40

    def test_simulate_block(self):
        draft = {'bu': self.BU, 'school': '211', 'sex': '男', 'major': '工学', 'month': '8月'}
        v = simulate(draft, self.rules, self.persons, self.headcounts, self.scope, 2026, month='8月')
        assert v['verdict'] == VERDICT_BLOCK
        c = next(ch for ch in v['checks'] if ch['dimension'] == '性别' and ch['indicator'] == '男')
        assert c['ratioStatus'] == RATIO_ABOVE
        assert c['strength'] == '硬约束'


# ============================ 100% 加和硬校验 ============================
@pytest.mark.django_db
class TestSum100Validation:
    def _mk_scope_dim_ind(self, hr_user):
        scope = ControlScope.objects.create(name='测试方案', bu='能电BG', created_by=hr_user, updated_by=hr_user)
        dim = ControlDimension.objects.create(name='性别', created_by=hr_user, updated_by=hr_user)
        i_m = ControlIndicator.objects.create(dimension=dim, name='男', created_by=hr_user, updated_by=hr_user)
        i_f = ControlIndicator.objects.create(dimension=dim, name='女', created_by=hr_user, updated_by=hr_user)
        return scope, dim, i_m, i_f

    def test_valid_100_sum_ok(self, hr_user):
        scope, dim, i_m, i_f = self._mk_scope_dim_ind(hr_user)
        ser = ControlRuleSerializer(data={
            'scope': scope.id, 'dimension': dim.id, 'indicator': i_m.id,
            'target': 0.6, 'lo': 0.5, 'hi': 0.7, 'strength': '硬约束',
        })
        assert ser.is_valid(), ser.errors
        ser.save(created_by=hr_user, updated_by=hr_user)
        ser2 = ControlRuleSerializer(data={
            'scope': scope.id, 'dimension': dim.id, 'indicator': i_f.id,
            'target': 0.4, 'lo': 0.3, 'hi': 0.5, 'strength': '软约束',
        })
        assert ser2.is_valid(), ser2.errors  # 0.6 + 0.4 = 100% OK

    def test_per_rule_overflow_blocked(self, hr_user):
        # 单条编辑仅拦截「超 100%」：0.6 + 0.5 = 110% → 阻断
        scope, dim, i_m, i_f = self._mk_scope_dim_ind(hr_user)
        ControlRule.objects.create(
            scope=scope, dimension=dim, indicator=i_m,
            target=Decimal('0.6'), lo=Decimal('0.5'), hi=Decimal('0.7'), strength='硬约束',
            created_by=hr_user, updated_by=hr_user,
        )
        ser = ControlRuleSerializer(data={
            'scope': scope.id, 'dimension': dim.id, 'indicator': i_f.id,
            'target': 0.5, 'lo': 0.3, 'hi': 0.6, 'strength': '软约束',
        })
        assert not ser.is_valid()
        assert any('100%' in str(v) for vals in ser.errors.values() for v in (vals if isinstance(vals, list) else [vals]))

    def test_sum_not_100_blocked(self, hr_user):
        scope, dim, i_m, i_f = self._mk_scope_dim_ind(hr_user)
        ControlRule.objects.create(
            scope=scope, dimension=dim, indicator=i_m,
            target=Decimal('0.6'), lo=Decimal('0.5'), hi=Decimal('0.7'), strength='硬约束',
            created_by=hr_user, updated_by=hr_user,
        )
        # 再加 女 target=0.5 -> 0.6+0.5=110% ≠ 100% -> 硬拦截
        ser = ControlRuleSerializer(data={
            'scope': scope.id, 'dimension': dim.id, 'indicator': i_f.id,
            'target': 0.5, 'lo': 0.3, 'hi': 0.6, 'strength': '软约束',
        })
        assert not ser.is_valid()
        assert any('100%' in str(v) for vals in ser.errors.values() for v in (vals if isinstance(vals, list) else [vals]))


# ============================ API 端点 ============================
@pytest.mark.django_db
class TestApiEndpoints:
    def _build_minimal_scheme(self, api_client):
        s = api_client.post('/api/v1/campus/scopes/', {'name': 'API方案', 'bu': '能电BG', 'is_active': True}, format='json').json()
        scope_id = s['id']
        d = api_client.post('/api/v1/campus/dimensions/', {'name': '性别'}, format='json').json()
        dim_id = d['id']
        im = api_client.post('/api/v1/campus/indicators/', {'dimension': dim_id, 'name': '男'}, format='json').json()
        ifm = api_client.post('/api/v1/campus/indicators/', {'dimension': dim_id, 'name': '女'}, format='json').json()
        api_client.post('/api/v1/campus/rules/', {'scope': scope_id, 'dimension': dim_id, 'indicator': im['id'], 'target': 0.6, 'lo': 0.5, 'hi': 0.7, 'strength': '硬约束'}, format='json')
        api_client.post('/api/v1/campus/rules/', {'scope': scope_id, 'dimension': dim_id, 'indicator': ifm['id'], 'target': 0.4, 'lo': 0.3, 'hi': 0.5, 'strength': '软约束'}, format='json')
        api_client.post('/api/v1/campus/headcounts/', {'scope': scope_id, 'indicator': im['id'], 'year': 2026, 'annual_target': 10, 'monthly_targets': [1] * 12}, format='json')
        api_client.post('/api/v1/campus/headcounts/', {'scope': scope_id, 'indicator': ifm['id'], 'year': 2026, 'annual_target': 10, 'monthly_targets': [1] * 12}, format='json')
        api_client.post('/api/v1/campus/persons/', {'code': 'A001', 'name': '甲', 'bu': '能电BG', 'school': '985', 'sex': '男', 'major': '工学', 'month': '8月', 'status': '已入职', 'counted': True}, format='json')
        return scope_id

    def test_ratio_endpoint(self, api_client):
        scope_id = self._build_minimal_scheme(api_client)
        resp = api_client.get(f'/api/v1/campus/rules/ratio/?scope={scope_id}')
        assert resp.status_code == 200, resp.json()
        data = resp.json()['data']
        male = next(r for r in data['rows'] if r['dimension'] == '性别' and r['indicator'] == '男')
        assert abs(male['ratio'] - 1.0) < 1e-3  # 仅 1 名男性
        assert male['status'] == '高于上限'
        # sumChecks 应全 ok
        assert all(s['ok'] for s in data['sumChecks'])

    def test_plan_endpoint(self, api_client):
        scope_id = self._build_minimal_scheme(api_client)
        resp = api_client.get(f'/api/v1/campus/rules/plan/?scope={scope_id}&year=2026&month=8月')
        assert resp.status_code == 200, resp.json()
        data = resp.json()['data']
        assert data['rows']

    def test_validate_endpoint_block(self, api_client):
        scope_id = self._build_minimal_scheme(api_client)
        resp = api_client.post(
            f'/api/v1/campus/rules/validate/?scope={scope_id}&year=2026',
            {'school': '211', 'sex': '男', 'major': '工学', 'month': '8月'},
            format='json',
        )
        assert resp.status_code == 200, resp.json()
        assert resp.json()['data']['verdict'] == VERDICT_BLOCK

    def test_rule_100_block_via_api(self, api_client):
        s = api_client.post('/api/v1/campus/scopes/', {'name': '阻断方案', 'bu': '三到BG', 'is_active': True}, format='json').json()
        scope_id = s['id']
        d = api_client.post('/api/v1/campus/dimensions/', {'name': '性别'}, format='json').json()
        dim_id = d['id']
        im = api_client.post('/api/v1/campus/indicators/', {'dimension': dim_id, 'name': '男'}, format='json').json()
        ifm = api_client.post('/api/v1/campus/indicators/', {'dimension': dim_id, 'name': '女'}, format='json').json()
        r1 = api_client.post('/api/v1/campus/rules/', {'scope': scope_id, 'dimension': dim_id, 'indicator': im['id'], 'target': 0.6, 'lo': 0.5, 'hi': 0.7, 'strength': '硬约束'}, format='json')
        assert r1.status_code == 201, r1.json()
        # 女加 0.5 -> 110% -> 400
        r2 = api_client.post('/api/v1/campus/rules/', {'scope': scope_id, 'dimension': dim_id, 'indicator': ifm['id'], 'target': 0.5, 'lo': 0.3, 'hi': 0.6, 'strength': '软约束'}, format='json')
        assert r2.status_code == 400, r2.json()

    def test_batch_100_ok(self, api_client):
        # 批量保存完整维度：0.6 + 0.4 = 100% → 201，且落库两条
        s = api_client.post('/api/v1/campus/scopes/', {'name': '批量方案', 'bu': '能电BG', 'is_active': True}, format='json').json()
        d = api_client.post('/api/v1/campus/dimensions/', {'name': '性别'}, format='json').json()
        im = api_client.post('/api/v1/campus/indicators/', {'dimension': d['id'], 'name': '男'}, format='json').json()
        ifm = api_client.post('/api/v1/campus/indicators/', {'dimension': d['id'], 'name': '女'}, format='json').json()
        resp = api_client.post('/api/v1/campus/rules/batch/', {
            'scope': s['id'], 'dimension': d['id'],
            'rules': [
                {'indicator': im['id'], 'target': 0.6, 'lo': 0.5, 'hi': 0.7, 'strength': '硬约束'},
                {'indicator': ifm['id'], 'target': 0.4, 'lo': 0.3, 'hi': 0.5, 'strength': '软约束'},
            ],
        }, format='json')
        assert resp.status_code == 200, resp.json()
        assert resp.json()['data']['saved'] == 2

    def test_batch_not_100_blocked(self, api_client):
        # 批量保存不完整维度：仅 0.6 ≠ 100% → 400
        s = api_client.post('/api/v1/campus/scopes/', {'name': '缺额方案', 'bu': '能电BG', 'is_active': True}, format='json').json()
        d = api_client.post('/api/v1/campus/dimensions/', {'name': '性别'}, format='json').json()
        im = api_client.post('/api/v1/campus/indicators/', {'dimension': d['id'], 'name': '男'}, format='json').json()
        api_client.post('/api/v1/campus/indicators/', {'dimension': d['id'], 'name': '女'}, format='json').json()
        resp = api_client.post('/api/v1/campus/rules/batch/', {
            'scope': s['id'], 'dimension': d['id'],
            'rules': [
                {'indicator': im['id'], 'target': 0.6, 'lo': 0.5, 'hi': 0.7, 'strength': '硬约束'},
            ],
        }, format='json')
        assert resp.status_code == 400, resp.json()
        assert '100%' in resp.json()['detail']

    def test_requires_auth(self):
        from rest_framework.test import APIClient
        client = APIClient()
        resp = client.get('/api/v1/campus/scopes/')
        assert resp.status_code in (401, 403)
