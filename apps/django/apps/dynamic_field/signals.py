"""动态字段信号 —— 新增字段时自动生成「对象路径」型指标定义。

用户诉求：每次新增字段时自动生成对象路径注解（如 candidate.<field_key>），
并将该字段映射至指标定义列表（原子指标 = 对象路径型）。

关键约束：
    - 仅 resource='Candidate' 的字段映射（快照根键为 candidate，路径才有意义）
    - 参数化 / 计算型指标（派生指标）**不**自动纳入 —— 由用户在「指标定义」
      中手动指派计算函数后另行添加（避免无数据来源路径的派生指标被错误生成）
    - 敏感字段类型（电话 / 邮箱 / 证件 / 银行卡）跳过，避免 PII 进入规则条件
    - 已存在相同 source_path 的原子指标则跳过（幂等，不重复创建）
    - 自动映射失败时静默跳过，绝不阻断字段保存（降级，绝不 500）
"""
import logging

from django.db import IntegrityError, OperationalError
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)

# 不自动映射为指标的字段类型（PII / 结构型，进入规则条件无业务意义）
_SKIP_TYPES = {'PHONE', 'EMAIL', 'ID_CARD', 'BANK_CARD', 'ATTACHMENT'}
# 不自动映射的字段 key（与快照 SENSITIVE_FIELDS 对齐）
_SKIP_KEYS = {
    'phone', 'email', 'phone_hash', 'email_hash',
    'id_card_no', 'id_card_hash', 'expected_salary', 'salary',
}


@receiver(post_save, sender='dynamic_field.DynamicField')
def auto_create_metric_on_field(sender, instance, created, **kwargs):
    if not created:
        return
    if getattr(instance, 'resource', None) != 'Candidate':
        return
    field_type = getattr(instance, 'field_type', None) or ''
    if field_type in _SKIP_TYPES:
        return
    field_key = (getattr(instance, 'field_key', None) or '').strip()
    if field_key in _SKIP_KEYS:
        return

    # 延迟导入，避免 app 加载期循环依赖
    from apps.metrics.models import AtomicMetric
    from apps.metrics.services.operator_matrix import field_type_capability

    path = f'candidate.{field_key}'
    if AtomicMetric.objects.filter(source_path=path).exists():
        return

    cap = field_type_capability(field_type)
    label = getattr(instance, 'label', None) or field_key
    name = label
    # 名称唯一保护：重名时追加序号，避免撞 UniqueConstraint
    n = 1
    while AtomicMetric.objects.filter(name=name).exists():
        n += 1
        name = f'{label}({n})'

    try:
        AtomicMetric.objects.create(
            name=name,
            source_path=path,
            data_type=cap['metricType'],
            unit='',
            description=f'由动态字段「{label}」自动生成的对象路径指标',
            status='enabled',
            is_enum=cap['isEnum'],
            auto_generated=True,
        )
    except (OperationalError, IntegrityError, ValueError) as e:
        # 自动映射到 AtomicMetric 失败不应阻断字段保存: 指标落库失败/字段值非法/重复键均吞。
        # 编程错误 (AttributeError/NameError) 仍向上抛以便排查。
        logger.warning('动态字段自动映射指标失败 field_id=%s err=%s', getattr(instance, 'id', '?'), e)
