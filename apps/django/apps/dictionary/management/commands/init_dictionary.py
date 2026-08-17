"""初始化数据字典。

遍历字典种子注册表，幂等创建各业务模块注册的内置字典类型与字典项。
"""
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = '初始化系统数据字典（按注册表注入各业务模块的内置字典数据）'

    @transaction.atomic
    def handle(self, *args, **options):
        from apps.dictionary.registry import run_dictionary_seeds

        run_dictionary_seeds()
        self.stdout.write(self.style.SUCCESS('✓ 数据字典初始化完成'))
