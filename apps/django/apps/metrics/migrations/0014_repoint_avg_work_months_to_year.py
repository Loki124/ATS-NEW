"""数据迁移：将「平均工作时长」派生指标的输出单位由月调整为年。

背景：用户要求「平均工作时长」按年计算（输出单位=年，而非月）。AVG_WORK_MONTHS
计算函数已支持 unit 参数（month/year，year 时结果 ÷12），本迁移把既有指标记录的
默认参数与展示单位改为年，使指标定义中该指标直接以「年」呈现。

范围说明（避免弄虚作假 / 非破坏性）：
    - 仅更新 name='平均工作时长' 且 calc_func='AVG_WORK_MONTHS' 的这一条记录：
      unit 月→年，params 由 {'recent_n':0} 改为 {'recent_n':0,'unit':'year'}，
      description 同步更新。
    - 逆操作（_unseed）将其还原为月，保证可回滚、不影响其他派生指标。
    - 运营仍可在指标管理详情弹窗把 unit 切回 month（参数化 Handler 的参数编辑器已支持）。
"""
from django.db import migrations


def _seed_avg_work_years(apps, schema_editor):
    DerivedMetric = apps.get_model('metrics', 'DerivedMetric')
    obj = DerivedMetric.objects.filter(
        name='平均工作时长', calc_func='AVG_WORK_MONTHS'
    ).first()
    if not obj:
        return
    obj.unit = '年'
    obj.params = {'recent_n': 0, 'unit': 'year'}
    obj.description = '平均每段工作经历的工作年数；recent_n=0 为全部工作经历平均'
    obj.status = 'enabled'
    obj.save(update_fields=['unit', 'params', 'description', 'status', 'updated_at'])


def _unseed_avg_work_years(apps, schema_editor):
    DerivedMetric = apps.get_model('metrics', 'DerivedMetric')
    obj = DerivedMetric.objects.filter(
        name='平均工作时长', calc_func='AVG_WORK_MONTHS'
    ).first()
    if not obj:
        return
    obj.unit = '月'
    obj.params = {'recent_n': 0}
    obj.save(update_fields=['unit', 'params', 'updated_at'])


class Migration(migrations.Migration):

    dependencies = [
        ('metrics', '0013_seed_avg_work_months'),
    ]

    operations = [
        migrations.RunPython(_seed_avg_work_years, _unseed_avg_work_years),
    ]
