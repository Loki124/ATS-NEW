"""数据迁移：初始化「平均工作时长」派生指标进指标定义。

背景：用户要求在指标管理中增加一个「平均工作时长」指标，需同时满足：
    - 支持最近任意段数工作经历的平均工作时长（recent_n = N）
    - 包含全部工作经历的平均工作时长（recent_n = 0）

设计：注册一个参数化函数 AVG_WORK_MONTHS（见 services/derived_registry.py），
其 recent_n 参数：0 / 省略 = 全部工作经历；正整数 N = 按开始日期降序最近 N 段。
本迁移落库一条默认参数 recent_n=0（全部平均）的 DerivedMetric，使指标定义直接可见；
运营可在指标定义/模板配置里改 recent_n 得到「最近 N 段平均」，零代码。

范围说明（避免弄虚作假）：
    - 仅新增 1 条派生指标（calc_func=AVG_WORK_MONTHS）。
    - 逆操作仅删除本迁移新增的 1 条，不动其他派生指标。
"""
from django.db import migrations

METRIC_NAME = '平均工作时长'
CALC_FUNC = 'AVG_WORK_MONTHS'
BASE_PATH = 'candidate.workExperience'
DEFAULT_PARAMS = {'recent_n': 0}


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


def _seed_avg_work_months(apps, schema_editor):
    DerivedMetric = apps.get_model('metrics', 'DerivedMetric')
    obj, created = DerivedMetric.objects.get_or_create(
        name=METRIC_NAME,
        defaults={
            'id': _new_id(),
            'calc_func': CALC_FUNC,
            'base_path': BASE_PATH,
            'params': DEFAULT_PARAMS,
            'data_type': 'number',
            'unit': '月',
            'description': '平均每段工作经历的工作月数；recent_n=0 为全部工作经历平均',
            'status': 'enabled',
        },
    )
    if not created:
        # 已存在（同名指标曾被手工建立）—— 保底对齐计算函数与默认参数，避免静默错配
        dirty = False
        if obj.calc_func != CALC_FUNC:
            obj.calc_func = CALC_FUNC
            dirty = True
        if obj.base_path != BASE_PATH:
            obj.base_path = BASE_PATH
            dirty = True
        if obj.params != DEFAULT_PARAMS:
            obj.params = DEFAULT_PARAMS
            dirty = True
        if obj.status != 'enabled':
            obj.status = 'enabled'
            dirty = True
        if dirty:
            obj.save(update_fields=['calc_func', 'base_path', 'params', 'status', 'updated_at'])


def _unseed_avg_work_months(apps, schema_editor):
    DerivedMetric = apps.get_model('metrics', 'DerivedMetric')
    DerivedMetric.objects.filter(name=METRIC_NAME, calc_func=CALC_FUNC).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('metrics', '0012_seed_demand_position_object_path_metrics'),
    ]

    operations = [
        migrations.RunPython(_seed_avg_work_months, _unseed_avg_work_months),
    ]
