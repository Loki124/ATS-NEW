"""校招管控 → 编制管控 资源名对齐（2026-10-19）。

数据迁移（无 schema 变更），仅把 `recruit:settings:campus_control:*` 四条资源的
`resource_name` 中的「校招管控」替换为「编制管控」，使运行库与 seed_v2_init 真源一致：
  - recruit:settings:campus_control:menu:view  校招管控     → 编制管控
  - recruit:settings:campus_control:edit       编辑校招管控 → 编辑编制管控
  - recruit:settings:campus_control:delete     删除校招管控 → 删除编制管控
  - recruit:settings:campus_control:list       校招管控列表 → 编制管控列表

幂等：Replace 只替换子串，不影响其它资源码族（campus_ambassador / campus_session 不命中前缀）。
反向迁移把「编制管控」换回「校招管控」，保证可回滚。
"""
from django.db import migrations
from django.db.models import Value, CharField
from django.db.models.functions import Replace


def forward(apps, schema_editor):
    Resource = apps.get_model('core', 'PermissionResource')
    qs = Resource.objects.filter(
        resource_code__startswith='recruit:settings:campus_control:'
    )
    qs.update(
        resource_name=Replace(
            'resource_name',
            Value('校招管控'),
            Value('编制管控'),
            output_field=CharField(max_length=64),
        )
    )


def backward(apps, schema_editor):
    Resource = apps.get_model('core', 'PermissionResource')
    qs = Resource.objects.filter(
        resource_code__startswith='recruit:settings:campus_control:'
    )
    qs.update(
        resource_name=Replace(
            'resource_name',
            Value('编制管控'),
            Value('校招管控'),
            output_field=CharField(max_length=64),
        )
    )


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0030_split_campus_resource_codes'),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
