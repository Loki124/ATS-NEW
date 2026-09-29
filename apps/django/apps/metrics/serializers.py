"""指标库序列化器。

字段命名遵循项目约定：内部 snake_case（DRF 字段），对外由全局 CamelCase 渲染器
输出 camelCase（sourcePath / dataType / atomicMetric ...）；请求体由 CamelCaseParser
把 camelCase 转回 snake_case，故前端可两种拼写混发。
"""
from rest_framework import serializers

from apps.rule_engine.models import UnifiedOperator

from .models import AtomicMetric, DerivedMetric, MetricRule, MetricTemplate
from .services.derived_registry import get as get_derived_func
from .services.rule_validators import validate_metric_rule


class AtomicMetricSerializer(serializers.ModelSerializer):
    template_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = AtomicMetric
        fields = [
            'id', 'name', 'source_path', 'data_type', 'unit', 'is_enum',
            'description', 'status', 'auto_generated', 'created_at', 'template_count',
        ]
        read_only_fields = ['id', 'created_at', 'template_count', 'auto_generated']

    def validate_source_path(self, value):
        if '.' not in (value or ''):
            raise serializers.ValidationError('字段路径必须包含 "." ，如 candidate.age')
        return value

    def get_template_count(self, obj):
        return obj.templates.count()


class DerivedMetricSerializer(serializers.ModelSerializer):
    template_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = DerivedMetric
        fields = [
            'id', 'name', 'calc_func', 'base_path', 'params', 'data_type',
            'unit', 'description', 'status', 'created_at', 'template_count',
        ]
        read_only_fields = ['id', 'created_at', 'template_count']

    def validate_calc_func(self, value):
        if get_derived_func(value) is None:
            raise serializers.ValidationError(f'未注册的计算函数: {value}')
        return value

    def validate_base_path(self, value):
        if '.' not in (value or ''):
            raise serializers.ValidationError('数据来源路径必须包含 "." ，如 candidate.workExperience')
        return value

    def validate_params(self, value):
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError('参数必须是对象')
        return value

    def get_template_count(self, obj):
        return obj.templates.count()


class MetricTemplateSerializer(serializers.ModelSerializer):
    metric_name = serializers.SerializerMethodField(read_only=True)
    metric_path = serializers.SerializerMethodField(read_only=True)
    metric_kind = serializers.SerializerMethodField(read_only=True)
    data_type = serializers.SerializerMethodField(read_only=True)
    unit = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MetricTemplate
        fields = [
            'id', 'name', 'atomic_metric', 'derived_metric',
            'metric_name', 'metric_path', 'metric_kind', 'data_type', 'unit',
            'operators', 'status', 'description', 'created_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'metric_name', 'metric_path',
            'metric_kind', 'data_type', 'unit',
        ]

    def validate(self, attrs):
        instance = self.instance
        atomic = attrs.get('atomic_metric',
                           instance.atomic_metric if instance else None)
        derived = attrs.get('derived_metric',
                            instance.derived_metric if instance else None)
        if (atomic is None) == (derived is None):
            raise serializers.ValidationError('模板必须且只能引用一个指标（原子指标或派生指标）')

        operators = attrs.get('operators')
        if operators is not None:
            if not operators:
                raise serializers.ValidationError('至少选择 1 个运算符')
            invalid = [op for op in operators if op not in UnifiedOperator.values]
            if invalid:
                raise serializers.ValidationError(f'不支持的运算符: {invalid}')
        return attrs

    def get_metric_name(self, obj):
        return obj.metric.name if obj.metric else ''

    def get_metric_path(self, obj):
        return obj.metric_path

    def get_metric_kind(self, obj):
        return obj.metric_kind

    def get_data_type(self, obj):
        return obj.data_type

    def get_unit(self, obj):
        return obj.unit


class ConditionInputSerializer(serializers.Serializer):
    """单条条件输入（前端可发 templateId，view 层已归一化为 template_id）。"""
    template_id = serializers.CharField()
    operator = serializers.ChoiceField(choices=UnifiedOperator.choices)
    value = serializers.JSONField(required=False, allow_null=True, default=None)
    meta = serializers.JSONField(required=False, default=dict)


