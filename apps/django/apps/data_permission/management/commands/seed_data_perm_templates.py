"""预置内置数据权限模板（幂等 upsert，可重复执行）。

与 seed_v2_init.py 拆开：权限模板是「业务规则预设」，与 RBAC 种子数据
（资源/角色/权限点）生命周期不同，单独成命令便于按需执行。

当前预置：
  DPT0001 本部门及所辖部门 —— 需求所属部门「包含」我的负责部门。
  DPT0002 本部门及下级     —— 需求所属部门属于我的负责部门或其子树。
两者即动态取值能力的开箱即用形态：管理员在角色的数据权限里引用，
即可配出等价规则，无需手工去选动态来源 + 包含关系。

幂等策略：按 code upsert。已存在的模板默认不覆盖 groups/params，
避免管理员在 UI 上改过模板后被下次 seed 悄悄重置（需显式 --reset）。
"""
from django.core.management.base import BaseCommand
from django.db import transaction

BUILTIN_TEMPLATES = [
    {
        'code': 'DPT0001',
        'name': '本部门及所辖部门',
        'module_key': 'demand',
        'description': '需求所属部门包含当前用户的负责部门（含其任 leader 的部门）。适合部门负责人查看上级口径需求。',
        'params': [
            {
                'key': 'relation', 'label': '包含关系', 'valueType': 'text',
                'required': True, 'default': 'contains',
                'enum': ['exact', 'in_subtree', 'contains', 'overlap'],
            }
        ],
        'groups': [
            {
                'expr': '',
                'conditions': [
                    {
                        'kind': 'relationship',
                        'dimension': 'dept',
                        'valueSource': 'dynamic',
                        'dynamicKey': 'currentUser.departments',
                        'relation': '${relation}',
                    }
                ],
            }
        ],
    },
    {
        'code': 'DPT0002',
        'name': '本部门及下级',
        'module_key': 'demand',
        'description': '需求所属部门是当前用户负责部门本身或其下级（部门负责人看本部门全部需求）。',
        'params': [
            {
                'key': 'relation', 'label': '包含关系', 'valueType': 'text',
                'required': True, 'default': 'in_subtree',
                'enum': ['exact', 'in_subtree', 'contains', 'overlap'],
            }
        ],
        'groups': [
            {
                'expr': '',
                'conditions': [
                    {
                        'kind': 'relationship',
                        'dimension': 'dept',
                        'valueSource': 'dynamic',
                        'dynamicKey': 'currentUser.departments',
                        'relation': '${relation}',
                    }
                ],
            }
        ],
    },
]


class Command(BaseCommand):
    help = '预置内置数据权限模板（幂等，按 code upsert）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='同时覆盖已存在模板的 groups/params（默认不覆盖，避免重置管理员改动）',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        from apps.data_permission.models import DataPermTemplate

        reset = options.get('reset')
        created = updated = skipped = 0

        for spec in BUILTIN_TEMPLATES:
            code = spec['code']
            name = spec['name']
            obj = DataPermTemplate.all_objects.filter(code=code).first()
            if obj is None:
                DataPermTemplate.objects.create(
                    code=code,
                    name=name,
                    module_key=spec['module_key'],
                    description=spec['description'],
                    params=spec['params'],
                    groups=spec['groups'],
                    version=1,
                )
                created += 1
                self.stdout.write('  + 创建 {} {}'.format(code, name))
                continue

            if reset:
                obj.name = name
                obj.module_key = spec['module_key']
                obj.description = spec['description']
                obj.params = spec['params']
                obj.groups = spec['groups']
                obj.version = (obj.version or 1) + 1
                obj.deleted_at = None
                obj.save()
                updated += 1
                self.stdout.write('  ~ 覆盖 {} {}（版本升至 v{}）'.format(code, name, obj.version))
            elif obj.deleted_at is not None:
                obj.restore()
                updated += 1
                self.stdout.write('  ~ 恢复 {} {}'.format(code, name))
            else:
                skipped += 1
                self.stdout.write('  = 跳过 {}（已存在，加 --reset 可覆盖）'.format(code))

        self.stdout.write(
            self.style.SUCCESS(
                '数据权限模板预置完成：新建 {} / 覆盖或恢复 {} / 跳过 {}'.format(
                    created, updated, skipped)
            )
        )