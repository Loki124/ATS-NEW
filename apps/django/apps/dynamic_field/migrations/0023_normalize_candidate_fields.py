"""数据迁移：规范化候选人动态字段（补板块 / 去垃圾 / 归一化 key / 补全类型）。

背景（2026-10 全量治理）:
    指标定义长期只收录了主表字段，候选人动态字段几乎全部缺席。根因有三层:
        1. 候选人侧 66 个动态字段里有 64 个**不属于任何板块** —— 板块体系只在
           Demand/Position 落地了，候选人侧从未建过（"业务板块字段没纳入"的真正原因）
        2. 57 个 field_key 是 'Birth Date (Age)' 这类**显示标签**而非 snake_case，
           无法作为 source_path（模型 help_text 即约定「字段 key (snake_case)」）
        3. 8 个 field_type 为空（该字段有 choices + default，空值属脏数据），
           另有 excel / test_confirm_smoke 两个测试遗留字段混入

本迁移做四件事（顺序有依赖，不可调换）:
    1. 建候选人业务板块：候选人信息 / 求职意向 / 工作经历 / 项目经历 / 教育背景 /
       技能语言 / 证书荣誉。其中工作经历、项目经历、教育背景、技能语言、证书荣誉
       是**数组条目内的子字段**（一个字段定义对应 N 条经历，索引未知），
       已登记进 signals._MANUAL_PATH_MODULES，信号不会为它们自动推断 source_path
    2. 软删 2 个测试遗留 + 3 个与 snake_case 字段重复的字段
       —— 必须先于改名执行：dynamic_fields 的 unique_together 是
       (resource, field_key)，且软删行仍占用 key，不先软删则改名必然撞约束
    3. 57 个标签式 field_key 归一化为 snake_case
    4. 补全 8 个空 field_type，并按语义把字段归入对应板块

不做的事（留给 0027 backfill 迁移处理）:
    - 不建 / 不改任何 AtomicMetric。改名后 source_path 与主表指标重复的字段
      （如 name / gender 与主表同路径），由 backfill 的幂等检查自动跳过
    - 不动已软删的历史字段
"""
from django.db import migrations
from django.utils import timezone
from nanoid import generate as nanoid_generate

# 候选人业务板块：(code, 显示名, 排序)。id 取与既有数据一致的 code。
MODULES = [
    ('candidate', '候选人信息', 10),
    ('expectation', '求职意向', 20),
    ('work', '工作经历', 30),
    ('project', '项目经历', 40),
    ('edu', '教育背景', 50),
    ('skill', '技能语言', 60),
    ('certificate', '证书荣誉', 70),
]

# 软删：测试遗留 2 个 + 与 snake_case 字段重复的标签式字段
#
# 取舍说明：dynamic_fields 的 unique_together 是 (resource, field_key)，且**软删行仍占用
# key**。因此当同名的 snake_case 字段仍在库中时，标签式的 'Current company' 永远改不成
# current_company。故对重复项一律「保留 snake_case 版本、软删标签版本」：
#     - 'Current company' / 'Current title' / 'Expected salary'  → 已有 current_company /
#       current_title / expected_salary，语义相同，软删标签版
#     - 'highest_education' → 已由改名后的 highest_degree 承担（'Highest degree' 能改名
#       是因为库中不存在 highest_degree），软删旧的一条
# 而 'Highest degree' → highest_degree 改名成功，保留。
DEPRECATE_KEYS = {
    'excel',               # 「薪资流水」，测试导入残留，field_type 为空
    'test_confirm_smoke',  # 「测试确认题」，冒烟测试残留
    'Current company',     # 与 current_company 重复（最近公司 vs 当前公司）
    'Current title',       # 与 current_title 重复
    'Expected salary',     # 与 expected_salary 重复（单位标注有差异，均被薪资敏感规则拦截）
    'highest_education',   # 已由 highest_degree 承担
}

