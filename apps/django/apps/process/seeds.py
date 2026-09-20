"""招聘流程模块的内置字典种子（注册到数据字典注册表）。"""
from apps.dictionary.models import DictionaryType, DictionaryItem


def seed_recruitment_stage_type():
    """幂等创建「招聘阶段类型」字典及其 4 个阶段项。"""
    stage_type, _ = DictionaryType.objects.update_or_create(
        code='recruitment_stage_type',
        defaults={
            'name': '招聘阶段类型',
            'description': '招聘流程中各阶段的类型划分',
        },
    )
    items = [
        ('SCREEN', '筛选', 10),
        ('INVITATION', '邀约', 20),
        ('INTERVIEW', '面试', 30),
        ('OFFER', '录用', 40),
        # 系统级「起止阶段」类型：绑定初评/正式录用，不可删除/修改（is_system=True）
        ('START_END', '起止阶段', 50),
    ]
    for key, value, order in items:
        DictionaryItem.objects.update_or_create(
            type=stage_type,
            key=key,
            defaults={
                'value': value,
                'sort_order': order,
                'is_active': True,
                'is_system': key == 'START_END',
            },
        )
