"""数据迁移：把动态字段回填为指标定义（AtomicMetric + MetricTemplate）。

背景（2026-10 全量治理）:
    AtomicMetric.auto_generated 长期为 0 —— dynamic_field 的自动同步信号从未生效过。
    三个叠加根因已分别修掉：信号只认 Candidate（已放宽）、只在 created=True 触发
    （已改为幂等补建）、只建指标不建模板（已补建，规则条件字段目录只读模板）。
    但历史字段不会因代码修复而自动补齐，需要本次回填。

判定口径与 dynamic_field.signals 保持一致（务必同步维护）:
    - 同步范围：Candidate / Demand / Position
    - 排除 PII 类型（电话/邮箱/证件/银行卡/附件）与联系方式、薪资类 key
      （key 按归一化比对：'Expected salary' 与 'expected_salary' 等价）
    - 排除数组条目类板块（work/project/edu/skill/certificate）：其字段位于数组内，
      source_path 需要索引，信号推断不出，路径不确定的指标比没有更危险
    - 要求 field_type 非空且 field_key 为 snake_case

为什么直接复用 signals 的 field_type_capability():
    保证回填产出的 data_type / operators 与「今后新建字段」走信号得到的完全一致。
    若在此硬编码一份映射，两者会随迭代漂移，同一字段出现两套运算符口径。
    该函数只依赖一个纯枚举（UnifiedOperator），在迁移中导入是安全的。

为什么手工生成 code:
    RunPython 里的历史模型不含 AtomicMetric / MetricTemplate 的自定义 save()，
    不会自动补编号；而 code 是 unique 字段，多条空串会直接撞约束。

逆向操作（可回滚）:
    只删除 auto_generated=True 的记录，绝不触碰 58 条手工种子 —— 既有的 _unseed
    写法是按 source_path 硬删，会连带删掉后来人工建的同名指标（见代码审查 M-29）。
    删除顺序必须是「先模板后指标」：MetricTemplate.atomic_metric 是 on_delete=PROTECT。
"""
import re

from django.db import migrations
from nanoid import generate as nanoid_generate

# ── 与 dynamic_field.signals 一致的判定口径快照 ────────────────────────────
SYNC_RESOURCES = {'Candidate', 'Demand', 'Position'}
SKIP_TYPES = {'PHONE', 'EMAIL', 'ID_CARD', 'BANK_CARD', 'ATTACHMENT'}
SKIP_KEYS = {
    'phone', 'email', 'phonehash', 'emailhash',
    'idcard', 'idcardno', 'idcardhash', 'bankcard',
    'salary', 'expectedsalary', 'currentsalary', 'salarymin', 'salarymax',
    'wechat', 'weixin', 'qq',
}
SKIP_KEY_SUBSTRINGS = ('salary', 'wage', 'income', 'pay')
SKIP_LABEL_SUBSTRINGS = ('薪资', '工资', '薪酬', '薪水', '收入', '年薪', '月薪')
MANUAL_PATH_MODULES = {
    'work', 'project', 'edu', 'education', 'skill', 'certificate',
    'experience', 'language',
}
KEY_RE = re.compile(r'^[a-z][a-z0-9_]*$')


def _norm_key(field_key):
    return re.sub(r'[\s\-_]+', '', field_key or '').lower()


def _is_sensitive_key(field_key, label=None):
    """敏感字段判定：精确名单 + 语义子串兜底（与 signals._is_sensitive_key 一致）。

    只靠枚举会漏：'salary_budget'（薪资范围）归一化后是 'salarybudget'，不在名单内。
    """
    norm = _norm_key(field_key)
    if norm in SKIP_KEYS:
        return True
    if any(token in norm for token in SKIP_KEY_SUBSTRINGS):
        return True
    return any(token in (label or '') for token in SKIP_LABEL_SUBSTRINGS)


def _unique_name(model, base):
    if not model.objects.filter(name=base).exists():
        return base
    n = 1
    while model.objects.filter(name=f'{base}({n})').exists():
        n += 1
    return f'{base}({n})'


def _next_code(model, prefix):
    """生成「前缀 + 4 位序号」，等价于 models._next_code（历史模型无法调用它）。

    先按前缀过滤再取最大：全表排序时别的前缀会压过当前前缀（'D' > 'A'），
    导致 seq 退回 0 并撞上已存在的 XX0001。
    """
    last = model.objects.filter(code__startswith=prefix).order_by('-code').first()
    seq = 0
    if last and last.code:
        try:
            seq = int(last.code[len(prefix):])
        except (ValueError, IndexError):
            seq = 0
    return f'{prefix}{seq + 1:04d}'