# 标签式 field_key → snake_case。57 条，与现存非规范字段一一对应。
KEY_MAP = {
    'Name': 'name',
    'Gender': 'gender',
    'About me': 'about_me',
    'Birth Date (Age)': 'birth_date_age',
    'Mobile': 'mobile',
    'WeChat': 'wechat',
    'Email': 'email',
    'Political affiliation': 'political_affiliation',
    'Registered birthplace': 'registered_birthplace',
    'Highest degree': 'highest_degree',
    'Work experience': 'work_experience',
    'Upload ID photo (portrait side)': 'id_card_photo_front',
    'Upload ID photo (national emblem side)': 'id_card_photo_back',
    'Issuing authority': 'id_card_issuing_authority',
    'ID card validity period': 'id_card_validity_period',
    'ID number': 'id_card_number',
    'Country/Region': 'country_region',
    'Ethnicity': 'ethnicity',
    'Residence address': 'residence_address',
    'Hobbies': 'hobbies',
    'Graduation date': 'graduation_date',
    'Major': 'major',
    'Current company': 'current_company',
    'Industry': 'industry',
    'Current title': 'current_title',
    'Location': 'location',
    'Current salary': 'current_salary',
    'Expected salary': 'expected_salary',
    'Onboarding time': 'onboarding_time',
    'Expected city': 'expected_city',
    'Expected industry': 'expected_industry',
    'Rating': 'rating',
    'Resume update time': 'resume_update_time',
    'Start date': 'start_date',
    'School': 'school',
    'Degree': 'degree',
    'Company': 'company',
    'Current department': 'current_department',
    'Job title': 'job_title',
    'Responsibilities': 'responsibilities',
    'Team leader': 'team_leader',
    'Work location': 'work_location',
    'Company size': 'company_size',
    'Company type': 'company_type',
    'Salary': 'salary',
    'Reason for leaving': 'reason_for_leaving',
    'No. of subordinates': 'no_of_subordinates',
    'End date': 'end_date',
    'Project name': 'project_name',
    'Organizational role': 'organizational_role',
    'Project description': 'project_description',
    'Language': 'language',
    'Proficiency': 'proficiency',
    'Listening and speaking': 'listening_and_speaking',
    'Reading and writing': 'reading_and_writing',
    'Award time': 'award_time',
    'Award name': 'award_name',
}

# 空 field_type 补全：按 label 语义推断（字段有 choices + default，空值属脏数据）
TYPE_MAP = {
    'Political affiliation': 'LIST_SINGLE',  # 政治面貌：中共党员/群众/其他
    'Work experience': 'TEXT',                # 经历集合标记，归工作经历板块
    'Country/Region': 'REGION',
    'Current salary': 'NUMBER',
    'Expected industry': 'TEXT',
    'Resume update time': 'DATE',
    'Salary': 'NUMBER',
    'End date': 'DATE',
}

# 字段归组：现 field_key（改名后）→ 板块 code
MODULE_ASSIGN = {
    # 候选人信息：顶层属性，值在快照顶层 key，信号可自动映射
    'name': 'candidate', 'gender': 'candidate', 'about_me': 'candidate',
    'birth_date_age': 'candidate', 'mobile': 'candidate', 'wechat': 'candidate',
    'email': 'candidate', 'political_affiliation': 'candidate',
    'registered_birthplace': 'candidate', 'country_region': 'candidate',
    'ethnicity': 'candidate', 'residence_address': 'candidate', 'hobbies': 'candidate',
    'highest_degree': 'candidate', 'location': 'candidate', 'rating': 'candidate',
    'resume_update_time': 'candidate', 'source_channel': 'candidate',
    'id_card_photo_front': 'candidate', 'id_card_photo_back': 'candidate',
    'id_card_issuing_authority': 'candidate', 'id_card_validity_period': 'candidate',
    'id_card_number': 'candidate',
    # 求职意向：顶层属性，可自动映射（薪资类另被敏感 key 规则拦截）
    'expected_salary': 'expectation', 'current_salary': 'expectation',
    'onboarding_time': 'expectation', 'expected_city': 'expectation',
    'expected_industry': 'expectation', 'available_date': 'expectation',
    'years_experience': 'expectation',
    # 以下为数组条目内的子字段：source_path 需索引，交人工配置
    'work_experience': 'work', 'industry': 'work', 'current_company': 'work',
    'current_title': 'work', 'start_date': 'work', 'end_date': 'work',
    'company': 'work', 'current_department': 'work', 'job_title': 'work',
    'responsibilities': 'work', 'team_leader': 'work', 'work_location': 'work',
    'company_size': 'work', 'company_type': 'work', 'salary': 'work',
    'reason_for_leaving': 'work', 'no_of_subordinates': 'work',
    'project_name': 'project', 'organizational_role': 'project',
    'project_description': 'project',
    'graduation_date': 'edu', 'school': 'edu', 'degree': 'edu', 'major': 'edu',
    'language': 'skill', 'proficiency': 'skill',
    'listening_and_speaking': 'skill', 'reading_and_writing': 'skill',
    'award_time': 'certificate', 'award_name': 'certificate',
}

# 板块 code → 是否为数组类（数组类字段不自动映射指标）
_ARRAY_MODULES = {'work', 'project', 'edu', 'skill', 'certificate'}


