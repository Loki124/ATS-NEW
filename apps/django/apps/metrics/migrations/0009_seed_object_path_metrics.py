"""数据迁移：把候选人主表对象路径指标初始化进「指标定义」。

背景：指标定义视图（MetricDefinitionViewSet）合并原子指标（对象路径）与派生指标
（参数化 Handler）。此前仅手工建了 4 条原子指标（年龄 / 出生日期 / 性别 / 院校标签），
导致指标定义里对象路径类指标不全。

本迁移把候选人的**主表白名单字段**（candidate_snapshot.BASIC_FIELDS）全部落库为
AtomicMetric（valueMode=object_path），使指标定义覆盖所有真实可引用的对象路径字段。

范围说明（避免弄虚作假）：
    - 仅初始化 14 个主表字段（真实业务对象路径），不含动态字段。
    - 动态字段（apps.dynamic_field）当前多为 QA/smoke 测试产物
      （candidate.smoke_test_address / candidate.阿斯蒂芬 …），落库会污染指标定义，
      故不纳入；真实动态字段应在其创建流程中另行初始化。
    - 既有的 4 条原子指标（age/birth_date/gender/school_tag）已存在，本迁移只补缺失的 10 条，
      逆操作仅删除本迁移新增的 10 条，不动既有数据。
"""
from django.db import migrations

# 本次新增的 10 条（候选主表字段，缺于既有 4 条之外）
NEW_OBJECT_PATH_FIELDS = [
    ('candidate.id', '候选人ID', 'string'),
    ('candidate.name', '姓名', 'string'),
    ('candidate.highest_education', '最高学历', 'string'),
    ('candidate.work_years', '工作年限', 'number'),
    ('candidate.current_city', '当前城市', 'string'),
    ('candidate.expected_city', '期望城市', 'string'),
    ('candidate.current_company', '当前公司', 'string'),
    ('candidate.current_position', '当前职位', 'string'),
    ('candidate.major_tag', '专业标签', 'string'),
    ('candidate.resume_score', '简历评分', 'number'),
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


def _seed_object_path_metrics(apps, schema_editor):
    AtomicMetric = apps.get_model('metrics', 'AtomicMetric')
    for path, name, dtype in NEW_OBJECT_PATH_FIELDS:
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
            # 已存在（理论上不会，因这 10 条此前不存在）—— 保底补齐字段，避免静默漏建
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


def _unseed_object_path_metrics(apps, schema_editor):
    # 仅删除本迁移新增的 10 条，保留迁移前既有的 age/birth_date/gender/school_tag
    AtomicMetric = apps.get_model('metrics', 'AtomicMetric')
    new_paths = [p for p, _n, _d in NEW_OBJECT_PATH_FIELDS]
    AtomicMetric.objects.filter(source_path__in=new_paths).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('metrics', '0008_atomic_metric_enum_values'),
    ]

    operations = [
        migrations.RunPython(_seed_object_path_metrics, _unseed_object_path_metrics),
    ]
