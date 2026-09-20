"""软删 recruitment_stage_type 字典类型及其项 (系统级默认不再进数据字典)。

阶段类型改为系统内置枚举 (apps.process.models.StageType), 经 0012 迁移预置
起止阶段。存量库里该字典类型已无代码引用, 此处软删以彻底退出数据字典。
幂等: fresh DB 无该类型时不操作。
"""
from django.db import migrations
from django.utils import timezone


def remove_stage_type_dict(apps, schema_editor):
    DictionaryType = apps.get_model('dictionary', 'DictionaryType')
    DictionaryItem = apps.get_model('dictionary', 'DictionaryItem')
    now = timezone.now()
    dt = DictionaryType.objects.filter(
        code='recruitment_stage_type', deleted_at__isnull=True,
    ).first()
    if dt:
        DictionaryItem.objects.filter(type=dt, deleted_at__isnull=True).update(
            deleted_at=now, is_active=False,
        )
        dt.deleted_at = now
        dt.is_enabled = False
        dt.save(update_fields=['deleted_at', 'is_enabled'])


def restore_stage_type_dict(apps, schema_editor):
    DictionaryType = apps.get_model('dictionary', 'DictionaryType')
    DictionaryItem = apps.get_model('dictionary', 'DictionaryItem')
    dt = DictionaryType.objects.filter(code='recruitment_stage_type').first()
    if dt:
        DictionaryItem.objects.filter(type=dt).update(deleted_at=None, is_active=True)
        dt.deleted_at = None
        dt.is_enabled = True
        dt.save(update_fields=['deleted_at', 'is_enabled'])


class Migration(migrations.Migration):

    dependencies = [
        ('process', '0012_preset_start_end_stages'),
        ('dictionary', '0003_dictionaryitem_is_system'),
    ]

    operations = [
        migrations.RunPython(remove_stage_type_dict, restore_stage_type_dict),
    ]