def _forwards(apps, schema_editor):
    FieldModule = apps.get_model('dynamic_field', 'FieldModule')
    DynamicField = apps.get_model('dynamic_field', 'DynamicField')
    now = timezone.now()

    # ── 1. 建候选人业务板块 ────────────────────────────────────────────────
    # 按 (resource, code) 查找而非 id：FieldModule.id 是 nanoid 主键，且候选人信息
    # 板块早已存在（code='candidate'），必须复用而不是重复插入撞 (resource, code) 唯一约束。
    # id 需显式生成：RunPython 里的历史模型不含模型自定义 save()，不会自动补主键。
    for code, name, order in MODULES:
        module = FieldModule.objects.filter(resource='Candidate', code=code).first()
        if module:
            continue
        FieldModule.objects.create(
            id=nanoid_generate(size=21),
            resource='Candidate',
            code=code,
            name=name,
            order_index=order,
            is_active=True,
        )

    # ── 2. 先软删：必须早于改名（软删行仍占用 (resource, field_key)）────────
    # 直接 update 而非 .soft_delete()：RunPython 的历史模型不含具体模型自定义方法
    DynamicField.objects.filter(
        resource='Candidate', field_key__in=DEPRECATE_KEYS, deleted_at__isnull=True,
    ).update(deleted_at=now, updated_at=now)

    # ── 3. 归一化 field_key ──────────────────────────────────────────────
    # 目标 key 若已被任意行占用（含软删行），跳过 —— 宁可少改，也不撞唯一约束
    taken = set(
        DynamicField.objects.filter(resource='Candidate').values_list('field_key', flat=True)
    )
    renamed = {}
    for old_key, new_key in KEY_MAP.items():
        if new_key in taken:
            continue
        field = DynamicField.objects.filter(
            resource='Candidate', field_key=old_key, deleted_at__isnull=True,
        ).first()
        if not field:
            continue
        DynamicField.objects.filter(pk=field.pk).update(field_key=new_key, updated_at=now)
        taken.discard(old_key)
        taken.add(new_key)
        renamed[old_key] = new_key

    # ── 4. 补全空 field_type ─────────────────────────────────────────────
    for old_key, field_type in TYPE_MAP.items():
        key = renamed.get(old_key, old_key)
        DynamicField.objects.filter(
            resource='Candidate', field_key=key, field_type='', deleted_at__isnull=True,
        ).update(field_type=field_type, updated_at=now)

    # ── 5. 归入板块 ───────────────────────────────────────────────────────
    for key, module_code in MODULE_ASSIGN.items():
        module = FieldModule.objects.filter(resource='Candidate', code=module_code).first()
        if not module:
            continue
        DynamicField.objects.filter(
            resource='Candidate', field_key=key, deleted_at__isnull=True,
        ).update(module=module, updated_at=now)


def _backwards(apps, schema_editor):
    """反向还原：字段改回原 key / 清空补的类型 / 归零板块 / 恢复软删 / 删板块。

    改名还原必须以「旧 key 当前未被任何行占用」为前提：正向改名对被占用而跳过的
    字段是 no-op，若无条件改回会与占位行撞 (resource, field_key) 唯一约束。

    2026-10-21 卡 B5：占用判定改到 **Python 侧**做。
    原来用 ``filter(field_key=old_key).exists()`` 在 DB 侧判定 —— 测试库是 MySQL，
    ``utf8mb4_unicode_ci`` 排序规则**大小写不敏感** → 查 'Name' 会命中改名后的
    'name' 行 → 判定为「旧 key 被占用」→ **改名还原被整段跳过**（反向迁移在 MySQL 上
    实际失效）。SQLite 时代大小写敏感，才没暴露。
    """
    FieldModule = apps.get_model('dynamic_field', 'FieldModule')
    DynamicField = apps.get_model('dynamic_field', 'DynamicField')

    # 1. 先还原 key（此时软删行仍占位，能正确识别出「正向跳过改名」的字段）
    #    占用集合在 Python 侧构建 —— 与正向迁移的 `taken` 口径一致（大小写敏感）。
    taken = set(
        DynamicField.objects.filter(resource='Candidate').values_list('field_key', flat=True)
    )
    for old_key, new_key in KEY_MAP.items():
        if old_key in taken:
            continue
        DynamicField.objects.filter(
            resource='Candidate', field_key=new_key, deleted_at__isnull=True,
        ).update(field_key=old_key)
        taken.discard(new_key)
        taken.add(old_key)

    # 2. 清空补全的 field_type
    for old_key in TYPE_MAP:
        DynamicField.objects.filter(
            resource='Candidate', field_key=old_key, deleted_at__isnull=True,
        ).update(field_type='')

    # 3. 清空板块归属
    DynamicField.objects.filter(resource='Candidate').update(module=None)

    # 4. 恢复软删（须在改名之后：先让位再复活，否则活过来的行会挡住改名）
    #    2026-10-21 卡 D3: 必须用 _base_manager —— Django 的 ModelState 会把默认
    #    manager 的**类**复制成 shim 给历史模型, 故迁移里的 `objects` 也成了
    #    SoftDeleteManager（过滤软删行）→ 用 objects 永远匹配不到要复活的软删行。
    DynamicField._base_manager.filter(
        resource='Candidate', field_key__in=DEPRECATE_KEYS,
    ).update(deleted_at=None)

    # 5. 删掉正向新建的板块（候选人信息板块早已存在，不可删）
    FieldModule.objects.filter(
        resource='Candidate', code__in=[c for c, _, _ in MODULES],
    ).exclude(code='candidate').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('dynamic_field', '0022_seed_demand_jd_requirements'),
    ]

    operations = [
        migrations.RunPython(_forwards, _backwards),
    ]