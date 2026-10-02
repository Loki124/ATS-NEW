from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('process', '0014_alter_recruitmentstage_stage_type'),
    ]

    operations = [
        # 2026-10-02: 补 stage_limit（阶段限时, 小时, 0=不限时）。
        #   此前 FE 在 addProcessLink / updateProcessLink 中发送 stageLimit，
        #   但 ProcessStageLink 模型与序列化器均无此字段，被 ModelSerializer 静默丢弃，
        #   「阶段限时」功能从未真正落库。新增可空默认 0 的列，沿用 existing 行默认不限时。
        migrations.AddField(
            model_name='processstagelink',
            name='stage_limit',
            field=models.PositiveIntegerField(
                blank=True,
                default=0,
                verbose_name='阶段限时(小时)',
                help_text='0 表示不限时',
            ),
        ),
    ]
