from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('metrics', '0006_atomicmetric_auto_generated_atomicmetric_is_enum'),
    ]

    operations = [
        migrations.AddField(
            model_name='metrictemplate',
            name='param_config',
            field=models.JSONField(
                blank=True,
                default=dict,
                verbose_name='参数配置',
                help_text='{min, max, step, prefix, suffix, allOption}',
            ),
        ),
        migrations.AddField(
            model_name='metrictemplate',
            name='value_domain',
            field=models.JSONField(
                blank=True,
                default=dict,
                verbose_name='值域配置',
                help_text='{segments:[{min, max, step, label}]}',
            ),
        ),
        migrations.AddField(
            model_name='metrictemplate',
            name='param_enums',
            field=models.JSONField(
                blank=True,
                default=list,
                verbose_name='参数枚举',
                help_text='枚举型指标的允许取值列表',
            ),
        ),
        migrations.AddField(
            model_name='metrictemplate',
            name='param_allow_null',
            field=models.BooleanField(default=False, verbose_name='允许为空'),
        ),
    ]
