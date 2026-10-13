"""需求新增预置列: 人才层级/职位性质/需求起止日期/需求共享人/审批状态 (2026-10-12 字段结构对齐规范)。

依据《需求字段规范》截图: 规范「预置字段」对应系统内置属性 → 落 Demand 模型列,
值由 DemandDetailSerializer 出参 camelCase 渲染, 前端 MODEL_ATTR_MAP 取值。

date_range / sharers 为 JSONField(default=list) 无 null → 空值统一存 []。

只加列不改既有列, 与 0007 无冲突(0007 单独加 talent_nature 以贴合自动生成形态)。
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('demand', '0005_demand_recruit_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='demand',
            name='talent_level',
            field=models.CharField(blank=True, default='', max_length=50, verbose_name='人才层级'),
        ),
        migrations.AddField(
            model_name='demand',
            name='date_range',
            field=models.JSONField(blank=True, default=list, verbose_name='需求起止日期'),
        ),
        migrations.AddField(
            model_name='demand',
            name='sharers',
            field=models.JSONField(blank=True, default=list, verbose_name='需求共享人'),
        ),
        migrations.AddField(
            model_name='demand',
            name='approval_status',
            field=models.CharField(
                blank=True, default='', max_length=16,
                choices=[('NONE', '未提交'), ('PENDING', '待审批'), ('APPROVED', '已通过'), ('REJECTED', '已驳回')],
                verbose_name='审批状态',
            ),
        ),
    ]