"""数据迁移：补全候选人主表剩余对象路径指标（共 24 个）。

背景：0009 仅按 candidate_snapshot.BASIC_FIELDS 白名单初始化了 14 个候选对象路径指标。
经运行时内省，Candidate 模型真实可引用的标量字段共 24 个（剔除审计/敏感/外键/JSON）。
本迁移补入其余 10 个，使指标定义覆盖候选人的全部真实对象路径字段。

范围（保持「真实可靠」原则）：
    - 仅纳入非敏感标量字段；敏感字段（phone/email/id_card/salary 及其哈希）已排除。
    - 仅候选主表字段；外键/一对多/多对多/JSON 不纳入（非标量，无法作为点路径原子指标）。
    - 这 10 个字段走既有 candidate 快照，引擎可真实求值，不造假。
    - demand / position 字段因引擎尚无其快照上下文（求值必 FAIL），不在本迁移范围，
      单独与用户确认后再行录入（避免定义存在却永远算不出的假指标）。
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


# 本次新增的 10 个候选主表字段（source_path, name, data_type）
# archived_at 为 DateTimeField，指标系统仅支持 date 粒度，按 date 入库（type_cast 兼容带时间 ISO）。
EXTRA_CANDIDATE_FIELDS = [
    ('candidate.recruit_type', '招聘类型', 'string'),
    ('candidate.resume_file_url', '简历文件地址', 'string'),
    ('candidate.resume_text', '简历文本', 'string'),
    ('candidate.referral_type', '内推类型', 'string'),
    ('candidate.current_state', '候选人当前状态', 'string'),
    ('candidate.is_blacklisted', '是否黑名单', 'boolean'),
    ('candidate.blacklist_reason', '黑名单原因', 'string'),
    ('candidate.moka_candidate_id', 'Moka候选人ID', 'string'),
    ('candidate.is_archived', '是否归档', 'boolean'),
    ('candidate.archived_at', '归档时间', 'date'),
]


def _seed_extra_candidate_metrics(apps, schema_editor):
    AtomicMetric = apps.get_model('metrics', 'AtomicMetric')
    for path, name, dtype in EXTRA_CANDIDATE_FIELDS:
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


def _unseed_extra_candidate_metrics(apps, schema_editor):
    AtomicMetric = apps.get_model('metrics', 'AtomicMetric')
    new_paths = [p for p, _n, _d in EXTRA_CANDIDATE_FIELDS]
    AtomicMetric.objects.filter(source_path__in=new_paths).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('metrics', '0009_seed_object_path_metrics'),
    ]

    operations = [
        migrations.RunPython(_seed_extra_candidate_metrics, _unseed_extra_candidate_metrics),
    ]
