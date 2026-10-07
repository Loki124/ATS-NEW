from django.db import migrations, models


def backfill_template_calc_params(apps, schema_editor):
    """把定义层 DerivedMetric.params（实际取值）回填到引用它的模板 calc_params，
    并把定义单位回填到模板 unit，保证存量模板求值与展示行为不变。

    必须在 RemoveField('derivedmetric','params') 之前执行——此时 params 列仍存在可读。
    """
    MetricTemplate = apps.get_model('metrics', 'MetricTemplate')
    for tpl in MetricTemplate.objects.all().select_related('derived_metric', 'atomic_metric'):
        metric = tpl.derived_metric or tpl.atomic_metric
        if metric is None:
            continue
        if tpl.derived_metric_id and tpl.derived_metric.params:
            tpl.calc_params = dict(tpl.derived_metric.params)
        if not tpl.unit and getattr(metric, 'unit', ''):
            tpl.unit = metric.unit
        tpl.save(update_fields=['calc_params', 'unit'])


def reverse_backfill(apps, schema_editor):
    # 反向迁移：仅清空模板 calc_params / unit（不回写定义层，定义层已无 params 列）
    MetricTemplate = apps.get_model('metrics', 'MetricTemplate')
    MetricTemplate.objects.update(calc_params={}, unit='')


class Migration(migrations.Migration):
    dependencies = [
        ('metrics', '0020_seed_position_profile_metrics'),
    ]

    operations = [
        # 1) 先加模板侧字段，以便回填
        migrations.AddField(
            model_name='metrictemplate',
            name='calc_params',
            field=models.JSONField(blank=True, default=dict, verbose_name='计算参数', help_text='参数化派生指标的实际输入值（如 {"recent_n": 3}），使用指标时生效，模板层维护'),
        ),
        migrations.AddField(
            model_name='metrictemplate',
            name='unit',
            field=models.CharField(blank=True, default='', max_length=16, verbose_name='输出单位'),
        ),
        # 2) 回填存量模板（此时 DerivedMetric.params 仍存在）
        migrations.RunPython(backfill_template_calc_params, reverse_backfill),
        # 3) 移除定义层 params 列（计算参数实际取值不再存于定义层）
        migrations.RemoveField(
            model_name='derivedmetric',
            name='params',
        ),
    ]
