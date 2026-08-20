"""校招管控 v2.1 — 种子数据写入。

用法：
    python manage.py seed_campus            # 若不存在则写入
    python manage.py seed_campus --force     # 清空后重写

写入：3 维度 + 指标 + 规则(全局院校/专业 + 各部门性别，加和=100%) + 指标层年度/12月目标 + 31 名样例人员。
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.campus_control.models import (
    ControlDimension, ControlIndicator, ControlRule, ControlHeadcount, Person,
)
from apps.campus_control.sample_data import (
    SAMPLE_PERSONS, DIMENSION_NAMES, INDICATOR_NAMES, build_rules, build_headcounts,
)


class Command(BaseCommand):
    help = '写入校招管控 v2.1 种子数据（维度/指标/规则/人数目标/样例人员）'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='清空后重写')

    @transaction.atomic
    def handle(self, *args, **options):
        if options['force']:
            ControlHeadcount.objects.all().delete()
            ControlRule.objects.all().delete()
            ControlIndicator.objects.all().delete()
            ControlDimension.objects.all().delete()
            Person.objects.all().delete()
            self.stdout.write('已清空旧数据')

        # 维度
        dims = {}
        for name in DIMENSION_NAMES:
            d, _ = ControlDimension.objects.get_or_create(name=name)
            dims[name] = d
        self.stdout.write(f'已写入 {len(dims)} 个维度')

        # 指标（关联维度）
        inds = {}
        for dim_name, ind_list in INDICATOR_NAMES.items():
            for ind_name in ind_list:
                ind, _ = ControlIndicator.objects.get_or_create(
                    dimension=dims[dim_name], name=ind_name
                )
                inds[(dim_name, ind_name)] = ind
        self.stdout.write(f'已写入 {len(inds)} 个指标')

        # 规则（全局院校/专业 + 各部门性别）
        rule_count = 0
        for r in build_rules():
            _, created = ControlRule.objects.get_or_create(
                bu=r['bu'], position=r['position'], level=r['level'],
                dimension=dims[r['dimension']], indicator=inds[(r['dimension'], r['indicator'])],
                defaults={'target': Decimal(str(r['target'])), 'lo': Decimal(str(r['lo'])),
                          'hi': Decimal(str(r['hi'])), 'strength': r['strength']},
            )
            rule_count += 1 if created else 0
        self.stdout.write(f'已写入 {rule_count} 条规则')

        # 人数目标（指标层，适用范围自带）
        hc_count = 0
        for h in build_headcounts(2026):
            _, created = ControlHeadcount.objects.get_or_create(
                bu=h['bu'], position=h['position'], level=h['level'],
                indicator=inds[(h['dimension'], h['indicator'])], year=h['year'],
                defaults={'annual_target': h['annual_target'], 'monthly_targets': h['monthly_targets']},
            )
            hc_count += 1 if created else 0
        self.stdout.write(f'已写入 {hc_count} 条人数目标')

        # 样例人员
        p_count = 0
        for p in SAMPLE_PERSONS:
            _, created = Person.objects.get_or_create(
                code=p['code'],
                defaults={
                    'name': p['name'], 'bu': p['bu'], 'school': p['school'],
                    'sex': p['sex'], 'major': p['major'], 'month': p['month'],
                    'status': p['status'], 'counted': p['counted'],
                    'position': p['position'], 'level': p['level'],
                },
            )
            p_count += 1 if created else 0
        self.stdout.write(f'已写入 {p_count} 名样例人员')
        self.stdout.write(self.style.SUCCESS('种子完成'))
