"""迁移预置系统内置起止阶段: 初评(P001, is_start) / 正式录用(P099, is_end)。

项目级标准: 系统级默认数据走系统内置 (代码枚举 + 迁移预置), 不进数据字典。
本迁移幂等: 行已存在则强制修正系统不可变量, 不存在则创建, 闭合 BR-001。
"""
from django.db import migrations


def preset_start_end_stages(apps, schema_editor):
    RecruitmentStage = apps.get_model('process', 'RecruitmentStage')
    presets = [
        # code,  name,     is_start, is_end
        ('P001', '初评', True, False),
        ('P099', '正式录用', False, True),
    ]
    for code, name, is_start, is_end in presets:
        obj, _created = RecruitmentStage.objects.get_or_create(
            code=code,
            defaults={
                'name': name,
                'stage_type': 'START_END',
                'is_builtin': True,
                'is_start': is_start,
                'is_end': is_end,
                'status': 'ENABLED',
            },
        )
        # 系统不可变量始终强制正确 (即便行已存在且被手动改过)
        obj.stage_type = 'START_END'
        obj.is_builtin = True
        obj.is_start = is_start
        obj.is_end = is_end
        obj.status = 'ENABLED'
        obj.save(update_fields=['stage_type', 'is_builtin', 'is_start', 'is_end', 'status'])


def reverse_preset_start_end_stages(apps, schema_editor):
    # 不可逆: 删除/还原系统预置阶段会破坏 BR-001 与历史流程关联
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('process', '0011_reclassify_start_end_type'),
    ]

    operations = [
        migrations.RunPython(preset_start_end_stages, reverse_preset_start_end_stages),
    ]
