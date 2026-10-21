"""S5-19：把 RotationArrangement.stage 从普通 CharField 改为 django_fsm.FSMField。

DB 层 FSMField 即 CharField（同 VARCHAR），本迁移不改变列结构、不迁数据；
现有 PENDING/ONGOING 等记录原值保留。protected=True 由模型层在描述符层面拦截
任意直写，流转只经 @transition 方法（见 models.py）。
"""
import django_fsm
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('campus_rotation', '0006_alter_classroom_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='rotationarrangement',
            name='stage',
            field=django_fsm.FSMField(
                choices=[
                    ('PENDING', '待分配'),
                    ('APPROVING', '审批中'),
                    ('ONGOING', '轮岗中'),
                    ('DONE', '已完成'),
                    ('TERMINATED', '已终止'),
                ],
                db_index=True,
                default='PENDING',
                max_length=16,
                protected=True,
                verbose_name='阶段',
            ),
        ),
    ]
