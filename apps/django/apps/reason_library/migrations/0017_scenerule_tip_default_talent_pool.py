"""0017: SceneRule 新增 tip 与 default_talent_pool 两个字段 (2026-10-13)。

- tip: 配置人员编辑、终端用户在选择原因弹窗中可见的自定义提示文案 (CharField max255, 默认空)。
- default_talent_pool: 该规则预设的默认人才子库 key (CharField max32, 默认空),
  取值受限于 reason_library.models.TALENT_POOL_KEYS (6 子库)。

两列均 default='' + nullable=False, 历史行自动填充空串, 无停机、无回填。
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reason_library', '0016_alter_sceneruleversion_change_kind'),
    ]

    operations = [
        migrations.AddField(
            model_name='scenerule',
            name='tip',
            field=models.CharField(
                blank=True, default='', max_length=255, verbose_name='自定义提示',
            ),
        ),
        migrations.AddField(
            model_name='scenerule',
            name='default_talent_pool',
            field=models.CharField(
                blank=True, default='', max_length=32, verbose_name='默认人才库',
            ),
        ),
    ]
