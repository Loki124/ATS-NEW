"""数据迁移：初始化「安全集」两个派生指标进指标定义。

安全集（用户确认的「可干净映射」子集，本轮仅落这两个派生指标）：
  - 跳槽频率：calc_func=COUNT_IN_WINDOW，base_path=candidate.workExperience，
              params={'window_years':5}，单位 段，真实求值依赖 candidate.extra 工作经历数据
              （与平均工作时长同口径）。
  - 工作时长：calc_func=TOTAL_WORK_MONTHS，base_path=candidate.workExperience，
              params={}，单位 月。

仅新增 2 条派生指标（顺序：跳槽频率、工作时长）。
逆操作仅删除本迁移新增的 2 条，不动其他派生指标。
"""
from django.db import migrations

METRICS = [
    {
        'name': '跳槽频率',
        'calc_func': 'COUNT_IN_WINDOW',
        'base_path': 'candidate.workExperience',
        'params': {'window_years': 5},
        'unit': '段',
        'description': '近N年内工作经历段数（跳槽频率）',
    },
    {
        'name': '工作时长',
        'calc_func': 'TOTAL_WORK_MONTHS',
        'base_path': 'candidate.workExperience',
        'params': {},
        'unit': '月',
        'description': '所有工作经历累计月数',
    },
]


def _new_id():
    """迁移内历史模型不走 UUIDModel.save() 重载，必须显式生成主键，否则空串 PK 撞 PRIMARY。

    优先复刻 UUIDModel 的 nanoid(size=21)；不可用时退回 uuid4 hex（32 位，适配 id 字段长度）。
    """
    try:
        from nanoid import generate as nanoid_generate
        return nanoid_generate(size=21)
    except Exception:
        import uuid
        return uuid.uuid4().hex


def _seed_safe_set_derived_metrics(apps, schema_editor):
    DerivedMetric = apps.get_model('metrics', 'DerivedMetric')
    for spec in METRICS:
        obj, created = DerivedMetric.objects.get_or_create(
            name=spec['name'],
            defaults={
                'id': _new_id(),
                'calc_func': spec['calc_func'],
                'base_path': spec['base_path'],
                'params': spec['params'],
                'data_type': 'number',
                'unit': spec['unit'],
                'description': spec['description'],
                'status': 'enabled',
            },
        )
        if not created:
            # 已存在（同名指标曾被手工建立）—— 保底对齐计算函数与默认参数，避免静默错配
            dirty = False
            if obj.calc_func != spec['calc_func']:
                obj.calc_func = spec['calc_func']
                dirty = True
            if obj.base_path != spec['base_path']:
                obj.base_path = spec['base_path']
                dirty = True
            if obj.params != spec['params']:
                obj.params = spec['params']
                dirty = True
            if obj.unit != spec['unit']:
                obj.unit = spec['unit']
                dirty = True
            if obj.description != spec['description']:
                obj.description = spec['description']
                dirty = True
            if obj.status != 'enabled':
                obj.status = 'enabled'
                dirty = True
            if dirty:
                obj.save(update_fields=[
                    'calc_func', 'base_path', 'params', 'unit', 'description', 'status', 'updated_at',
                ])


def _unseed_safe_set_derived_metrics(apps, schema_editor):
    DerivedMetric = apps.get_model('metrics', 'DerivedMetric')
    DerivedMetric.objects.filter(
        name__in=[m['name'] for m in METRICS],
        calc_func__in=[m['calc_func'] for m in METRICS],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('metrics', '0016_seed_missing_core_candidate_metrics'),
    ]

    operations = [
        migrations.RunPython(_seed_safe_set_derived_metrics, _unseed_safe_set_derived_metrics),
    ]
