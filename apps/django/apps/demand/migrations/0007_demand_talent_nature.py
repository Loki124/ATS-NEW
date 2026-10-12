"""职位性质 talent_nature: 全职/兼职/实习/外包 (2026-10-12 字段结构对齐规范)。

与 demand_type(社招/校招) 语义不同 —— 一个讲岗位用工性质, 一个讲招聘批次, 独立成列。
选项与 dynamic_field.system_fields._TALENT_NATURE_OPTIONS 对齐。
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('demand', '0006_demand_approval_status_demand_date_range_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='demand',
            name='talent_nature',
            field=models.CharField(
                blank=True, default='', max_length=16,
                choices=[('FULLTIME', '全职'), ('PARTTIME', '兼职'), ('INTERN', '实习'), ('OUTSOURCE', '外包')],
                verbose_name='职位性质',
            ),
        ),
    ]