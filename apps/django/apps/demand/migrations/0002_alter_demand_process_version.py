"""T9/G2：``Demand.process_version`` default ``'1.0'`` → ``'V1.0'``。

**为什么需要 migration**（规格 §4.2 曾断言"仅影响新行，无需 migration"，该断言为假）：
``default`` 参与 ``Field.deconstruct()``，autodetector 必然产出 ``AlterField``；
不落 migration 则 ``makemigrations --check`` 永远脏。

**为什么不带数据订正**：dev 库实测 ``Demand`` 0 行，无 ``'1.0'`` 残行需要 UPDATE。
若未来在有存量的库上应用，须先 ``UPDATE demands SET process_version='V1.0'
WHERE process_version='1.0'``——否则 ``time_limit`` 的版本字符串精确匹配会静默落空。
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('demand', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='demand',
            name='process_version',
            field=models.CharField(default='V1.0', max_length=20, verbose_name='流程版本'),
        ),
    ]
