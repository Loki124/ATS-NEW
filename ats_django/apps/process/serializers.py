"""Process App Serializers (DRF)

包含：
- RecruitmentStageSerializer: 阶段库
- StageRuleSerializer: 阶段规则
- ProcessStageLinkSerializer: 流程-阶段关联
- RecruitmentProcessSerializer: 招聘流程
- RecruitmentProcessDetailSerializer: 含完整 links + rules
- ProcessTemplateSerializer: 流程模板
- ExpressionValidationRequest/Response: 表达式校验
"""
from __future__ import annotations

from rest_framework import serializers
from django.db import transaction

from .models import (
    ProcessStageLink,
    ProcessTemplate,
    ProcessingRule,
    RecruitmentProcess,
    RecruitmentStage,
    StageRule,
    StageStatus,
    StageType,
)
from .services.expression_service import (
    validate_expression,
    extract_ids,
    ExpressionError,
)


# ============================================================
# 阶段（RecruitmentStage）
# ============================================================
class RecruitmentStageSerializer(serializers.ModelSerializer):
    """阶段库 - 列表/详情"""
    reference_count = serializers.IntegerField(read_only=True)
    is_referenced = serializers.BooleanField(read_only=True)
    supports_to_be_scheduled = serializers.BooleanField(read_only=True)
    stage_type_display = serializers.CharField(source='get_stage_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = RecruitmentStage
        fields = [
            'id', 'code', 'name', 'stage_type', 'stage_type_display',
            'status', 'status_display',
            'is_builtin',
            'default_features', 'optional_features',
            'description',
            'reference_count', 'is_referenced', 'supports_to_be_scheduled',
            'created_at', 'updated_at', 'created_by', 'updated_by',
        ]
        read_only_fields = ['id', 'code', 'reference_count', 'is_referenced',
                            'supports_to_be_scheduled', 'created_at', 'updated_at',
                            'created_by', 'updated_by']

    def validate_name(self, value):
        """BR-001~003: 阶段名称约束"""
        if len(value) > 20:
            raise serializers.ValidationError('阶段名称不可超过 20 字')
        return value.strip()

    def validate(self, attrs):
        # 预置阶段不可停用/删除
        if self.instance and self.instance.is_builtin:
            if 'status' in attrs and attrs['status'] == StageStatus.DISABLED:
                raise serializers.ValidationError(
                    {'status': '预置阶段不可停用'},
                )
        return attrs


class RecruitmentStageCreateSerializer(RecruitmentStageSerializer):
    """创建阶段"""
    class Meta(RecruitmentStageSerializer.Meta):
        read_only_fields = ['id', 'code'] + [
            f for f in RecruitmentStageSerializer.Meta.read_only_fields
            if f not in ['id', 'code']
        ]


# ============================================================
# 阶段规则（StageRule）
# ============================================================
class StageRuleSerializer(serializers.ModelSerializer):
    """阶段规则"""
    processing_rule_display = serializers.CharField(source='get_processing_rule_display', read_only=True)

    class Meta:
        model = StageRule
        fields = [
            'id', 'link',
            'data_source', 'data_field',
            'processing_rule', 'processing_rule_display',
            'processor_order', 'current_processor_index',
            'auto_skip_n_plus_two', 'inherit_prior_consensus',
            'is_grab_mode', 'grab_threshold',
            'interview_rounds', 'interview_format',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'current_processor_index', 'created_at', 'updated_at']

    def validate_processor_order(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('processor_order 必须是数组')
        if len(value) > 50:
            raise serializers.ValidationError('处理人顺序列表最多 50 个')
        return value

    def validate(self, attrs):
        rule = attrs.get('processing_rule')
        order = attrs.get('processor_order')

        if rule == ProcessingRule.SEQUENTIAL and not order:
            raise serializers.ValidationError(
                {'processor_order': 'SEQUENTIAL 模式必须配置处理人顺序'},
            )
        if rule != ProcessingRule.SEQUENTIAL and order:
            # 其他模式警告
            pass

        grab_mode = attrs.get('is_grab_mode')
        threshold = attrs.get('grab_threshold')
        if grab_mode and (not threshold or threshold < 5):
            raise serializers.ValidationError(
                {'grab_threshold': '抢单模式必须配置阈值且 ≥ 5 分钟'},
            )
        return attrs


# ============================================================
# 流程-阶段关联（ProcessStageLink）
# ============================================================
class ProcessStageLinkSerializer(serializers.ModelSerializer):
    """流程-阶段关联"""
    stage = RecruitmentStageSerializer(read_only=True)
    stage_id = serializers.CharField(write_only=True, help_text='阶段 ID')
    stage_rule = StageRuleSerializer(read_only=True)

    class Meta:
        model = ProcessStageLink
        fields = [
            'id', 'process', 'stage', 'stage_id',
            'order', 'is_required',
            'entry_rule_expression',
            'stage_rule',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'process', 'stage', 'stage_rule', 'created_at', 'updated_at']

    def validate_order(self, value):
        if value < 0:
            raise serializers.ValidationError('order 必须为非负整数')
        return value

    def validate_entry_rule_expression(self, value):
        """基础语法预检（具体 max_id 校验在 service 中）"""
        if not value:
            return value
        try:
            tokens = [t for t in value.split() if t.strip()]
            # 基础括号匹配
            if value.count('(') != value.count(')'):
                raise serializers.ValidationError('括号不匹配')
        except Exception:
            raise serializers.ValidationError('表达式语法错误')
        return value.strip()


# ============================================================
# 招聘流程（RecruitmentProcess）
# ============================================================
class RecruitmentProcessListSerializer(serializers.ModelSerializer):
    """招聘流程 - 列表"""
    stage_count = serializers.SerializerMethodField()
    reference_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = RecruitmentProcess
        fields = [
            'id', 'code', 'name', 'current_version',
            'is_template', 'template_code',
            'is_enabled', 'validate_resume_score',
            'status', 'description',
            'stage_count', 'reference_count',
            'created_at', 'updated_at',
        ]

    def get_stage_count(self, obj):
        return obj.stage_links.count()


class RecruitmentProcessSerializer(serializers.ModelSerializer):
    """招聘流程 - 创建/更新"""
    stage_count = serializers.SerializerMethodField()
    reference_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = RecruitmentProcess
        fields = [
            'id', 'code', 'name', 'current_version',
            'applicable_scope',
            'is_template', 'template_code',
            'is_enabled', 'validate_resume_score',
            'status', 'description',
            'stage_count', 'reference_count',
            'created_at', 'updated_at', 'created_by', 'updated_by',
        ]
        read_only_fields = [
            'id', 'code', 'current_version',
            'stage_count', 'reference_count',
            'created_at', 'updated_at', 'created_by', 'updated_by',
        ]

    def get_stage_count(self, obj):
        return obj.stage_links.count()

    def validate_name(self, value):
        if len(value) > 30:
            raise serializers.ValidationError('流程名称不可超过 30 字')
        return value.strip()

    def validate_applicable_scope(self, value):
        """适用范围条件表达式校验"""
        if not value:
            return value
        items = value.get('items', [])
        if not isinstance(items, list):
            raise serializers.ValidationError('applicable_scope.items 必须是数组')
        expression = value.get('expression', '').strip()
        if expression:
            from .expressions import validate_syntax
            result = validate_syntax(expression, len(items))
            if not result['valid']:
                raise serializers.ValidationError(
                    f"applicable_scope.expression 非法: {result['error']}",
                )
        return value


class RecruitmentProcessDetailSerializer(RecruitmentProcessSerializer):
    """招聘流程 - 详情（含完整 stage links + rules）"""
    stage_links = ProcessStageLinkSerializer(many=True, read_only=True)

    class Meta(RecruitmentProcessSerializer.Meta):
        fields = RecruitmentProcessSerializer.Meta.fields + ['stage_links']


# ============================================================
# 流程模板（ProcessTemplate）
# ============================================================
class ProcessTemplateSerializer(serializers.ModelSerializer):
    """流程模板"""
    class Meta:
        model = ProcessTemplate
        fields = [
            'id', 'code', 'name', 'description', 'category',
            'snapshot', 'is_builtin', 'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProcessTemplateApplySerializer(serializers.Serializer):
    """应用流程模板"""
    template_id = serializers.CharField()
    name = serializers.CharField(max_length=30)
    code = serializers.CharField(max_length=20)


# ============================================================
# 表达式校验（Expression Validation）
# ============================================================
class ExpressionValidationRequestSerializer(serializers.Serializer):
    """表达式校验请求"""
    expression = serializers.CharField(
        max_length=500, help_text='条件表达式，如 (1 AND 2) OR 3',
    )
    max_id = serializers.IntegerField(
        min_value=1, max_value=100, help_text='最大条件编号（条件项总数）',
    )


class ExpressionValidationResponseSerializer(serializers.Serializer):
    """表达式校验响应"""
    valid = serializers.BooleanField()
    expression = serializers.CharField()
    error = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    error_pos = serializers.IntegerField(required=False, allow_null=True)
    suggestion = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    used_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
    max_id = serializers.IntegerField(required=False)


# ============================================================
# 嵌套写入序列化器（创建流程时同时创建 stage links + rules）
# ============================================================
class NestedStageRuleInputSerializer(serializers.Serializer):
    """嵌套 - 阶段规则输入"""
    data_source = serializers.CharField(required=False, allow_blank=True, max_length=32)
    data_field = serializers.CharField(required=False, allow_blank=True, max_length=64)
    processing_rule = serializers.ChoiceField(
        choices=ProcessingRule.choices,
        default=ProcessingRule.DIRECT,
    )
    processor_order = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    auto_skip_n_plus_two = serializers.BooleanField(default=False)
    inherit_prior_consensus = serializers.BooleanField(default=False)
    is_grab_mode = serializers.BooleanField(default=False)
    grab_threshold = serializers.IntegerField(default=30, min_value=5, max_value=1440)
    interview_rounds = serializers.IntegerField(default=1, min_value=1, max_value=10)
    interview_format = serializers.CharField(required=False, allow_blank=True, max_length=32)


class NestedStageLinkInputSerializer(serializers.Serializer):
    """嵌套 - 流程-阶段关联输入"""
    stage_id = serializers.CharField()
    order = serializers.IntegerField(min_value=0)
    is_required = serializers.BooleanField(default=True)
    entry_rule_expression = serializers.CharField(
        required=False, allow_blank=True, max_length=500,
    )
    stage_rule = NestedStageRuleInputSerializer(required=False)


class ProcessWithStagesCreateSerializer(serializers.Serializer):
    """创建流程（含 stages）"""
    code = serializers.CharField(max_length=20)
    name = serializers.CharField(max_length=30)
    description = serializers.CharField(required=False, allow_blank=True, max_length=100)
    is_template = serializers.BooleanField(default=False)
    template_code = serializers.CharField(required=False, allow_blank=True, max_length=50)
    applicable_scope = serializers.JSONField(required=False, default=dict)
    validate_resume_score = serializers.BooleanField(default=True)
    stage_links = NestedStageLinkInputSerializer(many=True)

    def validate_stage_links(self, value):
        if not value:
            raise serializers.ValidationError('流程至少需要一个阶段')
        # 校验 order 唯一
        orders = [v['order'] for v in value]
        if len(orders) != len(set(orders)):
            raise serializers.ValidationError('stage_links.order 必须唯一')
        # 校验 stage_id 唯一
        stage_ids = [v['stage_id'] for v in value]
        if len(stage_ids) != len(set(stage_ids)):
            raise serializers.ValidationError('同一阶段不可重复添加')
        return value

    @transaction.atomic
    def create(self, validated_data):
        stage_links_data = validated_data.pop('stage_links')
        request = self.context.get('request')
        actor = request.user if request and request.user.is_authenticated else None

        process = RecruitmentProcess.objects.create(
            **validated_data,
            current_version='V1.0',
            is_enabled=True,
            status='ENABLED',
            created_by=actor,
            updated_by=actor,
        )

        for link_data in stage_links_data:
            stage_id = link_data.pop('stage_id')
            stage_rule_data = link_data.pop('stage_rule', None)

            link = ProcessStageLink.objects.create(
                process=process,
                stage_id=stage_id,
                **link_data,
                created_by=actor,
                updated_by=actor,
            )
            if stage_rule_data:
                StageRule.objects.create(
                    link=link,
                    **stage_rule_data,
                    created_by=actor,
                    updated_by=actor,
                )
        return process
