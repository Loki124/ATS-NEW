"""校招管控 v2.4 — 种子数据写入。

用法：
    python manage.py seed_campus                # 若不存在则写入（幂等）
    python manage.py seed_campus --force        # 清空后重写
    python manage.py seed_campus --renumber     # 存量数据有 P 前缀/非 C+8 时兜底重编号

写入：3 维度 + 指标 + 规则(全局院校/专业 + 各部门性别，加和=100%，含年度/12月人数目标) + 31 名样例人员。

候选人编号（C+8 位流水号）由 Person.save() 自动补号；本命令不再硬编码 code，按
业务键 (name, bu, status) 做幂等查重。新建环境跑一次本命令即可得到
C00000001..C00000031 连续编号。
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.campus_control.models import (
    ControlDimension,
    ControlIndicator,
    ControlRule,
    Person,
)
from apps.campus_control.sample_data import (
    DIMENSION_NAMES,
    INDICATOR_NAMES,
    SAMPLE_PERSONS,
    build_rules,
)


class Command(BaseCommand):
    help = '写入校招管控 v2.4 种子数据（维度/指标/规则[含人数目标]/样例人员）'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='清空后重写')
        parser.add_argument(
            '--renumber', action='store_true',
            help='存量数据有非 C+8 前缀时，先调 renumber_persons 兜底重编号',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options['renumber']:
            from apps.campus_control.management.commands.renumber_persons import (
                Command as RenumberCommand,
            )
            RenumberCommand().handle()
            self.stdout.write('已执行 renumber_persons')

        if options['force']:
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

        # 规则（全局院校/专业 + 各部门性别，含年度/12月人数目标）
        rule_count = 0
        for r in build_rules(2026):
            _, created = ControlRule.objects.get_or_create(
                bu=r['bu'], position=r['position'], level=r['level'],
                dimension=dims[r['dimension']], indicator=inds[(r['dimension'], r['indicator'])],
                year=r['year'],
                defaults={
                    'target': Decimal(str(r['target'])),
                    'strength': r['strength'],
                    'annual_target': r.get('annual_target', 0),
                    'monthly_targets': r.get('monthly_targets', [0] * 12),
                },
            )
            rule_count += 1 if created else 0
        self.stdout.write(f'已写入 {rule_count} 条规则')

        # 样例人员：按业务键 (name, bu, status) 幂等查重，code 由 save() 自动补号 C+8
        p_count = 0
        p_skip = 0
        for p in SAMPLE_PERSONS:
            _, created = Person.objects.get_or_create(
                name=p['name'], bu=p['bu'], status=p['status'],
                defaults={
                    'school': p['school'], 'sex': p['sex'], 'major': p['major'],
                    'month': p['month'], 'counted': p['counted'],
                    'position': p['position'], 'level': p['level'],
                    # code 不传 → Person.save() 自动补号
                },
            )
            if created:
                p_count += 1
            else:
                p_skip += 1
        self.stdout.write(
            f'样例人员：新建 {p_count} / 已存在 {p_skip}（按业务键跳过）'
        )
        self.stdout.write(self.style.SUCCESS('种子完成'))
