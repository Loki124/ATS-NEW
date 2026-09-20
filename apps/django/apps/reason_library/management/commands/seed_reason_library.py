"""Manual seed CLI - ``python manage.py seed_reason_library`` (T02 backup).

效果: 等同 0002 migration RunPython. 在迁移已应用后, 用此命令可重置 / 重新灌入。
默认幂等; --reset 会先清掉系统预置的 tag + rule 再灌。
"""
from django.core.management.base import BaseCommand

from apps.reason_library.models import (
    CategoryAssignment, ReasonTag, RuleCategory,
    RuleSceneAssignment, SceneRule,
)
from apps.reason_library.seed_data import seed_initial_data


class Command(BaseCommand):
    help = '灌入 / 重灌 Reason Library 预置数据 (53 tags + 3 rules)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset', action='store_true',
            help='先清掉系统预置 tag (含 soft-delete) + is_system=True rule, 再灌入',
        )
        parser.add_argument(
            '--verbose', action='store_true', help='打印每条创建记录',
        )

    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write(self.style.WARNING('--reset: 清掉系统预置标签 + 系统规则 ...'))
            # 系统 tag 用 hard delete (反正 seed 重新灌)
            ReasonTag.objects.filter(type='system').delete()
            SceneRule.objects.filter(is_system=True).delete()

        result = seed_initial_data(verbose=options['verbose'])
        self.stdout.write(self.style.SUCCESS(
            f"seed 完成: tags={result['tags']} rules={result['rules']} "
            f"categories={result['categories']} assignments={result['assignments']} "
            f"scenes={result['scenes']}"
        ))
