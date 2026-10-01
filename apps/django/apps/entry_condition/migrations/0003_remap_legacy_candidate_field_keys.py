"""数据迁移：把存量 ConditionItem.field 的 legacy 候选键改写为 candidate.* source_path。

背景：2026-10-01 第二轮改造，进入条件目录（GET /api/v1/expressions/fields）改为完全由
指标库驱动，CANDIDATE 字段的 `field` 直接使用 AtomicMetric.source_path（如 candidate.age），
不再使用旧的 AGE / GENDER / ... legacy 键。

本迁移把已落库的 legacy 键改写为对应的 source_path，使存量规则在 UI 与评估两端都对齐新契约：
    - UI：下拉选项以 source_path 为 value，存量规则能正确回显中文 label。
    - 评估：services._get_candidate_value 仍兼容 legacy 键（反向映射），但统一为 source_path
      后行为与新增规则完全一致，消除两套键并存带来的歧义。

仅处理 condition_type=CANDIDATE 且 field 命中 legacy 键的行；其它行不受影响。
legacy 键 → source_path 映射与 apps.entry_condition.services.LEGACY_CANDIDATE_FIELD_TO_PATH 对齐。
"""
from django.db import migrations

# legacy 候选键 → candidate.* source_path（与 services.LEGACY_CANDIDATE_FIELD_TO_PATH 对齐）
LEGACY_TO_SOURCE = {
    'AGE': 'candidate.age',
    'GENDER': 'candidate.gender',
    'HIGHEST_EDU': 'candidate.highest_education',
    'WORK_YEARS': 'candidate.work_years',
    'CURRENT_CITY': 'candidate.current_city',
    'EXPECTED_CITY': 'candidate.expected_city',
}


def _remap_forward(apps, schema_editor):
    ConditionItem = apps.get_model('entry_condition', 'ConditionItem')
    for legacy_key, source_path in LEGACY_TO_SOURCE.items():
        updated = ConditionItem.objects.filter(
            condition_type='CANDIDATE', field=legacy_key,
        ).update(field=source_path)
        if updated:
            # 迁移期日志，便于对账
            print(f'[0003] remap ConditionItem field {legacy_key} -> {source_path}: {updated} rows')


def _remap_backward(apps, schema_editor):
    # 反向操作：把 source_path 还原为 legacy 键（仅当 field 正好等于映射值）。
    ConditionItem = apps.get_model('entry_condition', 'ConditionItem')
    for legacy_key, source_path in LEGACY_TO_SOURCE.items():
        ConditionItem.objects.filter(
            condition_type='CANDIDATE', field=source_path,
        ).update(field=legacy_key)


class Migration(migrations.Migration):

    dependencies = [
        ('entry_condition', '0002_conditionitem_deleted_at_and_more'),
    ]

    operations = [
        migrations.RunPython(_remap_forward, _remap_backward),
    ]
