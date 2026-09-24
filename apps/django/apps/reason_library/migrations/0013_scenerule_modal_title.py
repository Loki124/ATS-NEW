"""0013: SceneRule 新增 modal_title (终端用户选择原因弹窗的标题文案)。

空串 = 使用默认文案「选择原因」。加到已有表上, 对存量行以 default='' 回填。
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reason_library', '0012_delete_sibling_preset_rules'),
    ]

    operations = [
        migrations.AddField(
            model_name='scenerule',
            name='modal_title',
            field=models.CharField(
                blank=True, default='', max_length=64,
                help_text='终端用户选择原因弹窗的标题文案 (空=使用默认文案「选择原因」)',
                verbose_name='弹窗标题',
            ),
        ),
    ]
