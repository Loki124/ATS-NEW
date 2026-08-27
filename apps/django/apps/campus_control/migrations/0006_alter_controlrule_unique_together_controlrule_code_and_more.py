"""T01 迁移：ControlRule 增加 code（规则编号）/ is_active，唯一键含 is_active。

执行顺序（规避唯一字段默认值冲突）：
  1. 先放开旧唯一约束（避免与后续 AlterUniqueTogether 冲突）。
  2. AddField code（**非 unique**，否则存量全 '' 撞 unique 失败）。
  3. AddField is_active（默认 True）。
  4. RunPython 存量回填：按 (bu,position,level,dimension,indicator,year) 排序，
     回填 code=G0001..、is_active=True（项目铁律：migrate 集成须 fresh DB + 至少 1 行真实数据）。
  5. AlterField code 改 unique=True（回填后值已唯一）。
  6. AlterUniqueTogether 含 is_active（允许「启用原规则 + 未启用副本」共存）。
"""
from django.db import migrations, models


def _backfill_codes(apps, schema_editor):
    ControlRule = apps.get_model('campus_control', 'ControlRule')
    # 存量按 (bu,position,level,dimension,indicator,year) 排序后顺序编号
    rows = list(
        ControlRule.objects.all().order_by(
            'bu', 'position', 'level', 'dimension_id', 'indicator_id', 'year'
        )
    )
    for i, rule in enumerate(rows):
        if not rule.code:
            rule.code = f'G{(i + 1):04d}'
        rule.is_active = True
        rule.save(update_fields=['code', 'is_active'])


def _reverse_backfill(apps, schema_editor):
    # 反向：仅清空 code（is_active 反转为默认由字段定义处理）
    ControlRule = apps.get_model('campus_control', 'ControlRule')
    for rule in ControlRule.objects.all():
        rule.code = ''
        rule.save(update_fields=['code'])


class Migration(migrations.Migration):

    dependencies = [
        ('campus_control', '0005_persondimensionvalue'),
    ]

    operations = [
        # 1. 放开旧唯一约束（含 6 字段），为后续含 is_active 的唯一键做准备
        migrations.AlterUniqueTogether(
            name='controlrule',
            unique_together=set(),
        ),
        # 2. 先以非 unique 加 code（存量全 '' 若直接 unique 会撞约束）
        migrations.AddField(
            model_name='controlrule',
            name='code',
            field=models.CharField(blank=True, default='', max_length=8, verbose_name='规则编号'),
        ),
        # 3. 加 is_active（默认启用）
        migrations.AddField(
            model_name='controlrule',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='启用'),
        ),
        # 4. 存量回填：code + is_active（真实数据回归，防遮蔽类 bug）
        migrations.RunPython(_backfill_codes, _reverse_backfill),
        # 5. 回填完成后 code 已唯一，改为 unique=True
        migrations.AlterField(
            model_name='controlrule',
            name='code',
            field=models.CharField(blank=True, default='', max_length=8, unique=True, verbose_name='规则编号'),
        ),
        # 6. 唯一键含 is_active：启用原规则 + 未启用副本可共存
        migrations.AlterUniqueTogether(
            name='controlrule',
            unique_together={('bu', 'position', 'level', 'dimension', 'indicator', 'year', 'is_active')},
        ),
    ]
