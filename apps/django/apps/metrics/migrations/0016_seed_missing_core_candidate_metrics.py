"""数据迁移：补入指标管理遗漏的 4 个核心候选对象路径指标。

背景：0009 注释假设 age / birth_date / gender / school_tag 4 条原子指标「已存在」，
但全仓并无任何迁移真正创建它们（0008 仅对已存在的 candidate.gender 做枚举补丁、
因该记录不存在实际是空操作）。导致指标管理本身缺 4 条核心候选指标，进入条件目录也
无法展示它们（与「进入条件应用指标管理内容」诉求直接冲突）。

本迁移把 4 条补入 AtomicMetric，使指标库与 candidate 主表白名单（candidate_snapshot.
BASIC_FIELDS）完全对齐，目录、取值、指标定义三处统一收口。

范围：仅 4 个真实候选主表标量字段；data_type 与快照对齐（age=number / birth_date=date /
gender / school_tag=string）。gender 作为普通字符串指标（无 enum），运营可在指标管理里按需开启枚举。
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


CORE_CANDIDATE_METRICS = [
    ('candidate.age', '年龄', 'number'),
    ('candidate.gender', '性别', 'string'),
    ('candidate.birth_date', '出生日期', 'date'),
    ('candidate.school_tag', '学校标签', 'string'),
]


def _seed(apps, schema_editor):
    AtomicMetric = apps.get_model('metrics', 'AtomicMetric')
    for path, name, dtype in CORE_CANDIDATE_METRICS:
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
            # 已存在（理论上不会）：保底补齐字段，避免静默漏建
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
    AtomicMetric.objects.filter(
        source_path__in=[p for p, _n, _d in CORE_CANDIDATE_METRICS]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('metrics', '0015_alter_metrictemplate_operators_and_more'),
    ]

    operations = [
        migrations.RunPython(_seed, _unseed),
    ]
