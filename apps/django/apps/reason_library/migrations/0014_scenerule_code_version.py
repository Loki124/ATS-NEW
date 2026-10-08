"""0014: SceneRule 增加规则编号 code (S+4) 与当前版本号 version。

- code: max_length=8, unique=True, blank=True, default=''；写入由模型 save() 事务内自动补号。
- version: PositiveIntegerField default=1, 仅展示计数, 历史内容见 SceneRuleVersion。

存量回填 (RunPython):
- 按 created_at, id 升序遍历存量规则, 依次分配 S0001, S0002, ... 避免撞 unique 约束。
- version 统一置 1 (存量规则视为首版)。
回滚: 清空 code / version 复位 1 (再跑会自动重新补号)。
"""
from django.db import migrations, models


def backfill_code_version(apps, schema_editor):
    SceneRule = apps.get_model('reason_library', 'SceneRule')
    seq = 0
    for r in SceneRule.objects.order_by('created_at', 'id'):
        seq += 1
        r.code = f'S{seq:04d}'
        if not r.version:
            r.version = 1
        r.save(update_fields=['code', 'version'])


def reverse_code_version(apps, schema_editor):
    SceneRule = apps.get_model('reason_library', 'SceneRule')
    SceneRule.objects.update(code='', version=1)


class Migration(migrations.Migration):

    dependencies = [
        ('reason_library', '0013_scenerule_modal_title'),
    ]

    operations = [
        # 安全三步: 先以「非唯一」加列 (避免对已有数据的表建唯一索引时撞重复 '' 而 IntegrityError),
        # RunPython 回填唯一 S+4 编号, 最后再 AlterField 加回 unique 约束。
        # 若首步即 unique=True + default='', 在含 >=2 行 (code 默认 '') 的表上建唯一索引会直接失败,
        # 导致 dev/prod migrate 炸库 (2026-10-08 实测 Duplicate entry '' for key 'scene_rule.code')。
        migrations.AddField(
            model_name='scenerule',
            name='code',
            field=models.CharField(
                blank=True, default='', max_length=8, verbose_name='规则编号',
            ),
        ),
        migrations.AddField(
            model_name='scenerule',
            name='version',
            field=models.PositiveIntegerField(default=1, verbose_name='当前版本号'),
        ),
        migrations.RunPython(backfill_code_version, reverse_code_version),
        migrations.AlterField(
            model_name='scenerule',
            name='code',
            field=models.CharField(
                blank=True, default='', max_length=8, unique=True, verbose_name='规则编号',
            ),
        ),
    ]
