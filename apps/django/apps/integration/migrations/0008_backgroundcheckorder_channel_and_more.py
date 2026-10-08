# 背调订单步骤式改造 + 供应商渠道标记 (2026-10-08)
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('integration', '0007_backgroundcheckorder_deleted_at_and_more'),
    ]

    operations = [
        # 供应商是否系统已对接（决定「系统下单」可选范围）
        migrations.AddField(
            model_name='integrationconfig',
            name='is_system_integrated',
            field=models.BooleanField(
                default=True, db_index=True, verbose_name='系统已对接',
            ),
        ),
        # 自主背调(SELF)无真实供应商配置，config 允许为空
        migrations.AlterField(
            model_name='backgroundcheckorder',
            name='config',
            field=models.ForeignKey(
                on_delete=models.CASCADE, to='integration.IntegrationConfig',
                related_name='bg_orders',
                verbose_name='供应商配置', null=True, blank=True,
            ),
        ),
        # 下单渠道：SELF(自主背调) / SELF_ORDER(自主下单) / SYSTEM_ORDER(系统下单)
        migrations.AddField(
            model_name='backgroundcheckorder',
            name='channel',
            field=models.CharField(
                max_length=16, choices=[('SELF', '自主背调'), ('SELF_ORDER', '自主下单'), ('SYSTEM_ORDER', '系统下单')],
                default='SYSTEM_ORDER', db_index=True,
                verbose_name='下单渠道',
            ),
        ),
        # 订单备注 / 背调建议承载
        migrations.AddField(
            model_name='backgroundcheckorder',
            name='remark',
            field=models.TextField(blank=True, verbose_name='订单备注/背调建议'),
        ),
        # 是否补充背调
        migrations.AddField(
            model_name='backgroundcheckorder',
            name='is_supplementary',
            field=models.BooleanField(
                default=False, db_index=True, verbose_name='是否补充背调',
            ),
        ),
        # 父订单（补充背调关联）
        migrations.AddField(
            model_name='backgroundcheckorder',
            name='parent_order_id',
            field=models.CharField(
                max_length=32, blank=True, default='', db_index=True,
                verbose_name='父订单ID',
            ),
        ),
        # 背调建议快照（按面试官）
        migrations.AddField(
            model_name='backgroundcheckorder',
            name='bg_suggestions',
            field=models.JSONField(
                default=list, blank=True, verbose_name='背调建议快照',
            ),
        ),
    ]
