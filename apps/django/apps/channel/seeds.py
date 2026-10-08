"""渠道管理模块的内置字典种子（注册到数据字典注册表）。

「应聘渠道」字典 = 候选人应聘来源渠道的枚举 single source of truth，
供候选人来源字段 / 渠道分析等场景引用。
"""
from apps.dictionary.models import DictionaryItem, DictionaryType

# (key, 名称, 英文名, 排序) —— 顺序即兵哥 2026-09-18 确认的展示顺序
APPLICATION_CHANNEL_ITEMS = [
    ('BOSS_ZHIPIN', 'Boss直聘', 'Boss Zhipin', 10),
    ('LIEPIN', '猎聘网', 'Liepin', 20),
    ('ZHAOPIN', '智联招聘', 'Zhaopin', 30),
    ('CAMPUS', '校招', 'Campus Recruitment', 40),
    ('INTERNAL_REFERRAL', '内部推荐', 'Internal Referral', 50),
    ('REHIRE', '返聘', 'Rehire', 60),
    ('SHIXISENG', '实习僧', 'Shixiseng', 70),
    ('YINGJIESHENG', '应届生求职网', 'Yingjiesheng', 80),
    ('JOB_FAIR', '招聘会', 'Job Fair', 90),
    ('HEADHUNTER', '猎头平台', 'Headhunter Platform', 100),
    ('MAIMAI', '脉脉', 'Maimai', 110),
    ('LAGOU', '拉勾', 'Lagou', 120),
    ('CITY_58', '58同城', '58.com', 130),
    ('JOB_51', '前程无忧', '51job', 140),
    ('SOUCAI', '搜才网', 'Soucai', 150),
    ('OTHER', '其它', 'Other', 160),
    ('NELIANG_PORTAL', '能良招聘门户', 'Neliang Portal', 170),
    ('SOCIAL_PORTAL', '社招门户', 'Social Recruitment Portal', 180),
    ('REFERRAL_PLATFORM', '内推平台', 'Referral Platform', 190),
]


def seed_application_channel_type():
    """幂等创建「应聘渠道」字典及其 19 个渠道项。"""
    channel_type, _ = DictionaryType.objects.update_or_create(
        code='APPLICATION_CHANNEL',
        defaults={
            'name': '应聘渠道',
            'english_name': 'Application Channel',
            'description': '候选人应聘来源渠道（Boss直聘/猎聘/内推等）',
        },
    )
    for key, value, english_name, order in APPLICATION_CHANNEL_ITEMS:
        DictionaryItem.objects.update_or_create(
            type=channel_type,
            key=key,
            defaults={
                'value': value,
                'english_name': english_name,
                'sort_order': order,
                'is_active': True,
            },
        )


# (key, 名称, 英文名, 排序) —— 顺序即兵哥 2026-09-18 确认的展示顺序
RESUME_SOURCE_ITEMS = [
    ('ACTIVE_SEARCH', '主动搜索', 'Active Search', 10),
    ('ACTIVE_APPLY', '主动投递', 'Active Application', 20),
    ('TALENT_REFERRAL', '人才推荐', 'Talent Recommendation', 30),
    ('AI_SOURCING', 'AI获取', 'AI Sourcing', 40),
    ('WEBSITE_APPLY', '官网投递', 'Career Site Application', 50),
    ('HR_REFERRAL', 'HR推荐', 'HR Referral', 60),
    ('HEADHUNTER_REFERRAL', '猎头推荐', 'Headhunter Referral', 70),
    ('WUZHAO_COMMERCIAL', '无招商业化', 'Wuzhao Commercial', 80),
    ('INTERNAL_REFERRAL', '内部推荐', 'Internal Referral', 90),
    ('TALENT_SCOUT', '才探', 'Talent Scout', 100),
]


def seed_resume_source_type():
    """幂等创建「简历来源」字典及其 10 个来源项。"""
    source_type, _ = DictionaryType.objects.update_or_create(
        code='RESUME_SOURCE',
        defaults={
            'name': '简历来源',
            'english_name': 'Resume Source',
            'description': '简历获取来源（主动搜索/主动投递/内推等）',
        },
    )
    for key, value, english_name, order in RESUME_SOURCE_ITEMS:
        DictionaryItem.objects.update_or_create(
            type=source_type,
            key=key,
            defaults={
                'value': value,
                'english_name': english_name,
                'sort_order': order,
                'is_active': True,
            },
        )
