"""动态字段信号 —— 动态字段变更时自动同步「对象路径」型指标定义（原子指标 + 指标模板）。

同步设计（2026-10 全量治理后）：
    - 同步范围扩到全部业务资源：Candidate / Demand / Position。
      快照早已支持三者（build_candidate / build_demand / build_position_snapshot），
      指标路径前缀随之取 resource 小写；旧实现只认 Candidate，属历史遗留。
    - 只有「顶层属性字段」能自动映射：字段值在快照里位于顶层 key 时，路径可推断为
      `<resource>.<field_key>`。而工作经历 / 项目经历 / 教育经历 / 技能语言 等板块的
      字段是**数组条目内的子字段** —— 一个字段定义对应 N 条经历、索引未知，
      source_path 无法推断，故不在 _AUTO_SYNC_MODULES 内，由人工在指标定义页配置。
    - 规范字段闸门：field_type 非空、field_key 为 snake_case（模型注释即此约定）。
      不合规的字段跳过并记 warning，避免自动制造「指向不存在路径」的脏指标。
    - 敏感字段跳过：PII 类型（电话 / 邮箱 / 证件 / 银行卡 / 附件）+ 联系方式与薪资 key。
      注意 key 匹配必须先归一化 —— 库里真实 field_key 常是「Expected salary」这类
      带空格大写的标签，旧实现精确匹配 'salary' 形同虚设。
    - 建 AtomicMetric 的同时建 MetricTemplate：规则条件的字段目录只读模板
      （process/views.py 的条件字段列表过滤 MetricTemplate），只建指标则永远选不到。
    - 幂等：以 source_path 是否已存在为判据，**不依赖 created 标记**，因此软删复活、
      编辑字段、批量导入的 update 路径同样生效。
    - 自动映射失败仅记日志，绝不阻断字段保存（降级，绝不 500）。
"""
import logging
import re

from django.db import IntegrityError, OperationalError, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)

# 参与指标同步的业务资源；其小写即快照根键 / 指标路径前缀
_SYNC_RESOURCES = {'Candidate', 'Demand', 'Position'}

# 不自动映射为指标的字段类型（PII / 结构型，进入规则条件无业务意义）
_SKIP_TYPES = {'PHONE', 'EMAIL', 'ID_CARD', 'BANK_CARD', 'ATTACHMENT'}

# 不自动映射的字段 key —— 以**归一化后**的形式保存（见 _norm_key）
_SKIP_KEYS = {
    'phone', 'email', 'phonehash', 'emailhash',
    'idcard', 'idcardno', 'idcardhash', 'bankcard',
    'salary', 'expectedsalary', 'currentsalary', 'salarymin', 'salarymax',
    'wechat', 'weixin', 'qq',
}

# 精确名单拦不住的语义变体兜底：同义不同名的字段（salary_budget / budget_salary…）
# 若只靠枚举，维护的人稍有疏漏就会让薪资字段进入规则条件。
# 同时匹配 label，兼顾「key 规范但 label 写着薪资」的情况。
_SKIP_KEY_SUBSTRINGS = ('salary', 'wage', 'income', 'pay')
_SKIP_LABEL_SUBSTRINGS = ('薪资', '工资', '薪酬', '薪水', '收入', '年薪', '月薪')

# 字段位于**数组条目内**的板块（候选人侧）：一个字段定义对应 N 条经历，
# source_path 需要数组索引，信号无法推断 —— 落在这些板块的字段不自动映射，
# 由人工在「指标定义」页显式配置路径。
# 采用「默认放行 + 显式排除」而非白名单：新建字段若尚未归组板块，
# 其值通常就在快照顶层 key（如 candidate.<key>），此时自动映射才是正确行为；
# 只有明确归入数组类板块时才阻断。
_MANUAL_PATH_MODULES = {
    'work', 'project', 'edu', 'education', 'skill', 'certificate',
    'experience', 'language',
}

# 合规 field_key 约定（models.py 的 help_text 即「字段 key (snake_case)」）
_KEY_RE = re.compile(r'^[a-z][a-z0-9_]*$')


def _norm_key(field_key: str) -> str:
    """归一化 field_key 用于敏感词比对：去空格/连字符/下划线并转小写。

    「Expected salary」/「expected_salary」/「ExpectedSalary」→ expectedsalary
    """
    return re.sub(r'[\s\-_]+', '', field_key or '').lower()


def _is_sensitive_key(field_key: str, label: str = None) -> bool:
    """敏感字段判定：精确名单 + 语义子串兜底。

    只靠枚举会漏：'salary_budget'（薪资范围）归一化后是 'salarybudget'，不在名单里，
    实际就漏进了规则条件。子串兜底让 salary_budget / budget_salary 这类变体也拦得住。
    """
    norm = _norm_key(field_key)
    if norm in _SKIP_KEYS:
        return True
    if any(token in norm for token in _SKIP_KEY_SUBSTRINGS):
        return True
    return any(token in (label or '') for token in _SKIP_LABEL_SUBSTRINGS)


