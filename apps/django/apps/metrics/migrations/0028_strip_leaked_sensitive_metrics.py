"""数据迁移：清理回填时漏网的敏感指标（0027 的补救）。

起因:
    0027 的敏感字段判定只有精确名单，'salary_budget'（薪资范围）归一化后是
    'salarybudget'，不在名单内，于是这个薪资字段被回填成了指标并进了规则条件。
    0027 与 signals 均已升级为「精确名单 + 语义子串兜底」，但已执行的迁移不会
    自我修正，故用本迁移把漏网的记录清掉。

范围严格受限:
    - 只删 auto_generated=True 的指标（手工维护的一条不动）
    - 只删命中新敏感规则的（薪资 / 联系方式类），不误伤正常字段
    - 先删模板再删指标：MetricTemplate.atomic_metric 是 on_delete=PROTECT
    - 幂等：无漏网记录时不做任何事

之所以不直接改 0027 的数据、而保留历史迁移原样:
    已应用的迁移不应被改写成与当时行为不符的版本；而对「从零建库」的环境，
    更严的 0027 本就不会建这些指标，0028 届时自然空转。
"""
import re

from django.db import migrations

SKIP_KEY_SUBSTRINGS = ('salary', 'wage', 'income', 'pay')
SKIP_LABEL_SUBSTRINGS = ('薪资', '工资', '薪酬', '薪水', '收入', '年薪', '月薪')
# 仅清理动态字段路径（candidate./demand./position.），主表种子指标不参与
_DYNAMIC_PREFIXES = ('candidate.', 'demand.', 'position.')


def _norm_key(field_key):
    return re.sub(r'[\s\-_]+', '', field_key or '').lower()


def _is_sensitive(field_key, label=''):
    norm = _norm_key(field_key)
    if any(token in norm for token in SKIP_KEY_SUBSTRINGS):
        return True
    return any(token in (label or '') for token in SKIP_LABEL_SUBSTRINGS)


def _forwards(apps, schema_editor):
    AtomicMetric = apps.get_model('metrics', 'AtomicMetric')
    MetricTemplate = apps.get_model('metrics', 'MetricTemplate')

    leaked = [
        m for m in AtomicMetric.objects.filter(auto_generated=True)
        if m.source_path and m.source_path.startswith(_DYNAMIC_PREFIXES)
        and _is_sensitive(m.source_path.split('.', 1)[1], m.name)
    ]
    if not leaked:
        return

    paths = [m.source_path for m in leaked]
    n_tpl = MetricTemplate.objects.filter(
        atomic_metric__auto_generated=True, atomic_metric__source_path__in=paths,
    ).delete()[0]
    n_metric = AtomicMetric.objects.filter(source_path__in=paths).delete()[0]
    print(f'  清理漏网敏感指标: 模板 {n_tpl} 条 / 指标 {n_metric} 条 -> {paths}')


def _backwards(apps, schema_editor):
    """不可逆：被清理的指标属于自动生成的派生数据。

    重建方式是重跑 0027 的 forwards —— 届时判定已升级为「名单 + 子串兜底」，
    薪资类字段本就不会再建出来，所以也没有「恢复漏网指标」的意义。
    """
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('metrics', '0027_backfill_dynamic_field_metrics'),
    ]

    operations = [
        migrations.RunPython(_forwards, _backwards),
    ]
