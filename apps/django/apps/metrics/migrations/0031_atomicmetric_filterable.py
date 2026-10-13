"""AtomicMetric.filterable 红线字段 + 内省回填 (ARCH §2.1).

新增 filterable 元数据标记「可下推过滤」:
  - True: 标量字段, 可编译为 SQL WHERE 进入行级过滤场景;
  - False: 仅可进入点评估场景 (运行时求值).

回填策略 (按 source_path 内省目标模型字段):
  - 含数组下标 / 嵌套 JSON 路径 (candidate.workExperience.0.company) -> False;
  - 关系字段 (FK/M2M/O2O) -> False (不能作标量过滤下推);
  - 无对应模型字段 (未知 entity 前缀 / 模型无该字段) -> False;
  - 其余真实存在的标量字段 -> True.

反向迁移置 no-op: AddField 的默认 True 无法按行还原, 且回滚后点评估场景
本就放行全部原子指标, 不影响现网正确性。
"""
import importlib

from django.db import migrations, models
from django.core.exceptions import FieldDoesNotExist

# 与 data_permission.attribute_fields._ENTITY_MODEL_PATHS 同源 (迁移内自包含,
# 不 import 业务模块的配置常量, 避免其未来变更 silently 改变迁移语义).
ENTITY_MODEL_PATHS = {
    'demand': 'apps.demand.models.Demand',
    'position': 'apps.position.models.Position',
    'candidate': 'apps.candidate.models.Candidate',
    'process': 'apps.process.models.RecruitmentProcess',
}


def _classify_filterable(source_path: str) -> bool:
    """按 source_path 内省判定是否可下推为 SQL WHERE."""
    parts = [p for p in str(source_path or '').split('.') if p]
    if len(parts) != 2:
        # 非 entity.field 两段形态: 裸字段名 / JSON 嵌套 / 数组下标 -> 不可下推
        return False
    entity, tail = parts
    model_path = ENTITY_MODEL_PATHS.get(entity)
    if not model_path:
        return False  # 无对应模型可内省 (未知 entity 前缀)
    try:
        module_path, cls = model_path.rsplit('.', 1)
        model = getattr(importlib.import_module(module_path), cls)
        field = model._meta.get_field(tail)
    except (FieldDoesNotExist, ImportError, AttributeError, LookupError):
        return False
    if field.is_relation:
        return False  # 关系字段不能作标量过滤下推
    return True


def backfill_filterable(apps, schema_editor):
    AtomicMetric = apps.get_model('metrics', 'AtomicMetric')
    for metric in AtomicMetric.objects.all().only('id', 'source_path', 'filterable'):
        metric.filterable = _classify_filterable(metric.source_path)
        metric.save(update_fields=['filterable'])


class Migration(migrations.Migration):

    dependencies = [
        ('metrics', '0030_metrictemplate_scope_template_refs'),
    ]

    operations = [
        migrations.AddField(
            model_name='atomicmetric',
            name='filterable',
            field=models.BooleanField(
                default=True, verbose_name='可下推过滤',
                help_text='True：可进入行级过滤场景（编译为 SQL WHERE）；'
                          'False：仅可进入点评估场景（运行时求值）',
            ),
        ),
        migrations.RunPython(backfill_filterable, migrations.RunPython.noop),
    ]
