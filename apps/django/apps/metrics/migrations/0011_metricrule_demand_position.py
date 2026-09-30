# MetricRule 关联需求/职位，作为 demand.* / position.* 对象路径指标的求值上下文。
# 注意：本迁移仅含 MetricRule 的两个外键；metrics 的 MetricTemplate 字段漂移
# （makemigrations 一并报告）属并行模板 WIP，未纳入本迁移，保持隔离。

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('demand', '0005_demand_recruit_type'),
        ('metrics', '0010_seed_candidate_object_path_metrics'),
        ('position', '0004_position_priority'),
    ]

    operations = [
        migrations.AddField(
            model_name='metricrule',
            name='demand',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='metric_rules', to='demand.demand', verbose_name='关联需求'),
        ),
        migrations.AddField(
            model_name='metricrule',
            name='position',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='metric_rules', to='position.position', verbose_name='关联职位'),
        ),
    ]
