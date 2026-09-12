"""查重项字段目录 + 默认配置常量

查重项按「强 / 中 / 弱」三档分组（对应截图「新建候选人查重规则」抽屉）：
- 强：证件号码、拉勾用户ID、AI查疑率≥99%
- 中：手机号、邮箱
- 弱：姓名、性别、出生日期、教育经历、工作经历、实习经历

约束（截图「至少添加 1 项强查重项或中查重项」）：
规则至少需要 1 项 STRONG 或 MEDIUM 查重项，纯弱项组合不允许保存。
"""
from __future__ import annotations

# ===== 强度枚举 =====
STRENGTH_STRONG = 'STRONG'
STRENGTH_MEDIUM = 'MEDIUM'
STRENGTH_WEAK = 'WEAK'

STRENGTH_LABELS = {
    STRENGTH_STRONG: '强',
    STRENGTH_MEDIUM: '中',
    STRENGTH_WEAK: '弱',
}

# 档位顺序（前端按此顺序渲染分组）
STRENGTH_ORDER = [STRENGTH_STRONG, STRENGTH_MEDIUM, STRENGTH_WEAK]

# 合规查重所必须的最低强度要求：命中任一即通过校验
STRENGTH_REQUIRED_ANY = (STRENGTH_STRONG, STRENGTH_MEDIUM)


# ===== 查重项目录 =====
# key 为稳定标识（后续查重引擎按 key 取值），label 为展示名，hint 为悬浮说明。
DUPLICATE_FIELD_CATALOG: list[dict] = [
    {
        'strength': STRENGTH_STRONG,
        'items': [
            {
                'key': 'id_card',
                'label': '证件号码',
                'hint': '证件类型 + 证件号码完全一致即视为重复。',
            },
            {
                'key': 'channel_uid',
                'label': '拉勾用户ID',
                'hint': '渠道（拉勾）回传的候选人唯一标识完全一致即视为重复。',
            },
            {
                'key': 'ai_suspect_rate',
                'label': 'AI查疑率≥99%',
                'hint': '简历解析结果中 AI 判定为同一候选人的置信度 ≥ 99% 即视为重复。',
            },
        ],
    },
    {
        'strength': STRENGTH_MEDIUM,
        'items': [
            {
                'key': 'phone',
                'label': '手机号',
                'hint': '手机号完全一致即视为重复（忽略空格与连字符）。',
            },
            {
                'key': 'email',
                'label': '邮箱',
                'hint': '邮箱地址完全一致即视为重复（忽略大小写）。',
            },
        ],
    },
    {
        'strength': STRENGTH_WEAK,
        'items': [
            {'key': 'name', 'label': '姓名', 'hint': '姓名完全一致。'},
            {'key': 'gender', 'label': '性别', 'hint': '性别完全一致。'},
            {'key': 'birth_date', 'label': '出生日期', 'hint': '出生日期完全一致。'},
            {
                'key': 'education',
                'label': '教育经历',
                'hint': '任一段教育经历中，学校名称、起止日期、专业名称完全一致，即视为重复。',
            },
            {
                'key': 'work_experience',
                'label': '工作经历',
                'hint': (
                    '任意三段工作经历中，公司名称、起止日期、职位名称完全一致，即视为重复'
                    '（若不足三段工作经历，每段工作经历的上述信息完全一致时，即视为重复）'
                ),
            },
            {
                'key': 'internship',
                'label': '实习经历',
                'hint': '任一段实习经历中，公司名称、起止日期、职位名称完全一致，即视为重复。',
            },
        ],
    },
]

# 展平后的 key → item 映射，供序列化校验与文案回填使用
FIELD_BY_KEY: dict[str, dict] = {}
for _group in DUPLICATE_FIELD_CATALOG:
    for _item in _group['items']:
        FIELD_BY_KEY[_item['key']] = {**_item, 'strength': _group['strength']}
del _group, _item


# ===== 规则条件逻辑 =====
LOGIC_ALL = 'ALL'   # 勾选的查重项全部一致
LOGIC_ANY = 'ANY'   # 勾选的查重项中任意 N 项一致
LOGIC_CHOICES = [(LOGIC_ALL, '全部一致'), (LOGIC_ANY, '任意 N 项一致')]

# ===== 适用范围 =====
SCOPE_ALL = 'ALL'
SCOPE_CHOICES = [(SCOPE_ALL, '全局'), ('SOCIAL', '社招'), ('CAMPUS', '校招')]
SCOPE_LABELS = dict(SCOPE_CHOICES)


