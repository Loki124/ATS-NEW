"""种子校招管控默认规则与样例人员。

用法：
    python manage.py seed_campus            # 仅在空表时写入
    python manage.py seed_campus --force    # 清空后重填
"""
from django.core.management.base import BaseCommand

from apps.campus_control.models import ControlRule, Person
from apps.campus_control.sample_data import SAMPLE_PERSONS, DEFAULT_RULES


class Command(BaseCommand):
    help = '种子校招管控默认规则与样例人员（§9.0 / §2.2）'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='清空后重填')

    def handle(self, *args, **options):
        if options['force']:
            ControlRule.objects.filter(deleted_at__isnull=True).delete()
            Person.objects.filter(deleted_at__isnull=True).delete()
            self.stdout.write('已清空现有规则与人员')

        if not ControlRule.objects.filter(deleted_at__isnull=True).exists():
            for r in DEFAULT_RULES:
                ControlRule.objects.create(**r)
            self.stdout.write(self.style.SUCCESS(f'已写入 {len(DEFAULT_RULES)} 条默认规则'))
        else:
            self.stdout.write('规则已存在，跳过')

        if not Person.objects.filter(deleted_at__isnull=True).exists():
            for p in SAMPLE_PERSONS:
                Person.objects.create(**p)
            self.stdout.write(self.style.SUCCESS(f'已写入 {len(SAMPLE_PERSONS)} 名样例人员'))
        else:
            self.stdout.write('人员已存在，跳过')

        self.stdout.write(self.style.SUCCESS('种子完成'))
