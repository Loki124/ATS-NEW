# 背调订单扩展字段 + 集成配置 bg_metadata (2026-10-08)
# 新增：BackgroundCheckOrder.package_name/bg_provider/bg_time/bg_result/contactable/subject_snapshot
#       IntegrationConfig.bg_metadata（背调展示元数据：排名/标签/套餐目录）
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('integration', '0008_backgroundcheckorder_channel_and_more'),
    ]

    operations = [
        # 套餐名称（上传/下单分支冗余存选中套餐名）
        migrations.AddField(
            model_name='backgroundcheckorder',
            name='package_name',
            field=models.CharField(
                blank=True, default='', max_length=100, verbose_name='套餐名称',
            ),
        ),
        # 背调供应商（自主上传分支自由文本，无 IntegrationConfig FK）
        migrations.AddField(
            model_name='backgroundcheckorder',
            name='bg_provider',
            field=models.CharField(
                blank=True, default='', max_length=100, verbose_name='背调供应商',
            ),
        ),
        # 背调时间（上传分支「背调完成时间」）
        migrations.AddField(
            model_name='backgroundcheckorder',
            name='bg_time',
            field=models.DateTimeField(
                blank=True, null=True, verbose_name='背调时间',
            ),
        ),
        # 背调结果（HR 人工结论，独立于供应商 risk_level；空串 '' 表示未填）
        migrations.AddField(
            model_name='backgroundcheckorder',
            name='bg_result',
            field=models.CharField(
                blank=True, choices=[('PASS', '通过'), ('DOUBT', '存疑'), ('FAIL', '不通过'), ('PENDING', '待定')],
                default='', max_length=16, verbose_name='背调结果',
            ),
        ),
        # 是否可以联系候选人（下单分支「其他信息」单选；null=未选）
        migrations.AddField(
            model_name='backgroundcheckorder',
            name='contactable',
            field=models.BooleanField(
                blank=True, null=True, verbose_name='是否可以联系候选人',
            ),
        ),
        # 背调人信息快照（不建 Candidate 新列）
        migrations.AddField(
            model_name='backgroundcheckorder',
            name='subject_snapshot',
            field=models.JSONField(
                blank=True, default=dict, verbose_name='背调人信息快照',
            ),
        ),
        # 背调展示元数据（排名/标签/套餐目录；前端未配置时优雅降级）
        migrations.AddField(
            model_name='integrationconfig',
            name='bg_metadata',
            field=models.JSONField(
                blank=True, default=dict,
                help_text='交付效率/使用率排名与标签、套餐目录；前端未配置时优雅降级',
                verbose_name='背调展示元数据',
            ),
        ),
    ]
