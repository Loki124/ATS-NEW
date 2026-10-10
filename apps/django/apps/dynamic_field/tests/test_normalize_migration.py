"""候选人动态字段清洗迁移（0023）的正向/反向逻辑验证。

直接调用 RunPython 函数而非 MigrationExecutor（原因见 migration_loader 的说明）。
覆盖两个已知易错点:
    1. 正向改名会因 (resource, field_key) 唯一约束而跳过部分字段
       （软删行仍占用 key）—— 反向必须能识别并跳过这些「未改名」的字段
    2. 板块 upsert 按 (resource, code) 而非主键 id，候选人信息板块早已存在需复用
"""
import pytest
from nanoid import generate as nanoid_generate

from .migration_loader import load_migration, run

pytestmark = pytest.mark.django_db

MIG = load_migration('dynamic_field', '0023_normalize_candidate_fields.py')


@pytest.fixture
def silent_signals():
    """断开动态字段→指标同步信号。

    1. 本用例造的是「信号生效之前」的历史字段；不静默的话字段一落库就被信号
       建出指标，测的就不是迁移了
    2. sender 必须用字符串 'dynamic_field.DynamicField' —— 与 signals.py 注册形式
       一致；传模型类会让 lookup_key 不匹配，disconnect 静默失败
    """
    from django.db.models.signals import post_save

    from apps.dynamic_field.signals import sync_metric_on_field

    sender_ref = 'dynamic_field.DynamicField'
    post_save.disconnect(sync_metric_on_field, sender=sender_ref)
    try:
        yield
    finally:
        post_save.connect(sync_metric_on_field, sender=sender_ref)


def _make_legacy_fields():
    """构造迁移前的历史状态：标签式 key + 空 field_type + 无板块。"""
    from apps.dynamic_field.models import DynamicField, FieldModule

    # 候选人信息板块在生产库早已存在，迁移必须复用它而非重复插入
    FieldModule.objects.get_or_create(
        resource='Candidate',
        code='candidate',
        defaults={
            'id': nanoid_generate(size=21),  # 历史模型无自定义 save()，主键需显式给出
            'name': '候选人信息',
            'order_index': 10,
        },
    )

    samples = [
        ('Name', '姓名', 'TEXT'),
        ('Gender', '性别', 'LIST_SINGLE'),
        ('Highest degree', '最高学历', 'SELECT'),
        ('Political affiliation', '政治面貌', ''),       # 空类型 → 补 LIST_SINGLE
        ('Resume update time', '简历更新时间', ''),       # 空类型 → 补 DATE
        ('Company', '公司名称', 'TEXT'),                   # → work（数组类）板块
        ('Project name', '项目名称', 'TEXT'),              # → project 板块
        ('source_channel', '简历来源', 'SELECT'),          # 已是 snake_case
        ('excel', '薪资流水', ''),                          # 测试垃圾 → 软删
        ('test_confirm_smoke', '测试确认题', 'CONFIRM'),    # 测试垃圾 → 软删
    ]
    for key, label, ftype in samples:
        DynamicField.objects.create(
            resource='Candidate', field_key=key, label=label,
            field_type=ftype or 'TEXT', options=[],
        )
    # 让 field_type 真的为空（绕开 default=TEXT）
    DynamicField.objects.filter(
        field_key__in=['Political affiliation', 'Resume update time', 'excel'],
    ).update(field_type='')

    # 同名 snake_case 字段已存在 → 标签式版本改名必然被唯一约束挡住
    DynamicField.objects.create(
        resource='Candidate', field_key='current_company', label='当前公司',
        field_type='TEXT', options=[],
    )
    # 占位软删行：key 被占用，'Salary' 无法改名成 salary
    DynamicField.objects.create(
        resource='Candidate', field_key='salary', label='薪资占位',
        field_type='NUMBER', options=[],
    ).soft_delete()


def test_normalize_forward(silent_signals):
    from apps.dynamic_field.models import DynamicField, FieldModule

    _make_legacy_fields()
    run(MIG, 'forwards')

    codes = set(FieldModule.objects.filter(resource='Candidate').values_list('code', flat=True))
    assert {'candidate', 'expectation', 'work', 'project', 'edu', 'skill', 'certificate'} <= codes

    assert DynamicField.objects.filter(resource='Candidate', field_key='name').exists()
    assert not DynamicField.objects.filter(resource='Candidate', field_key='Name').exists()

    assert DynamicField.objects.get(field_key='political_affiliation').field_type == 'LIST_SINGLE'
    assert DynamicField.objects.get(field_key='resume_update_time').field_type == 'DATE'

    for junk in ('excel', 'test_confirm_smoke'):
        assert DynamicField.objects.get(field_key=junk).deleted_at is not None

    assert DynamicField.objects.get(field_key='company').module.code == 'work'
    assert DynamicField.objects.get(field_key='project_name').module.code == 'project'

    # 被占用的 key 不改名、不报错，占位行原样保留
    assert DynamicField.objects.filter(field_key='salary').exists()
    assert DynamicField.objects.get(field_key='salary').deleted_at is not None


def test_normalize_backwards_restores(silent_signals):
    from apps.dynamic_field.models import DynamicField, FieldModule

    _make_legacy_fields()
    run(MIG, 'forwards')
    run(MIG, 'backwards')

    assert DynamicField.objects.filter(resource='Candidate', field_key='Name').exists()
    assert not DynamicField.objects.filter(resource='Candidate', field_key='name').exists()
    assert DynamicField.objects.get(field_key='Political affiliation').field_type == ''
    assert DynamicField.objects.get(field_key='excel').deleted_at is None
    assert DynamicField.objects.get(field_key='test_confirm_smoke').deleted_at is None
    # 占位的 salary 不能被反向改名成 'Salary'
    assert DynamicField.objects.filter(field_key='salary').exists()

    codes = set(FieldModule.objects.filter(resource='Candidate').values_list('code', flat=True))
    assert 'expectation' not in codes
    assert 'candidate' in codes, '早已存在的候选人信息板块不应被删'


def test_normalize_is_idempotent(silent_signals):
    """重跑正向不得产生副作用（板块不重复、字段不多建、key 不冲突）。"""
    from apps.dynamic_field.models import DynamicField, FieldModule

    _make_legacy_fields()
    run(MIG, 'forwards')
    mods_first = FieldModule.objects.filter(resource='Candidate').count()
    fields_first = DynamicField.objects.filter(resource='Candidate').count()

    run(MIG, 'forwards')  # 再跑一次

    assert FieldModule.objects.filter(resource='Candidate').count() == mods_first
    assert DynamicField.objects.filter(resource='Candidate').count() == fields_first
    assert DynamicField.objects.filter(field_key='Name').count() == 0, '改名不应被重跑还原'