def _block_reason(instance) -> str:
    """返回不可同步的原因；可同步时返回空字符串（用于 warning 归因与排查）。"""
    field_key = (getattr(instance, 'field_key', None) or '').strip()
    field_type = (getattr(instance, 'field_type', None) or '').strip()

    if not field_key:
        return 'field_key 为空'
    if not field_type:
        return 'field_type 为空，无法推断指标数据类型'
    if not _KEY_RE.match(field_key):
        return f'field_key 非 snake_case（{field_key}），source_path 不可用'
    if field_type in _SKIP_TYPES:
        return f'敏感字段类型 {field_type}，不进规则条件'
    if _is_sensitive_key(field_key, getattr(instance, 'label', None)):
        return f'敏感字段（{field_key}），不进规则条件'

    # 板块闸门：数组条目内的子字段不自动映射（路径需索引，信号推断不出）
    module = getattr(instance, 'module', None)
    module_code = (getattr(module, 'code', None) or '').lower()
    if module_code in _MANUAL_PATH_MODULES:
        return f'板块 {module_code} 的字段位于数组条目内，路径需索引，需人工在指标定义页配置'
    return ''


def _unique_name(base: str, model) -> str:
    """名称唯一保护：重名时追加序号，避免撞 unique 约束。"""
    if not model.objects.filter(name=base).exists():
        return base
    n = 1
    while model.objects.filter(name=f'{base}({n})').exists():
        n += 1
    return f'{base}({n})'


@receiver(post_save, sender='dynamic_field.DynamicField')
def sync_metric_on_field(sender, instance, created, **kwargs):
    """动态字段保存后幂等同步原子指标 + 指标模板。

    幂等判据是 source_path 是否已存在，因此 created=True 与 update（软删复活 /
    编辑 / 批量导入）走同一条路径，都能补齐缺失的指标。
    """
    if getattr(instance, 'resource', None) not in _SYNC_RESOURCES:
        return

    reason = _block_reason(instance)
    if reason:
        # 仅在「本该同步」的字段上记日志，避免对明确排除的板块刷屏
        if (getattr(instance, 'field_type', None) or '').strip():
            logger.info('动态字段跳过指标同步 field=%s reason=%s', instance.field_key, reason)
        else:
            logger.warning('动态字段未同步指标 field=%s reason=%s', instance.field_key, reason)
        return

    # 延迟导入，避免 app 加载期循环依赖
    from apps.metrics.models import AtomicMetric, MetricTemplate
    from apps.metrics.services.operator_matrix import field_type_capability

    resource = instance.resource
    field_key = instance.field_key.strip()
    field_type = instance.field_type.strip()
    path = f'{resource.lower()}.{field_key}'
    cap = field_type_capability(field_type)

    existing = AtomicMetric.objects.filter(source_path=path).first()
    if existing:
        metric = existing
    else:
        label = (getattr(instance, 'label', None) or '').strip() or field_key
        metric = AtomicMetric(
            name=_unique_name(label, AtomicMetric),
            source_path=path,
            data_type=cap['metricType'],
            unit='',
            description=f'由动态字段「{label}」自动生成的对象路径指标',
            status='enabled',
            is_enum=cap['isEnum'],
            auto_generated=True,
        )

    # 枚举字段的值域来自动态字段配置，否则规则条件里无值可选
    options = getattr(instance, 'options', None) or []
    param_enums = [
        (o.get('value') or o.get('label')) if isinstance(o, dict) else o
        for o in options
    ]
    param_enums = [v for v in param_enums if v not in (None, '')]

    try:
        with transaction.atomic():
            metric.save()
            # 模板幂等：同名模板已存在即视为已同步（同名同源，name 唯一）
            if not MetricTemplate.objects.filter(name=metric.name).exists():
                MetricTemplate.objects.create(
                    name=metric.name,
                    atomic_metric=metric,
                    operators=cap['operators'],
                    param_enums=param_enums if cap['isEnum'] else [],
                    status='enabled',
                    description=f'由动态字段「{getattr(instance, "label", None) or field_key}」自动生成',
                )
    except (OperationalError, IntegrityError, ValueError) as e:
        # 指标落库失败不应阻断字段保存：冲突/非法值等均吞。
        # 编程错误 (AttributeError/NameError) 仍向上抛以便排查。
        logger.warning(
            '动态字段自动映射指标失败 field_id=%s path=%s err=%s',
            getattr(instance, 'id', '?'), path, e,
        )