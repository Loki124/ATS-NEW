"""校招管控 v2 — 种子数据写入。

用法：
    python manage.py seed_campus            # 若不存在则写入
    python manage.py seed_campus --force     # 清空后重写

写入：4 个适用范围 + 3 维度 + 指标 + 每方案规则(性别男+女=100%) + 每指标年度/12月目标 + 31 名样例人员。
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.campus_control.models import (
    ControlScope, ControlDimension, ControlIndicator, ControlRule, ControlHeadcount, Person,
)
from apps.campus_control.sample_data import (
    SAMPLE_PERSONS, SCHEME_DEFS, DIMENSION_NAMES, INDICATOR_NAMES,
    _SCHOOL_RULES, _MAJOR_RULES, _INDICATOR_ANNUAL,
)


class Command(BaseCommand):
    help = '写入校招管控 v2 种子数据（适用范围/维度/指标/规则/人数目标/样例人员）'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='清空后重写')

    @transaction.atomic
    def handle(self, *args, **options):
        if options['force']:
            ControlHeadcount.objects.all().delete()
            ControlRule.objects.all().delete()
            ControlIndicator.objects.all().delete()
            ControlDimension.objects.all().delete()
            ControlScope.objects.all().delete()
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

        # 适用范围
        scopes = {}
        for scope_name, d in SCHEME_DEFS.items():
            s, _ = ControlScope.objects.get_or_create(
                name=scope_name, defaults={'bu': d['bu'], 'is_active': True}
            )
            scopes[scope_name] = s
        self.stdout.write(f'已写入 {len(scopes)} 个适用范围')

        # 规则
        rule_count = 0
        for scope_name, d in SCHEME_DEFS.items():
            scope = scopes[scope_name]
            sex_rules = d['sex']
            for dim_name, base in (('院校标签', _SCHOOL_RULES), ('专业标签', _MAJOR_RULES)):
                for ind_name, t, lo, hi, st in base:
                    _, created = ControlRule.objects.get_or_create(
                        scope=scope, dimension=dims[dim_name], indicator=inds[(dim_name, ind_name)],
                        defaults={'target': Decimal(str(t)), 'lo': Decimal(str(lo)),
                                  'hi': Decimal(str(hi)), 'strength': st},
                    )
                    rule_count += 1 if created else 0
            for ind_name, t, lo, hi, st in sex_rules:
                _, created = ControlRule.objects.get_or_create(
                    scope=scope, dimension=dims['性别'], indicator=inds[('性别', ind_name)],
                    defaults={'target': Decimal(str(t)), 'lo': Decimal(str(lo)),
                              'hi': Decimal(str(hi)), 'strength': st},
                )
                rule_count += 1 if created else 0
        self.stdout.write(f'已写入 {rule_count} 条规则')

        # 人数目标（指标层）
        hc_count = 0
        annual_map = _INDICATOR_ANNUAL
        base = 12

        def monthly(annual):
            b = annual // base
            rem = annual % base
            return [b + 1 if i < rem else b for i in range(base)]

        for scope_name, d in SCHEME_DEFS.items():
            scope = scopes[scope_name]
            for dim_name, ind_list in INDICATOR_NAMES.items():
                for ind_name in ind_list:
                    annual = annual_map.get(ind_name, 0)
                    _, created = ControlHeadcount.objects.get_or_create(
                        scope=scope, indicator=inds[(dim_name, ind_name)], year=2026,
                        defaults={'annual_target': annual, 'monthly_targets': monthly(annual)},
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
                },
            )
            p_count += 1 if created else 0
        self.stdout.write(f'已写入 {p_count} 名样例人员')
        self.stdout.write(self.style.SUCCESS('种子完成'))
