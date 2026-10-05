"""数据迁移：种子「职位画像」可对比指标（方案 B 支撑数据）。

背景：方案 B 让指标规则支持「指标 vs 指标」比较（如候选年龄 ≤ 职位薪资上限）。
职位属性经 build_position_snapshot 已全量暴露为 position.* 点路径，本迁移把其中
可参与画像对比的标量字段建立为 AtomicMetric + MetricTemplate，使职位画像对比开箱即用。

范围：仅 position 模型既有标量字段（salary_min / salary_max / headcount / level /
priority / location），零表结构变更（纯 RunPython 数据写入）。

逆操作：删除本迁移建的模板；若对应 AtomicMetric 再无其它模板引用则一并清理，避免孤儿。
"""
from django.db import migrations


# (source_path, name, data_type, operators)
POSITION_METRICS = [
    ('position.salary_min', '职位薪资下限', 'number',
     ['IS_EMPTY', 'IS_NOT_EMPTY', 'GT', 'GTE', 'EQ', 'LT', 'LTE', 'BETWEEN']),
    ('position.salary_max', '职位薪资上限', 'number',
     ['IS_EMPTY', 'IS_NOT_EMPTY', 'GT', 'GTE', 'EQ', 'LT', 'LTE', 'BETWEEN']),
    ('position.headcount', '职位招聘人数', 'number',
     ['IS_EMPTY', 'IS_NOT_EMPTY', 'GT', 'GTE', 'EQ', 'LT', 'LTE']),
    ('position.level', '职位职级', 'string',
     ['IS_EMPTY', 'IS_NOT_EMPTY', 'EQ', 'NEQ', 'IN', 'NOT_IN']),
    ('position.priority', '职位优先级', 'string',
     ['IS_EMPTY', 'IS_NOT_EMPTY', 'EQ', 'NEQ', 'IN', 'NOT_IN']),
    ('position.location', '职位工作地点', 'string',
     ['IS_EMPTY', 'IS_NOT_EMPTY', 'EQ', 'NEQ', 'IN', 'NOT_IN', 'CONTAINS', 'NOT_CONTAINS']),
]


def _new_id():
    """迁移内历史模型不走 UUIDModel.save() 重载，必须显式生成主键，否则空串 PK 撞 UNIQUE。"""
    try:
        from nanoid import generate as nanoid_generate
        return nanoid_generate(size=21)
    except Exception:
        import uuid
        return uuid.uuid4().hex


def _seed(apps, schema_editor):
    AtomicMetric = apps.get_model('metrics', 'AtomicMetric')
    MetricTemplate = apps.get_model('metrics', 'MetricTemplate')

    for path, name, dtype, ops in POSITION_METRICS:
        metric, _created = AtomicMetric.objects.get_or_create(
            source_path=path,
            defaults={
                'id': _new_id(),
                'name': name,
                'data_type': dtype,
                'status': 'enabled',
                'auto_generated': False,
            },
        )
        if not _created:
            # 已存在（理论上不会）：保底补齐字段，避免静默漏建
            if metric.data_type != dtype:
                metric.data_type = dtype
                metric.save(update_fields=['data_type', 'updated_at'])

        # MetricTemplate 直写 .get_or_create 不走 clean()（避免恰好一个 FK / operators 校验拦截），
        # operators 均为合法 UnifiedOperator code。
        MetricTemplate.objects.get_or_create(
            name=name,
            defaults={
                'id': _new_id(),
                'atomic_metric': metric,
                'operators': ops,
                'status': 'enabled',
            },
        )


def _unseed(apps, schema_editor):
    MetricTemplate = apps.get_model('metrics', 'MetricTemplate')
    AtomicMetric = apps.get_model('metrics', 'AtomicMetric')

    names = [m[1] for m in POSITION_METRICS]
    MetricTemplate.objects.filter(name__in=names).delete()

    # 清理不再被任何模板引用的孤儿原子指标
    for path in [m[0] for m in POSITION_METRICS]:
        am = AtomicMetric.objects.filter(source_path=path).first()
        if am is not None and not am.templates.exists():
            am.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('metrics', '0019_metric_template_version'),
    ]

    operations = [
        migrations.RunPython(_seed, _unseed),
    ]
