"""0012_delete_sibling_preset_rules: 删除两条兄弟预置规则, 仅留单一「预置默认规则」。

背景 (2026-09-24 用户拍板):
- 原 seed 有 3 条预置规则: r-resume(预置默认规则) / r-cancel(预置默认规则 · 取消面试) /
  r-talent(预置默认规则 · 放入人才库)。
- 需求明确: 仅保留一条「预置默认规则」作为系统兜底 (覆盖全部场景×类型, 不可调整
  覆盖/名称/状态); 其它规则优先于它, 未覆盖时回退到它。
- 因此删除 r-cancel / r-talent 两条兄弟规则 (CASCADE 释放其分类树与场景绑定)。

幂等: 按 name 删除, 不存在则 no-op; 重跑绝对安全。
"""
from django.db import migrations


SIBLING_NAMES = [
    '预置默认规则 · 取消面试',
    '预置默认规则 · 放入人才库',
]


def _delete_siblings(apps, schema_editor):
    SceneRule = apps.get_model('reason_library', 'SceneRule')
    deleted = list(
        SceneRule.objects.filter(name__in=SIBLING_NAMES).values_list('id', 'name')
    )
    if deleted:
        SceneRule.objects.filter(name__in=SIBLING_NAMES).delete()


def _noop(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ('reason_library', '0011_ensure_rule_category_color'),
    ]

    operations = [
        migrations.RunPython(_delete_siblings, _noop),
    ]
