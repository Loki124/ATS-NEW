"""数据迁移：纠正字符串类模板的「值域 / 集合运算」错误配置。

背景（2026-10 指标值域治理）:
    前端模板弹窗只按「出参是不是日期」二分：日期走日期区间，其余一律渲染数值分段
    （min / max / 步长）。于是自由文本字段（如「需求职位名称」demand.position_title）
    被配成了数值值域，保存时又报「请填写步长」——用户既填不了也存不了。

    与此同时，字符串型模板普遍启用了「属于集合 / 不属于集合」。但值域的概念前提是
    「有限候选集」，只有数值（可按区间枚举）、日期（可按粒度枚举）成立；自由文本是无穷域，
    枚举不出全集，集合运算必然漏匹配，用户还会误以为覆盖完整。

本次处理:
    1. 自由文本模板（data_type=string 且 is_enum=False）移除 IN / NOT_IN。
       保留 EQ / NEQ / CONTAINS / NOT_CONTAINS / REGEX_MATCH / IS_EMPTY / IS_NOT_EMPTY
       —— 对无穷域语义成立（包含 / 正则可表达「命中一批值」）。
    2. 枚举型模板若候选值（param_enums / enum_values）为空，置为停用。
       这类模板一旦启用，规则配置者会看到一个空下拉（param_enums 是条件目录渲染
       校验值选项的唯一数据源，见 process.views._build_metric_template_catalog）。
       不在此伪造业务候选项 —— 由业务方补齐动态字段 options 后重新启用。

可逆性:
    第 1 步可逆（按同一判定条件加回）。第 2 步的 forward/reverse 不完全对称：
    无法区分「原本就停用」与「本次被停用」，reverse 会把满足条件的模板一律启用。
    这是有意的：误启用的模板仍会被前端候选值校验拦下，而漏恢复只会让配置者少看到一个选项。
"""
from django.db import migrations

# 自由文本字段不成立的运算符（无穷域无法穷举全集）
_FORBIDDEN_OPS = ('IN', 'NOT_IN')


def _forwards(apps, schema_editor):
    MetricTemplate = apps.get_model('metrics', 'MetricTemplate')

    # 注意：MetricTemplate.data_type / .is_enum 在真实模型上是 property（转发给引用的指标），
    # 而迁移拿到的历史模型不含自定义 property —— 必须显式经 atomic_metric / derived_metric
    # 取字段。DerivedMetric 没有 is_enum 列（只有 AtomicMetric 有），一律按非枚举处理。
    disabled, stripped = 0, 0
    for tpl in MetricTemplate.objects.select_related('atomic_metric', 'derived_metric').all():
        metric = tpl.atomic_metric or tpl.derived_metric
        if metric is None:
            continue
        data_type = metric.data_type
        is_enum = bool(getattr(tpl.atomic_metric, 'is_enum', False)) if tpl.atomic_metric_id else False
        enum_values = list(getattr(tpl.atomic_metric, 'enum_values', []) or []) if tpl.atomic_metric_id else []

        is_freetext = data_type == 'string' and not is_enum
        if is_freetext:
            kept = [op for op in (tpl.operators or []) if op not in _FORBIDDEN_OPS]
            if len(kept) != len(tpl.operators or []):
                tpl.operators = kept
                stripped += 1
            # 数值分段对自由文本无意义（历史脏数据 / 前端旧版渲染残留）
            if tpl.value_domain and tpl.value_domain.get('segments'):
                tpl.value_domain = {'segments': []}
        elif is_enum and not (tpl.param_enums or enum_values):
            # 候选值无处可寻：停用而不是留一个空下拉给规则配置者
            if tpl.status != 'disabled':
                tpl.status = 'disabled'
                disabled += 1
        if is_freetext or is_enum:
            tpl.save(update_fields=['operators', 'value_domain', 'status'])

    if stripped or disabled:
        print(
            f'[0029] 自由文本模板移除集合运算符 {stripped} 个；'
            f'候选值为空的枚举模板置为停用 {disabled} 个'
        )


def _backwards(apps, schema_editor):
    MetricTemplate = apps.get_model('metrics', 'MetricTemplate')

    restored, enabled = 0, 0
    for tpl in MetricTemplate.objects.select_related('atomic_metric', 'derived_metric').all():
        metric = tpl.atomic_metric or tpl.derived_metric
        if metric is None:
            continue
        is_enum = bool(getattr(tpl.atomic_metric, 'is_enum', False)) if tpl.atomic_metric_id else False
        is_freetext = metric.data_type == 'string' and not is_enum
        if is_freetext:
            ops = list(tpl.operators or [])
            if any(op not in ops for op in _FORBIDDEN_OPS):
                tpl.operators = sorted(set(ops) | set(_FORBIDDEN_OPS))
                restored += 1
                tpl.save(update_fields=['operators'])
        elif is_enum and not tpl.param_enums:
            if tpl.status == 'disabled':
                tpl.status = 'enabled'
                enabled += 1
                tpl.save(update_fields=['status'])

    if restored or enabled:
        print(f'[0029] 还原：恢复集合运算符 {restored} 个；重新启用枚举模板 {enabled} 个')


class Migration(migrations.Migration):

    dependencies = [
        ('metrics', '0028_strip_leaked_sensitive_metrics'),
    ]

    operations = [
        migrations.RunPython(_forwards, _backwards),
    ]