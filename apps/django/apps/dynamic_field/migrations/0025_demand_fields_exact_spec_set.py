"""需求字段集合与规范完全一致: 软删历史遗留行 (2026-10-12)。

0024 对齐迁移只做 upsert(改标签/归类/新增), 不清除环境里先于规范存在的
历史行。dev MySQL 实测有 10 行残留(对外简称/工作职责/任职资格/职位性质/
薪资范围/期望完成日期/用人经理/用人经理上级/试用期考核目标/TBP 的旧 key,
如 employment_type / salary_budget / f_xxxx 纳米 key), 与新规范字段重复,
导致字段管理页出现重复项, 违反「调整后的字段集合与规范完全一致」。

做法: 软删(deleted_at=now)所有 resource='Demand' 且 field_key 不在
DEMAND_SPEC_FIELD_KEYS(29 个规范 key)内的行。仅软删可 restore 恢复;
DynamicFieldValue 按 (resource, entity_id, field_key) 存储, 与字段定义
无 FK, 不做删除 —— 旧值成孤儿不可见, 若将来重新加回同 key 字段值即复现。

反向: 无法知道哪些行是本迁移删的 → noop(数据对齐迁移, 不做逆操作)。
"""
from django.db import migrations
from django.utils import timezone

from apps.dynamic_field.system_fields import DEMAND_SPEC_FIELD_KEYS


def prune_legacy_demand_fields(apps, schema_editor):
    DynamicField = apps.get_model('dynamic_field', 'DynamicField')
    stale = DynamicField._base_manager.filter(
        resource='Demand', deleted_at__isnull=True,
    ).exclude(field_key__in=DEMAND_SPEC_FIELD_KEYS)
    now = timezone.now()
    count = 0
    keys = [r.field_key for r in stale]
    for row in stale:
        row.deleted_at = now
        row.save(update_fields=['deleted_at'])
        count += 1
    if count:
        print(f'[0025] 软删非规范 Demand 字段 {count} 行: {keys}')


class Migration(migrations.Migration):

    dependencies = [
        ('dynamic_field', '0024_align_demand_fields_to_spec'),
    ]

    operations = [
        # 数据对齐含删行, 无法干净逆操作 → noop
        migrations.RunPython(prune_legacy_demand_fields, migrations.RunPython.noop),
    ]