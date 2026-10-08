"""数据迁移：把存量进入条件项的 field 从「指标 source_path / legacy 键」改写为「指标模板 id」。

背景（2026-10-09 全量迁移）：进入条件目录（CANDIDATE / DEMAND / POSITION）原由
AtomicMetric（source_path）驱动，ConditionItem.field 存的是 source_path（如
candidate.age）；METRIC 源则存指标模板 id。本次统一收口为「引用指标模板」，目录四类源
全部返回模板 id，故需把存量 source_path / legacy 键改写为对应模板 id。

策略（双模求值已在前端/后端兜底，本迁移追求「改写后求值语义不变」）：
  - field 已是 UUID（模板 id）→ 跳过；
  - legacy 键（仅 CANDIDATE：AGE/GENDER/...）→ 翻译为 source_path；
  - 以 entity. 开头的 source_path → 直接作为 source_path；
  - HIRING_MANAGER 等硬编码需求字段（非指标驱动）→ 保持原样，不迁移；
  - 按 source_path 查 AtomicMetric（启用且未软删），查不到 → 保留原值（双模求值兜底）；
  - 选「运算符被模板白名单覆盖」的模板优先；若无则按原子指标默认运算符 seed 一个模板，
    以保证改写后该条件仍能正常求值（不出现「模板不支持该运算符」降级）。
"""

from django.db import migrations

LEGACY_CANDIDATE_FIELD_TO_PATH = {
    'AGE': 'candidate.age',
    'GENDER': 'candidate.gender',
    'HIGHEST_EDU': 'candidate.highest_education',
    'WORK_YEARS': 'candidate.work_years',
    'CURRENT_CITY': 'candidate.current_city',
    'EXPECTED_CITY': 'candidate.expected_city',
}

ENTITY_PREFIXES = ('candidate.', 'demand.', 'position.')


def _default_operators(data_type: str) -> list:
    if data_type == 'number':
        return ['GT', 'GTE', 'LT', 'LTE', 'BETWEEN', 'EQ']
    if data_type == 'boolean':
        return ['EQ', 'NEQ', 'IN', 'NOT_IN']
    if data_type == 'date':
        return ['EQ', 'NEQ', 'GT', 'GTE', 'LT', 'LTE', 'BETWEEN', 'IS_EMPTY', 'IS_NOT_EMPTY']
    return ['EQ', 'NEQ', 'IN', 'NOT_IN']


def _looks_like_uuid(value) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        import uuid as _uuid
        _uuid.UUID(value)
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def migrate_condition_fields_to_template(apps, schema_editor):
    ConditionItem = apps.get_model('entry_condition', 'ConditionItem')
    AtomicMetric = apps.get_model('metrics', 'AtomicMetric')
    MetricTemplate = apps.get_model('metrics', 'MetricTemplate')

    for item in ConditionItem.objects.filter(
        condition_type__in=['CANDIDATE', 'DEMAND', 'POSITION'],
        deleted_at__isnull=True,
    ):
        field = item.field
        if _looks_like_uuid(field):
            continue  # 已是模板 id

        # 解析 source_path
        if field in LEGACY_CANDIDATE_FIELD_TO_PATH:
            source_path = LEGACY_CANDIDATE_FIELD_TO_PATH[field]
        elif isinstance(field, str) and field.startswith(ENTITY_PREFIXES):
            source_path = field
        else:
            # HIRING_MANAGER 等硬编码需求字段，非指标驱动，保持原样
            continue

        atomic = AtomicMetric.objects.filter(
            source_path=source_path, status='enabled', deleted_at__isnull=True,
        ).first()
        if atomic is None:
            # 无对应原子指标：保留原值，由双模求值兜底（不会 500）
            continue

        # 优先选「运算符被白名单覆盖」的模板，避免改写后该条件被「不支持运算符」降级
        templates = list(MetricTemplate.objects.filter(
            atomic_metric=atomic, status='enabled', deleted_at__isnull=True,
        ).order_by('id'))
        tpl = next(
            (t for t in templates if item.operator in (t.operators or [])), None,
        )
        if tpl is None:
            tpl = MetricTemplate.objects.create(
                name=f'{atomic.name} · {source_path} · {item.operator}',
                atomic_metric=atomic,
                operators=_default_operators(atomic.data_type),
                unit=atomic.unit or '',
                status='enabled',
            )

        item.field = str(tpl.id)
        item.save(update_fields=['field'])


def reverse_migrate_condition_fields(apps, schema_editor):
    # 反向迁移无法可靠还原 source_path（多对一 + seed），置为 no-op：
    # 模板 id 在双模求值下仍可正常求值，回滚不影响现网正确性。
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('entry_condition', '0006_alter_conditionitem_operator'),
        ('metrics', '0022_metrictemplate_param_unit'),
    ]

    operations = [
        migrations.RunPython(
            migrate_condition_fields_to_template,
            reverse_migrate_condition_fields,
        ),
    ]
