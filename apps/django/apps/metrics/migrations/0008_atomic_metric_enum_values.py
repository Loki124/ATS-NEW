from django.db import migrations, models


def _seed_gender_enum(apps, schema_editor):
    """示例枚举指标落库：性别 出参为枚举值 [男, 女]。

    仅对既有的「性别」原子指标（source_path=candidate.gender）补 is_enum 与枚举值，
    使其成为「出参为枚举值」的可演示样本；其余指标不受影响。
    """
    AtomicMetric = apps.get_model('metrics', 'AtomicMetric')
    AtomicMetric.objects.filter(
        source_path='candidate.gender', is_enum=False,
    ).update(is_enum=True, enum_values=['男', '女'])


def _unseed_gender_enum(apps, schema_editor):
    AtomicMetric = apps.get_model('metrics', 'AtomicMetric')
    AtomicMetric.objects.filter(
        source_path='candidate.gender', is_enum=True,
    ).update(is_enum=False, enum_values=[])


class Migration(migrations.Migration):

    dependencies = [
        ('metrics', '0007_metric_template_config'),
    ]

    operations = [
        migrations.AddField(
            model_name='atomicmetric',
            name='enum_values',
            field=models.JSONField(
                blank=True,
                default=list,
                verbose_name='枚举值',
                help_text='is_enum 为 True 时的候选取值列表，如 ["男","女"]',
            ),
        ),
        migrations.RunPython(_seed_gender_enum, _unseed_gender_enum),
    ]
