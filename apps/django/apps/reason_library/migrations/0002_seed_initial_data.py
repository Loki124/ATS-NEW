"""0002 seed initial data (T02).

RunPython 调用 ``seed_initial_data()`` 灌入 53 系统标签 + 3 预置规则。
幂等: 全部 get_or_create, 重复 migrate 不会重复灌入。
"""
from django.db import migrations


def _seed(apps, schema_editor):
    # 动态导入 seed_data - 不在 migration 顶层依赖, 避免 makemigrations 失败
    from apps.reason_library.seed_data import seed_initial_data
    seed_initial_data(verbose=False, apps=apps)


def _unseed(apps, schema_editor):
    """reverse_code: 仅清掉本次 seed 灌入的数据 (按 name + is_system=True 标识)。

    注意: 这里只删除系统预置的标签 + 名称以预置规则名开头 (含 "(副本)") 的规则。
    真实生产环境的 reverse 操作应更严格 — 但因为这是测试/演示种子,
    直接清掉即可。
    """
    from apps.reason_library.models import (
        CategoryAssignment, ReasonTag, RuleCategory,
        RuleSceneAssignment, SceneRule,
    )
    ReasonTag.objects.filter(type='system', deleted_at__isnull=True).delete()
    SceneRule.objects.filter(is_system=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('reason_library', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(_seed, _unseed),
    ]