# ===== 默认规则（对应截图）=====
# 截图证据：
#   1. 总览页「候选人查重规则」表只有 3 行（基于证件类型 / 基于渠道ID / 基于联系方式），
#      无「（系统）」后缀；
#   2. 「编辑候选人查重规则」弹窗有 5 行，前 2 行带「（系统）」后缀且操作列只有「停用 / 启用」，
#      后 3 行操作列是「编辑 停用 删除」。
# 结论：系统内置规则 2 条（不可删除），预置的自定义规则 3 条（可编辑、可删除）。
DEFAULT_SYSTEM_RULES: list[dict] = [
    {
        'name': '基于实习经历（系统）',
        'condition_logic': LOGIC_ALL,
        'any_count': 1,
        'items': [
            {'key': 'name', 'strength': STRENGTH_WEAK},
            {'key': 'internship', 'strength': STRENGTH_WEAK},
            {'key': 'education', 'strength': STRENGTH_WEAK},
            {'key': 'birth_date', 'strength': STRENGTH_WEAK},
            {'key': 'gender', 'strength': STRENGTH_WEAK},
        ],
        'is_enabled': True,
        'is_system': True,
        'order_index': 10,
    },
    {
        'name': '基于工作经历（系统）',
        'condition_logic': LOGIC_ALL,
        'any_count': 1,
        'items': [
            {'key': 'name', 'strength': STRENGTH_WEAK},
            {'key': 'work_experience', 'strength': STRENGTH_WEAK},
            {'key': 'education', 'strength': STRENGTH_WEAK},
            {'key': 'birth_date', 'strength': STRENGTH_WEAK},
            {'key': 'gender', 'strength': STRENGTH_WEAK},
        ],
        'is_enabled': False,
        'is_system': True,
        'order_index': 20,
    },
]

# 预置的自定义规则：首次初始化一并种入，但用户可自由编辑 / 删除
DEFAULT_PRESET_RULES: list[dict] = [
    {
        'name': '基于身份证',
        'condition_logic': LOGIC_ALL,
        'any_count': 1,
        'items': [{'key': 'id_card', 'strength': STRENGTH_STRONG}],
        'is_enabled': True,
        'order_index': 30,
    },
    {
        'name': '基于渠道ID',
        'condition_logic': LOGIC_ALL,
        'any_count': 1,
        'items': [{'key': 'channel_uid', 'strength': STRENGTH_STRONG}],
        'is_enabled': True,
        'order_index': 40,
    },
    {
        'name': '基于联系方式',
        'condition_logic': LOGIC_ANY,
        'any_count': 2,
        'items': [
            {'key': 'phone', 'strength': STRENGTH_MEDIUM},
            {'key': 'email', 'strength': STRENGTH_MEDIUM},
            {'key': 'name', 'strength': STRENGTH_WEAK},
        ],
        'is_enabled': True,
        'order_index': 50,
    },
]

# 完整默认集合（系统 2 条 + 预置 3 条 = 5 条，与编辑弹窗行数一致）
DEFAULT_RULES: list[dict] = DEFAULT_SYSTEM_RULES + DEFAULT_PRESET_RULES


# ===== 重复候选人合并规则默认配置 =====
# strategies[].value 决定页面第一段「合并规则如下」的编号文案（前端按 label 渲染）。
MERGE_CONFIG_KEY = 'merge'
DEFAULT_MERGE_CONFIG: dict = {
    'enabled': True,
    'cancel_unaccepted_headhunter': True,
    'strategies': [
        {
            'key': 'resume',
            'label': '标准简历',
            'value': 'SUBJECT_ONLY',
            'options': [
                {
                    'value': 'SUBJECT_ONLY',
                    'label': '仅保留主体信息，主体完整内容覆盖非主体信息',
                },
                {
                    'value': 'MERGE_ALL',
                    'label': '合并主体与非主体信息，冲突项以主体为准',
                },
            ],
        },
        {
            'key': 'application_lock',
            'label': '申请锁定状态',
            'value': 'SUBJECT_ONLY',
            'options': [
                {
                    'value': 'SUBJECT_ONLY',
                    'label': '若拥有有效中的申请，则仅保留主体的锁定',
                },
                {
                    'value': 'KEEP_ALL',
                    'label': '保留主体与非主体各自的申请锁定状态',
                },
            ],
        },
        {
            'key': 'other_content',
            'label': '其他内容',
            'value': 'KEEP_ALL',
            'options': [
                {
                    'value': 'KEEP_ALL',
                    'label': '保留主体和非主体信息（面试记录、筛选记录、附加信息、备注等）',
                },
                {
                    'value': 'SUBJECT_ONLY',
                    'label': '仅保留主体的其他内容',
                },
            ],
        },
    ],
}


# ===== 重复申请管理默认配置（社招）=====
APPLICATION_CONFIG_KEY = 'application'
DEFAULT_APPLICATION_CONFIG: dict = {
    'enabled': True,
    'window_months': 6,
    'window_options': [
        {'value': 6, 'label': '6个月内重复申请自动管控'},
        {'value': 12, 'label': '12个月内重复申请自动管控'},
        {'value': 24, 'label': '24个月内重复申请自动管控'},
    ],
}