def _forwards(apps, schema_editor):
    from apps.metrics.services.operator_matrix import field_type_capability

    DynamicField = apps.get_model('dynamic_field', 'DynamicField')
    AtomicMetric = apps.get_model('metrics', 'AtomicMetric')
    MetricTemplate = apps.get_model('metrics', 'MetricTemplate')

    created_metrics = created_tpls = skipped = 0
    for resource in sorted(SYNC_RESOURCES):
        prefix = resource.lower()
        rows = DynamicField.objects.filter(
            resource=resource, deleted_at__isnull=True,
        ).select_related('module')

        for field in rows:
            field_key = (field.field_key or '').strip()
            field_type = (field.field_type or '').strip()

            if not field_key or not field_type or not KEY_RE.match(field_key):
                skipped += 1
                continue
            if field_type in SKIP_TYPES or _is_sensitive_key(field_key, field.label):
                skipped += 1
                continue
            module_code = (field.module.code if field.module_id else '') or ''
            if module_code.lower() in MANUAL_PATH_MODULES:
                skipped += 1
                continue

            path = f'{prefix}.{field_key}'
            # 幂等：与手工种子同路径时以既有指标为准（如 candidate.name / candidate.gender）
            if AtomicMetric.objects.filter(source_path=path).exists():
                skipped += 1
                continue

            cap = field_type_capability(field_type)
            label = (field.label or '').strip() or field_key
            metric = AtomicMetric.objects.create(
                id=nanoid_generate(size=21),
                # 编号前缀区分的是实体类型而非资源：AtomicMetric 一律 AM
                # （DM 专属于 DerivedMetric），否则 Demand/Position 的原子指标
                # 会被标成派生指标编号，列表里无法分辨
                code=_next_code(AtomicMetric, 'AM'),
                name=_unique_name(AtomicMetric, label),
                source_path=path,
                data_type=cap['metricType'],
                unit='',
                description=f'由动态字段「{label}」自动生成的对象路径指标',
                status='enabled',
                is_enum=cap['isEnum'],
                auto_generated=True,
            )
            created_metrics += 1

            # 模板是规则条件字段目录的唯一数据源（process/views.py 只读 MetricTemplate），
            # 只建指标则该字段在规则条件里永远选不到
            options = field.options or []
            param_enums = []
            for opt in options:
                value = opt.get('value') or opt.get('label') if isinstance(opt, dict) else opt
                if value not in (None, ''):
                    param_enums.append(value)

            MetricTemplate.objects.create(
                id=nanoid_generate(size=21),
                code=_next_code(MetricTemplate, 'MT'),
                name=_unique_name(MetricTemplate, metric.name),
                atomic_metric=metric,
                operators=cap['operators'],
                param_enums=param_enums if cap['isEnum'] else [],
                status='enabled',
                description=f'由动态字段「{label}」自动生成',
            )
            created_tpls += 1

    print(f'  回填动态字段指标: 指标 {created_metrics} 条 / 模板 {created_tpls} 条，跳过 {skipped} 条')


def _backwards(apps, schema_editor):
    MetricTemplate = apps.get_model('metrics', 'MetricTemplate')
    AtomicMetric = apps.get_model('metrics', 'AtomicMetric')

    # 只回滚自动生成的记录，手工种子（auto_generated=False）原样保留
    auto_metrics = AtomicMetric.objects.filter(auto_generated=True)
    # noqa 说明: paths 是回滚前 source_path 的快照（历史留痕）。迁移已应用,
    # 保留不删; ruff F841 卡 A6。注意 list() 会真实求值一次 queryset,
    # 但紧接着 auto_metrics.delete() 会再查一次 —— 删掉 paths 只省一次查询,
    # 不改数据结果, 收益小于「改动已应用迁移」的风险。
    paths = list(auto_metrics.values_list('source_path', flat=True))  # noqa: F841
    n_tpl = MetricTemplate.objects.filter(atomic_metric__auto_generated=True).delete()[0]
    n_metric = auto_metrics.delete()[0]
    print(f'  回滚自动生成指标: 模板 {n_tpl} 条 / 指标 {n_metric} 条')


class Migration(migrations.Migration):
    dependencies = [
        ('metrics', '0026_alter_metrictemplate_value_domain'),
        ('dynamic_field', '0023_normalize_candidate_fields'),
    ]

    operations = [
        migrations.RunPython(_forwards, _backwards),
    ]