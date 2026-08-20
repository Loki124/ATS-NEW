"""PRD §9 验收（v2.1，适用范围由规则自带，纯函数，不依赖数据库）。

用法：
    python manage.py verify_prd

用 §9.0 样例人员 + 默认规则/人数目标 跑 compute_ratio + compute_count + simulate，
断言 v2.1 关键结论：同适用范围同维度目标占比加和=100%、性别男比例（部门口径）、录入校验阻断。
"""
from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.campus_control.calc import (
    compute_ratio, compute_count, simulate, check_dimension_sums, _scope_key,
)
from apps.campus_control.constants import VERDICT_BLOCK, RATIO_ABOVE
from apps.campus_control.sample_data import (
    SAMPLE_PERSONS, build_rules, build_headcounts, _INDICATOR_ANNUAL,
)


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
    help = '验证 PRD §9 v2.1 计算断言（纯函数）'

    def handle(self, *args, **options):
        persons = SAMPLE_PERSONS
        rules = build_rules()
        headcounts = build_headcounts(2026)

        # ---------- §9.1 比例断言（适用范围自带） ----------
        res = compute_ratio(persons, rules)
        assert res['total'] == 31, f"计入人数应为 31，实际 {res['total']}"
        rows = {(_scope_key(r), r['dimension'], r['indicator']): r for r in res['rows']}

        # 全局 985 比例
        r985 = rows[(('', '', ''), '院校标签', '985')]
        exp985 = _cnt(persons, school='985') / _cnt(persons)
        assert abs(float(r985['ratio']) - exp985) < 1e-3, r985

        # 能电BG 性别·男 比例（部门口径，硬约束超标）
        r_male = rows[(('能电BG', '', ''), '性别', '男')]
        exp_male = _cnt(persons, bu='能电BG', sex='男') / _cnt(persons, bu='能电BG')
        assert abs(float(r_male['ratio']) - exp_male) < 1e-3, r_male
        assert r_male['status'] == RATIO_ABOVE, r_male
        assert r_male['strength'] == '硬约束', r_male

        # ---------- §9.x 100% 加和断言（按适用范围分组） ----------
        g_sum = check_dimension_sums(rules, ('', '', ''))
        assert all(s['ok'] for s in g_sum), f'全局存在未加和到100%的维度：{g_sum}'
        ne_sum = check_dimension_sums(rules, ('能电BG', '', ''))
        assert all(s['ok'] for s in ne_sum), f'能电BG存在未加和到100%的维度：{ne_sum}'
        self.stdout.write(self.style.SUCCESS('✅ 各适用范围各维度目标占比加和均 = 100%'))

        # ---------- §9.2 人数规划断言（指标层，适用范围自带） ----------
        cnt_rows = compute_count(persons, rules, headcounts, 2026, '8月')
        hc = {(_scope_key(c), c['dimension'], c['indicator']): c for c in cnt_rows}
        c985 = hc[(('', '', ''), '院校标签', '985')]
        assert c985['onjob'] == _cnt(persons, school='985'), c985
        assert c985['annualTarget'] == _INDICATOR_ANNUAL['985'], c985
        mt = _monthly_annual(_INDICATOR_ANNUAL['985'], 8)
        assert c985['monthTarget'] == mt, (c985['monthTarget'], mt)

        # ---------- §9.3 录入校验断言 ----------
        draft = {'bu': '能电BG', 'school': '211', 'sex': '男', 'major': '工学', 'month': '8月'}
        v = simulate(draft, rules, persons, headcounts, 2026, month='8月')
        assert v['verdict'] == VERDICT_BLOCK, v

        self.stdout.write(self.style.SUCCESS(
            '✅ PRD §9 v2.1 断言通过：比例 / 100%加和 / 人数规划 / 录入校验(阻断)'
        ))
