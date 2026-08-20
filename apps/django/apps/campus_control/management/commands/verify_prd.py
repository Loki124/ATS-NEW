"""PRD §9 验收（v2，scope 感知，纯函数，不依赖数据库）。

用法：
    python manage.py verify_prd

用 §9.0 样例人员 + 默认方案/规则/人数目标 跑 compute_ratio + compute_count + simulate，
断言 v2 关键结论：同维度目标占比加和=100%、性别男比例、录入校验阻断。
"""
from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.campus_control.calc import (
    compute_ratio, compute_count, simulate, check_dimension_sums,
)
from apps.campus_control.constants import VERDICT_BLOCK
from apps.campus_control.sample_data import (
    SAMPLE_PERSONS, build_rules, build_headcounts, _INDICATOR_ANNUAL,
)

SCOPE_ID = '能电BG校招'
BU = '能电BG'


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


def _monthly_annual(annual, idx1):
    base = annual // 12
    rem = annual % 12
    return base + 1 if (idx1 - 1) < rem else base


class Command(BaseCommand):
    help = '验证 PRD §9 v2 计算断言（纯函数）'

    def handle(self, *args, **options):
        persons = SAMPLE_PERSONS
        rules = build_rules(SCOPE_ID)
        headcounts = build_headcounts(SCOPE_ID, 2026)
        scope = {'bu': BU, 'position': '', 'level': ''}

        # ---------- §9.1 比例断言（scope 感知）----------
        res = compute_ratio(persons, rules, scope)
        assert res['total'] == 12, f"能电BG 计入人数应为 12，实际 {res['total']}"
        rows = {(r['dimension'], r['indicator']): r for r in res['rows']}

        exp_male = _cnt(persons, bu=BU, sex='男') / _cnt(persons, bu=BU)
        r = rows[('性别', '男')]
        assert abs(float(r['ratio']) - exp_male) < 1e-3, r
        assert r['status'] == '高于上限', r
        assert r['strength'] == '硬约束', r

        exp_985 = _cnt(persons, bu=BU, school='985') / _cnt(persons, bu=BU)
        r985 = rows[('院校标签', '985')]
        assert abs(float(r985['ratio']) - exp_985) < 1e-3, r985

        # ---------- §9.x 100% 加和断言 ----------
        sums = check_dimension_sums(rules, SCOPE_ID)
        assert all(s['ok'] for s in sums), f"存在未加和到100%的维度：{sums}"
        self.stdout.write(self.style.SUCCESS('✅ 各维度目标占比加和均 = 100%'))

        # ---------- §9.2 人数规划断言（指标层）----------
        cnt_rows = compute_count(persons, rules, headcounts, scope, 2026, '8月')
        hc = {(c['dimension'], c['indicator']): c for c in cnt_rows}
        c985 = hc[('院校标签', '985')]
        assert c985['onjob'] == _cnt(persons, bu=BU, school='985'), c985
        mt = _monthly_annual(_INDICATOR_ANNUAL['985'], 8)  # 8月
        assert c985['monthTarget'] == mt, (c985['monthTarget'], mt)
        assert c985['annualTarget'] == _INDICATOR_ANNUAL['985'], c985

        # ---------- §9.3 录入校验断言 ----------
        draft = {'bu': BU, 'school': '211', 'sex': '男', 'major': '工学', 'month': '8月'}
        v = simulate(draft, rules, persons, headcounts, scope, 2026, month='8月')
        assert v['verdict'] == VERDICT_BLOCK, v

        self.stdout.write(self.style.SUCCESS(
            '✅ PRD §9 v2 断言通过：比例 / 100%加和 / 人数规划 / 录入校验(阻断)'
        ))
