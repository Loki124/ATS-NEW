"""ManagementUnit 新增 data_range(JSON) 字段 —— 北森「数据范围」条件筛选器载体.

存储结构(首版): { op:'or'|'and', groups:[ {op, conditions:[{dimension,field,operator,value,includeSub}]} ] }
scope_resolver.compile_data_range_q 负责把该结构编译成行级 Q(首版仅 department 维度生效).
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_cleanup_uads_user_data_permission_rules'),
    ]

    operations = [
        migrations.AddField(
            model_name='managementunit',
            name='data_range',
            field=models.JSONField(blank=True, null=True, verbose_name='数据范围(JSON)'),
        ),
    ]