class RuleExecuteSerializer(serializers.Serializer):
    """规则执行输入（一次性执行，不落库 —— 避免每次执行都产生垃圾规则记录）。"""
    conditions = ConditionInputSerializer(many=True, allow_empty=False)
    logic = serializers.ChoiceField(choices=[('AND', 'AND'), ('OR', 'OR')], required=False, default='AND')
    data = serializers.JSONField()


class MetricRuleSerializer(serializers.ModelSerializer):
    """指标规则序列化器 —— 持久化规则（支持新增/编辑/删除/启停）。"""

    condition_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MetricRule
        fields = [
            'id', 'name', 'description', 'scene', 'conditions', 'logic',
            'status', 'enabled', 'action_type',
            'created_at', 'condition_count',
        ]
        read_only_fields = ['id', 'created_at', 'condition_count']
        # 模型字段带 default=list → ModelSerializer 会生成 required=False，
        # 导致「不传 conditions」绕过 validate_conditions。显式要求必传。
        extra_kwargs = {'conditions': {'required': True}}

    def validate_conditions(self, value):
        if not isinstance(value, list) or not value:
            raise serializers.ValidationError('至少配置 1 个条件')
        for idx, cond in enumerate(value, start=1):
            if not isinstance(cond, dict):
                raise serializers.ValidationError(f'第 {idx} 个条件格式不正确')
            template_id = cond.get('templateId') or cond.get('template_id')
            operator = cond.get('operator')
            if not template_id:
                raise serializers.ValidationError(f'第 {idx} 个条件缺少 templateId')
            if operator not in UnifiedOperator.values:
                raise serializers.ValidationError(f'第 {idx} 个条件运算符不合法: {operator}')
            if not MetricTemplate.objects.filter(pk=template_id).exists():
                raise serializers.ValidationError(f'第 {idx} 个条件引用的模板不存在: {template_id}')
        # T5：数值型条件值统一 coerce 为字符串，避免 JSON number → Python float
        # 序列化时的二进制精度丢失（INV-9）。仅对 int/float 生效，字符串/布尔/日期不动。
        return _coerce_numeric_strings(value)

    def validate(self, attrs):
        """请求态：规则级校验链（防御前端绕过）。

        field 级校验（validate_conditions）先行；此处跑规则级跨条件校验，
        返回人话中文错误，DRF 聚合后给出 400。

        部分更新（PATCH）容错：payload 未携带的字段回退到 self.instance 当前值，
        避免「只改 conditions」这类局部更新被 V05 的 scene 非空校验误杀。
        """
        instance = self.instance
        errors = validate_metric_rule({
            'name': attrs.get('name', instance.name if instance else None),
            'scene': attrs.get('scene', instance.scene if instance else None),
            'logic': attrs.get('logic', instance.logic if instance else None),
            'conditions': attrs.get('conditions', instance.conditions if instance else None),
            'action_type': attrs.get(
                'action_type', getattr(instance, 'action_type', None) if instance else None),
            'id': instance.pk if instance else None,
        })
        if errors:
            raise serializers.ValidationError({'conditions': errors})
        return attrs

    def get_condition_count(self, obj):
        return len(obj.conditions or [])


def _coerce_numeric_strings(conditions):
    """把条件中的数值（int/float）就地转为字符串，保留 Decimal 精度语义。

    - 单值 value（GT/LT/EQ/...）
    - BETWEEN 的 meta.min / meta.max
    - IN / NOT_IN 的 value 数组元素
    bool 不处理（避免 True/False 被当数字）。
    """
    for cond in conditions:
        if not isinstance(cond, dict):
            continue
        operator = cond.get('operator')
        value = cond.get('value')
        if operator in ('IN', 'NOT_IN'):
            if isinstance(value, list):
                cond['value'] = [
                    str(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v
                    for v in value
                ]
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            cond['value'] = str(value)
        if operator == 'BETWEEN':
            meta = cond.get('meta') or {}
            if isinstance(meta, dict):
                for k in ('min', 'max'):
                    mv = meta.get(k)
                    if isinstance(mv, (int, float)) and not isinstance(mv, bool):
                        meta[k] = str(mv)
                cond['meta'] = meta
    return conditions
