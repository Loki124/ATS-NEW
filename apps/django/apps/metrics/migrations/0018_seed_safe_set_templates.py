"""数据迁移：补建「安全集」指标模板。

为每个安全集指标（原子指标已在前序迁移 seed；派生指标由 0017 / 0013 落库）补建
MetricTemplate（模板名=指标名；operators 用合法 UnifiedOperator code；status='enabled'）。

原子指标（按 name get_or_create，应已存在，无需新建）：
  - 性别 / 年龄 / 最高学历 / 当前公司 / 需求级别 / 需求职位名称 / 职位名称
派生指标（0017 落库 + 平均工作时长 0013 落库）：
  - 跳槽频率 / 工作时长 / 平均工作时长

逆操作：仅删本迁移按 name 建的模板（用名字清单 filter(name__in=[...]).delete()）。
"""
from django.db import migrations


TEMPLATES = [
    {'name': '性别', 'kind': 'atomic', 'metric_name': '性别',
     'calc_func': None, 'params': None, 'unit': None,
     'operators': ['IS_EMPTY', 'IS_NOT_EMPTY', 'IN', 'NOT_IN'], 'param_enums': ['男', '女']},
    {'name': '年龄', 'kind': 'atomic', 'metric_name': '年龄',
     'calc_func': None, 'params': None, 'unit': None,
     'operators': ['IS_EMPTY', 'IS_NOT_EMPTY', 'GT', 'GTE', 'EQ', 'LT', 'LTE', 'BETWEEN'], 'param_enums': []},
    {'name': '最高学历', 'kind': 'atomic', 'metric_name': '最高学历',
     'calc_func': None, 'params': None, 'unit': None,
     'operators': ['IS_EMPTY', 'IS_NOT_EMPTY', 'IN', 'NOT_IN'], 'param_enums': []},
    {'name': '当前公司', 'kind': 'atomic', 'metric_name': '当前公司',
     'calc_func': None, 'params': None, 'unit': None,
     'operators': ['IS_EMPTY', 'IS_NOT_EMPTY', 'IN', 'NOT_IN'], 'param_enums': []},
    {'name': '需求级别', 'kind': 'atomic', 'metric_name': '需求级别',
     'calc_func': None, 'params': None, 'unit': None,
     'operators': ['IS_EMPTY', 'IS_NOT_EMPTY', 'IN', 'NOT_IN'], 'param_enums': []},
    {'name': '需求职位名称', 'kind': 'atomic', 'metric_name': '需求职位名称',
     'calc_func': None, 'params': None, 'unit': None,
     'operators': ['IS_EMPTY', 'IS_NOT_EMPTY', 'IN', 'NOT_IN'], 'param_enums': []},
    {'name': '职位名称', 'kind': 'atomic', 'metric_name': '职位名称',
     'calc_func': None, 'params': None, 'unit': None,
     'operators': ['IS_EMPTY', 'IS_NOT_EMPTY', 'IN', 'NOT_IN'], 'param_enums': []},
    {'name': '跳槽频率', 'kind': 'derived', 'metric_name': '跳槽频率',
     'calc_func': 'COUNT_IN_WINDOW', 'params': {'window_years': 5}, 'unit': '段',
     'operators': ['GTE'], 'param_enums': []},
    {'name': '工作时长', 'kind': 'derived', 'metric_name': '工作时长',
     'calc_func': 'TOTAL_WORK_MONTHS', 'params': {}, 'unit': '月',
     'operators': ['GTE'], 'param_enums': []},
    {'name': '平均工作时长', 'kind': 'derived', 'metric_name': '平均工作时长',
     'calc_func': 'AVG_WORK_MONTHS', 'params': {'recent_n': 0}, 'unit': '月',
     'operators': ['GT', 'GTE', 'EQ', 'LT', 'LTE', 'BETWEEN'], 'param_enums': []},
]


def _new_id():
    try:
        from nanoid import generate as nanoid_generate
        return nanoid_generate(size=21)
    except Exception:
        import uuid
        return uuid.uuid4().hex


def _seed_safe_set_templates(apps, schema_editor):
    AtomicMetric = apps.get_model('metrics', 'AtomicMetric')
    DerivedMetric = apps.get_model('metrics', 'DerivedMetric')
    MetricTemplate = apps.get_model('metrics', 'MetricTemplate')

    for spec in TEMPLATES:
        if spec['kind'] == 'atomic':
            # 原子指标应已在前序迁移 seed；get_or_create 仅作保底（defaults 基本不会触发）。
            # 历史模型在迁移中丢失 UUIDModel.save() 的 nanoid 赋值覆盖，须显式给 id 否则空 PK 撞 UNIQUE。
            metric, _ = AtomicMetric.objects.get_or_create(
                name=spec['metric_name'],
                defaults={
                    'id': _new_id(),
                    'source_path': 'candidate.extra', 'data_type': 'string', 'status': 'enabled',
                },
            )
            fk_field = 'atomic_metric'
            fk_value = metric
        else:
            # 派生指标由 0017（跳槽频率 / 工作时长）与 0013（平均工作时长）落库；get_or_create 仅保底。
            metric, _ = DerivedMetric.objects.get_or_create(
                name=spec['metric_name'],
                defaults={
                    'id': _new_id(),
                    'calc_func': spec['calc_func'],
                    'base_path': 'candidate.workExperience',
                    'params': spec['params'],
                    'data_type': 'number',
                    'unit': spec['unit'],
                    'status': 'enabled',
                },
            )
            fk_field = 'derived_metric'
            fk_value = metric

        # MetricTemplate 直写 .get_or_create 不走 clean()（避免恰好一个 FK / operators 校验拦截），
        # operators 均为合法 UnifiedOperator code，安全集内数据保证一致。
        # 历史模型在迁移中丢失 UUIDModel.save() 的 nanoid 赋值覆盖，须显式给 id 否则空 PK 撞 UNIQUE。
        MetricTemplate.objects.get_or_create(
            name=spec['name'],
            defaults={
                'id': _new_id(),
                fk_field: fk_value,
                'operators': spec['operators'],
                'param_enums': spec['param_enums'],
                'status': 'enabled',
            },
        )


def _unseed_safe_set_templates(apps, schema_editor):
    MetricTemplate = apps.get_model('metrics', 'MetricTemplate')
    MetricTemplate.objects.filter(name__in=[t['name'] for t in TEMPLATES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('metrics', '0017_seed_safe_set_derived_metrics'),
    ]

    operations = [
        migrations.RunPython(_seed_safe_set_templates, _unseed_safe_set_templates),
    ]
