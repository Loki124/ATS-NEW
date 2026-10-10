"""日期型模板的存量值域归一化。

背景：值域早期一律按数值 min/max/step 存（如「出生年月范围」= {min:1, max:3, step:1}）。
日期型出参没有刻度概念，1~3 既不是日期也不是可解释的区间，属无效数据；
本迁移把这类段清空（留空 = 自由区间，语义正确），并把非法的单位值归零。

不可反向：被清掉的是无法解释的无效值，没有可恢复的目标状态。
"""
from django.db import migrations

DATE_GRANULARITIES = ('年', '月', '日')


def normalize(apps, schema_editor):
    MetricTemplate = apps.get_model('metrics', 'MetricTemplate')
    AtomicMetric = apps.get_model('metrics', 'AtomicMetric')
    DerivedMetric = apps.get_model('metrics', 'DerivedMetric')
    changed = []
    for tpl in MetricTemplate.objects.all():
        metric = tpl.atomic_metric or tpl.derived_metric
        # 历史模型上 data_type 值就是 'date'
        if not metric or metric.data_type != 'date':
            continue
        dirty = False
        domain = tpl.value_domain or {}
        segs = domain.get('segments') or []
        if any(isinstance(s, dict) and ('min' in s or 'max' in s) for s in segs):
            # 数值段在日期口径下无意义 → 清空为自由区间
            domain['segments'] = []
            dirty = True
        if tpl.unit and tpl.unit not in DATE_GRANULARITIES:
            tpl.unit = ''
            dirty = True
        if dirty:
            tpl.value_domain = domain
            tpl.save(update_fields=['value_domain', 'unit'])
            changed.append(tpl.code or tpl.name)
    if changed:
        print(f'  已归一化日期型值域: {", ".join(changed)}')


def noop(apps, schema_editor):
    """无效数据无目标状态可恢复。"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('metrics', '0024_atomicmetric_code_derivedmetric_code_and_more'),
    ]

    operations = [
        migrations.RunPython(normalize, noop),
    ]
