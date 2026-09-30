"""数据迁移：把需求(Demand)与职位(Position)的真实对象路径字段录入指标定义。

背景：0009/0010 已把候选人主表 24 个字段录入指标定义。本迁移补入需求(16)与职位(18)
共 34 个真实可引用标量字段，使「指标定义」覆盖需求与职位维度。

求值上下文（与「真实可靠」原则对齐）：
    这些指标此前无法求值，因引擎所有求值入口只构造 candidate 快照。本批次随
    0011_metricrule_demand_position（MetricRule 关联需求/职位）+ rule_trigger /
    views 的快照并入改造一同落地：规则绑定需求/职位后，引擎会把对应实体快照并入
    data，使 demand.* / position.* 可真实求值，而非「定义存在却永远算不出」的假指标。

范围（保持真实可靠）：
    - 仅纳入非敏感标量字段；需求/职位无个人敏感字段（salary_min/max 为职位级区间，纳入）。
    - 外键/一对一/多对多/JSON/审计字段已排除（非标量，无法作为点路径原子指标）。
    - 名称统一加「需求/职位」前缀，避免与候选人同名指标（如 headcount/state）冲突。
"""
from django.db import migrations


def _new_id():
    """迁移内历史模型不走 UUIDModel.save() 重载，必须显式生成主键，否则空串 PK 撞 PRIMARY。"""
    try:
        from nanoid import generate as nanoid_generate
        return nanoid_generate(size=21)
    except Exception:
        import uuid
        return uuid.uuid4().hex


# (source_path, name, data_type)
DEMAND_FIELDS = [
    ('demand.id', '需求ID', 'string'),
    ('demand.recruit_type', '需求招聘类型', 'string'),
    ('demand.code', '需求编号', 'string'),
    ('demand.title', '需求标题', 'string'),
    ('demand.headcount', '需求编制数', 'number'),
    ('demand.filled_count', '需求已招数', 'number'),
    ('demand.level', '需求级别', 'string'),
    ('demand.position_title', '需求职位名称', 'string'),
    ('demand.process_version', '需求流程版本', 'string'),
    ('demand.jd', '需求JD', 'string'),
    ('demand.requirements', '需求任职要求', 'string'),
    ('demand.state', '需求状态', 'string'),
    ('demand.priority', '需求优先级', 'string'),
    ('demand.demand_type', '需求类型', 'string'),
    ('demand.submitted_at', '需求提交时间', 'date'),
    ('demand.approved_at', '需求审批时间', 'date'),
]

POSITION_FIELDS = [
    ('position.id', '职位ID', 'string'),
    ('position.recruit_type', '职位招聘类型', 'string'),
    ('position.code', '职位编号', 'string'),
    ('position.title', '职位标题', 'string'),
    ('position.description', '职位描述', 'string'),
    ('position.requirements', '职位任职要求', 'string'),
    ('position.level', '职位级别', 'string'),
    ('position.position_title', '职位名称', 'string'),
    ('position.location', '职位地点', 'string'),
    ('position.salary_min', '职位薪资下限', 'number'),
    ('position.salary_max', '职位薪资上限', 'number'),
    ('position.headcount', '职位编制数', 'number'),
    ('position.filled_count', '职位已招数', 'number'),
    ('position.priority', '职位优先级', 'string'),
    ('position.process_version', '职位流程版本', 'string'),
    ('position.state', '职位状态', 'string'),
    ('position.published_at', '职位发布时间', 'date'),
    ('position.closed_at', '职位关闭时间', 'date'),
]

ALL_FIELDS = DEMAND_FIELDS + POSITION_FIELDS


def _seed(apps, schema_editor):
    AtomicMetric = apps.get_model('metrics', 'AtomicMetric')
    for path, name, dtype in ALL_FIELDS:
        obj, created = AtomicMetric.objects.get_or_create(
            source_path=path,
            defaults={
                'id': _new_id(),
                'name': name,
                'data_type': dtype,
                'status': 'enabled',
                'auto_generated': False,
            },
        )
        if not created:
            dirty = False
            if obj.name != name:
                obj.name = name
                dirty = True
            if obj.data_type != dtype:
                obj.data_type = dtype
                dirty = True
            if obj.status != 'enabled':
                obj.status = 'enabled'
                dirty = True
            if dirty:
                obj.save(update_fields=['name', 'data_type', 'status', 'updated_at'])


def _unseed(apps, schema_editor):
    AtomicMetric = apps.get_model('metrics', 'AtomicMetric')
    paths = [p for p, _n, _d in ALL_FIELDS]
    AtomicMetric.objects.filter(source_path__in=paths).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('metrics', '0011_metricrule_demand_position'),
    ]

    operations = [
        migrations.RunPython(_seed, _unseed),
    ]
