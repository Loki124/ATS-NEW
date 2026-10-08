"""为所有背调供应商预置标准背调套餐目录。

将用户指定的 5 个标准套餐（面试预检 / 人才审计 / 一履套餐 / 二履套餐 / 三履套餐）
写入每个 ``IntegrationConfig(type='BACKGROUND_CHECK')`` 的 ``bg_metadata['packages']``。

- 数据由用户明确指定，属权威业务数据，非占位/伪造。
- 幂等：重复执行结果一致（整体覆盖 packages，保留 bg_metadata 其它键，如排名/标签）。
- 说明：本迁移只覆盖**当前已存在**的背调供应商；后续新增供应商需在管理端自行配置
  ``bg_metadata.packages``（或另跑同等数据迁移）。
"""
from copy import deepcopy

from django.db import migrations

# 标准背调套餐目录（用户指定，按参考图忠实转录）
BG_PACKAGES = [
    {
        'token': 'interview_precheck',
        'name': '面试预检',
        'workdays': 1,
        'features': [
            '信贷风险信息', '失信记录', '个人涉诉记录',
            '不良记录查询', '身份验证', '商业利益冲突',
        ],
    },
    {
        'token': 'talent_audit',
        'name': '人才审计',
        'workdays': 1,
        'features': [
            '信贷风险信息', '失信记录', '个人涉诉记录', '欠税不良记录',
            '不良记录查询', '身份验证', '商业利益冲突',
        ],
    },
    {
        'token': 'one_experience',
        'name': '一履套餐',
        'workdays': 2,
        'features': [
            '信贷风险信息', '失信记录', '个人涉诉记录', '不良记录查询',
            '身份验证', '商业利益冲突', '教育经历', '工作履历(标准)',
        ],
    },
    {
        'token': 'two_experience',
        'name': '二履套餐',
        'workdays': 3,
        'features': [
            '信贷风险信息', '失信记录', '个人涉诉记录', '不良记录查询',
            '身份验证', '商业利益冲突', '教育经历', '工作履历(标准)*2',
        ],
    },
    {
        'token': 'three_experience',
        'name': '三履套餐',
        'workdays': 1,
        'features': [
            '信贷风险信息', '失信记录', '个人涉诉记录', '不良记录查询',
            '身份验证', '商业利益冲突', '教育经历', '工作履历(标准)*3',
        ],
    },
]


def seed_bg_packages(apps, schema_editor):
    """写入标准套餐目录（保留 bg_metadata 上的其它键）。"""
    IntegrationConfig = apps.get_model('integration', 'IntegrationConfig')
    for cfg in IntegrationConfig.objects.filter(type='BACKGROUND_CHECK'):
        meta = dict(cfg.bg_metadata or {})
        meta['packages'] = deepcopy(BG_PACKAGES)
        cfg.bg_metadata = meta
        cfg.save(update_fields=['bg_metadata'])


def unseed_bg_packages(apps, schema_editor):
    """回滚：移除本迁移写入的 packages（不动 bg_metadata 其它键）。"""
    IntegrationConfig = apps.get_model('integration', 'IntegrationConfig')
    for cfg in IntegrationConfig.objects.filter(type='BACKGROUND_CHECK'):
        meta = dict(cfg.bg_metadata or {})
        meta.pop('packages', None)
        cfg.bg_metadata = meta
        cfg.save(update_fields=['bg_metadata'])


class Migration(migrations.Migration):

    dependencies = [
        ('integration', '0009_backgroundcheckorder_bg_fields_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_bg_packages, unseed_bg_packages),
    ]
