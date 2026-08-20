"""PRD §9 验收（纯函数，不依赖数据库）。

用法：
    python manage.py verify_prd

用 §9.0 样例数据跑 compute_ratio + compute_count + simulate，
断言 §9.1 / §9.2 / §9.3 全部成立，作为实施硬证据。
"""
from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.campus_control.calc import compute_ratio, compute_count, simulate
from apps.campus_control.constants import VERDICT_BLOCK
from apps.campus_control.sample_data import SAMPLE_PERSONS, DEFAULT_RULES


class Command(BaseCommand):
    help = '验证 PRD §9 计算断言（纯函数）'

    def handle(self, *args, **options):
        persons = SAMPLE_PERSONS
        rules = DEFAULT_RULES

        # §9.0 数据规模
        res = compute_ratio(persons, rules)
        assert res['total'] == 31, f"§9.0 total 应为 31，实际 {res['total']}"

        rows = {(r['dim'], r['group']): r for r in res['rows']}

        # §9.1 比例断言
        r = rows[('性别', '能电BG-男')]
        assert r['ratio'] == Decimal('0.75'), r
        assert r['status'] == '高于上限', r
        assert r['strength'] == '硬约束', r

        r = rows[('专业标签', '工学')]
        assert r['ratio'] == Decimal('0.323'), r
        assert r['status'] == '低于下限', r

        r = rows[('性别', '三到BG-男')]
        assert r['ratio'] == Decimal('1.000'), r
        assert r['status'] == '正常', r

        r = rows[('院校标签', '985')]
        assert r['ratio'] == Decimal('0.355'), r
        assert r['status'] == '正常', r

        # §9.2 人数规划断言（month=8月）
        cnt = {(r['dim'], r['group']): r for r in compute_count(persons, rules, '8月')}
        c = cnt[('院校标签', '985')]
        assert c['onjob'] == 11, c
        assert c['month_target'] == 120, c
        assert c['gap'] == 109, c
        assert c['whole'] == 120, c
        assert c['whole_gap'] == 109, c

        # §9.3 录入校验断言：能电BG/211/男/工学/8月 → 阻断提交
        draft = {'bu': '能电BG', 'school': '211', 'sex': '男', 'major': '工学', 'month': '8月'}
        v = simulate(draft, rules, persons, month='8月')
        assert v['verdict'] == VERDICT_BLOCK, v

        self.stdout.write(self.style.SUCCESS(
            '✅ PRD §9.0 / §9.1 / §9.2 / §9.3 全部断言通过'
        ))
