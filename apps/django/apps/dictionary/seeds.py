"""业务枚举字典种子（注册到数据字典注册表）。

承载原「业务码表」中需要用户可维护的枚举值——学历 / 职位类别 / 招聘渠道 /
离职原因 / 合同类型。这些类别注册为系统预置 DictionaryType（is_system=True），
初始灌入常用项，后续可在数据字典管理页继续增改删（区别于只读标准码表）。

数据来源：内部招聘业务常用枚举，人工整理；项可由业务方在字典页自由扩展。
"""

from apps.dictionary.models import DictionaryType, DictionaryItem

# (key, 名称, 英文名, 排序)
EDUCATION_ITEMS = [
    ('BELOW_HIGH_SCHOOL', '高中及以下', 'Below High School', 10),
    ('TECHNICAL_SECONDARY', '中专/中技', 'Secondary Technical', 20),
    ('JUNIOR_COLLEGE', '大专', 'Junior College', 30),
    ('BACHELOR', '本科', 'Bachelor', 40),
    ('MASTER', '硕士', 'Master', 50),
    ('DOCTOR', '博士', 'Doctor', 60),
    ('OTHER', '其他', 'Other', 70),
]

JOB_CATEGORY_ITEMS = [
    ('TECH', '技术', 'Technology', 10),
    ('PRODUCT', '产品', 'Product', 20),
    ('DESIGN', '设计', 'Design', 30),
    ('OPERATION', '运营', 'Operations', 40),
    ('MARKETING', '市场', 'Marketing', 50),
    ('SALES', '销售', 'Sales', 60),
    ('HR', '人力资源', 'Human Resources', 70),
    ('FINANCE', '财务', 'Finance', 80),
    ('LEGAL', '法务', 'Legal', 90),
    ('ADMIN', '行政', 'Administration', 100),
    ('SUPPLY_CHAIN', '供应链', 'Supply Chain', 110),
    ('MANAGEMENT', '管理', 'Management', 120),
]

RECRUIT_CHANNEL_ITEMS = [
    ('CAMPUS', '校园招聘', 'Campus Recruitment', 10),
    ('SOCIAL', '社会招聘', 'Social Recruitment', 20),
    ('INTERNAL_REFERRAL', '内部推荐', 'Internal Referral', 30),
    ('HEADHUNTER', '猎头', 'Headhunter', 40),
    ('JOB_BOARD', '招聘网站', 'Job Board', 50),
    ('AGENCY', '招聘代理机构', 'Recruitment Agency', 60),
    ('OTHER', '其他', 'Other', 70),
]

OFFBOARD_REASON_ITEMS = [
    ('COMPENSATION', '薪酬待遇', 'Compensation', 10),
    ('CAREER_DEV', '职业发展', 'Career Development', 20),
    ('WORK_LIFE', '工作生活平衡', 'Work-life Balance', 30),
    ('MANAGEMENT', '管理方式', 'Management', 40),
    ('RELOCATION', '工作地点变动', 'Relocation', 50),
    ('PERSONAL', '个人原因', 'Personal', 60),
    ('HEALTH', '健康原因', 'Health', 70),
    ('TERMINATION', '合同终止', 'Contract Termination', 80),
    ('OTHER', '其他', 'Other', 90),
]

CONTRACT_TYPE_ITEMS = [
    ('FULL_TIME', '全职', 'Full-time', 10),
    ('PART_TIME', '兼职', 'Part-time', 20),
    ('INTERN', '实习', 'Intern', 30),
    ('OUTSOURCING', '劳务派遣', 'Outsourcing', 40),
    ('LABOR_DISPATCH', '劳务外包', 'Labor Outsourcing', 50),
    ('PROBATION', '试用期', 'Probation', 60),
    ('PROJECT', '项目制', 'Project-based', 70),
    ('OTHER', '其他', 'Other', 80),
]


def _seed_type(code: str, name: str, english_name: str, description: str, items: list):
    """幂等创建字典类型及其子项（系统预置）。"""
    dtype, _ = DictionaryType.objects.update_or_create(
        code=code,
        defaults={
            'name': name,
            'english_name': english_name,
            'description': description,
        },
    )
    for key, value, english_name_i, order in items:
        DictionaryItem.objects.update_or_create(
            type=dtype,
            key=key,
            defaults={
                'value': value,
                'english_name': english_name_i,
                'sort_order': order,
                'is_active': True,
            },
        )


def seed_education_type():
    """学历字典（系统预置，可扩展）。"""
    _seed_type(
        'EDUCATION', '学历', 'Education',
        '候选人学历枚举（高中及以下/大专/本科/硕士/博士等）',
        EDUCATION_ITEMS,
    )


def seed_job_category_type():
    """职位类别字典（系统预置，可扩展）。"""
    _seed_type(
        'JOB_CATEGORY', '职位类别', 'Job Category',
        '职位职能类别枚举（技术/产品/设计/运营等）',
        JOB_CATEGORY_ITEMS,
    )


def seed_recruit_channel_type():
    """招聘渠道字典（系统预置，可扩展）。"""
    _seed_type(
        'RECRUIT_CHANNEL', '招聘渠道', 'Recruitment Channel',
        '招聘渠道枚举（校招/社招/内推/猎头等），区别于「应聘渠道」',
        RECRUIT_CHANNEL_ITEMS,
    )


def seed_offboard_reason_type():
    """离职原因字典（系统预置，可扩展）。"""
    _seed_type(
        'OFFBOARD_REASON', '离职原因', 'Offboard Reason',
        '员工离职原因枚举（薪酬/职业发展/个人原因等）',
        OFFBOARD_REASON_ITEMS,
    )


def seed_contract_type_type():
    """合同类型字典（系统预置，可扩展）。"""
    _seed_type(
        'CONTRACT_TYPE', '合同类型', 'Contract Type',
        '用工合同类型枚举（全职/兼职/实习/劳务派遣等）',
        CONTRACT_TYPE_ITEMS,
    )
