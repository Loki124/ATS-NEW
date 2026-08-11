"""T9：``Position.demand`` 外键（G1 路径 (c)）+ ``process_version`` default 翻 ``'V1.0'``（G2）。

两个操作合并在同一 migration 文件：同属 position 应用、同批交付，拆开只会多一次
``AlterField`` 的表锁窗口。

``AddField(demand)``：``null=True`` + ``SET_NULL``。**存量行 demand_id 一律 NULL**——
Demand 与 Position 此前无任何关联字段，归属关系无法反推，任何自动回填都是编造数据。
存量归属订正登记为独立数据治理项（业务提供「需求↔职位」映射后再回填）。

``AlterField(process_version)``：理由同 ``demand/0002``。dev 库 ``Position`` 实测 0 行，
本轮无需配套 UPDATE。
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('demand', '0002_alter_demand_process_version'),
        ('position', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='position',
            name='demand',
            field=models.ForeignKey(blank=True, help_text='可空：职位可脱离需求独立存在；存量职位 demand_id 一律 NULL（归属无法反推）', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='positions', to='demand.demand', verbose_name='所属需求'),
        ),
        migrations.AlterField(
            model_name='position',
            name='process_version',
            field=models.CharField(default='V1.0', max_length=20, verbose_name='流程版本'),
        ),
    ]
