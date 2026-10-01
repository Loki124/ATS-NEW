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

from apps.core.serializers import UserMinimalSerializer

from .models import (
    InterviewRound,
    InterviewRoundStatus,
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
    stage_type_display = serializers.SerializerMethodField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    # FE 用 features 字段维护「功能项」，映射到模型的 default_features
    features = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        source='default_features',
    )

    class Meta:
        model = RecruitmentStage
        fields = [
            'id', 'code', 'name', 'stage_type', 'stage_type_display',
            'status', 'status_display',
            'is_builtin', 'is_start', 'is_end',
            'default_features', 'optional_features', 'features',
            'description',
            'reference_count', 'is_referenced', 'supports_to_be_scheduled',
            'created_at', 'updated_at', 'created_by', 'updated_by',
        ]
        read_only_fields = ['id', 'code', 'reference_count', 'is_referenced',
                            'supports_to_be_scheduled', 'created_at', 'updated_at',
                            'created_by', 'updated_by']

    def get_stage_type_display(self, obj: RecruitmentStage) -> str:
        from apps.process.models import StageType
        try:
            return StageType(obj.stage_type).label
        except ValueError:
            return obj.stage_type

    def validate_name(self, value):
        """BR-001~003: 阶段名称约束"""
        if len(value) > 20:
            raise serializers.ValidationError('阶段名称不可超过 20 字')
        return value.strip()

    def _resolve_flag(self, attrs, field_name):
        """从 attrs 或 self.instance 取最终值 (attrs 优先)"""
        if field_name in attrs:
            return attrs[field_name]
        return getattr(self.instance, field_name, False) if self.instance else False

    def validate(self, attrs):
        # 阶段类型必须是系统内置枚举值 (不再依赖数据字典)
        stage_type = attrs.get('stage_type')
        if stage_type:
            from apps.process.models import StageType, STAGE_TYPE_VALUES
            if stage_type not in STAGE_TYPE_VALUES:
                raise serializers.ValidationError(
                    {'stage_type': f'无效的阶段类型: {stage_type}'},
                )
            # 起止阶段类型仅系统预置 (初评/正式录用) 可用, 不允许新建阶段使用
            if stage_type == StageType.START_END:
                new_is_builtin = attrs.get('is_builtin')
                if new_is_builtin is None and self.instance:
                    new_is_builtin = self.instance.is_builtin
                if not new_is_builtin:
                    raise serializers.ValidationError(
                        {'stage_type': '起止阶段类型仅系统预置（初评/正式录用）可用，不可用于新建阶段'},
                    )

        # 预置阶段不可停用/删除
        if self.instance and self.instance.is_builtin:
            if 'status' in attrs and attrs['status'] == StageStatus.DISABLED:
                raise serializers.ValidationError(
                    {'status': '预置阶段不可停用'},
                )

        # BR-001: 互斥 + 全局唯一
        new_is_start = self._resolve_flag(attrs, 'is_start')
        new_is_end = self._resolve_flag(attrs, 'is_end')

        if new_is_start and new_is_end:
            raise serializers.ValidationError(
                {'is_start': '同一阶段不可同时为起始和结束阶段'},
            )

        # select_for_update 缩锁粒度, 只锁目标行 (MySQL 8+ / PG 12+)
        with transaction.atomic():
            exclude_pk = self.instance.pk if self.instance else None
            if new_is_start:
                existing_name = (
                    RecruitmentStage.objects
                    .select_for_update()
                    .filter(is_start=True)
                    .exclude(pk=exclude_pk)
                    .values_list('name', flat=True)
                    .first()
                )
                if existing_name:
                    raise serializers.ValidationError(
                        {'is_start': f'阶段「{existing_name}」已是起始阶段, 全局只能有 1 个起始'},
                    )
            if new_is_end:
                existing_name = (
                    RecruitmentStage.objects
                    .select_for_update()
                    .filter(is_end=True)
                    .exclude(pk=exclude_pk)
                    .values_list('name', flat=True)
                    .first()
                )
                if existing_name:
                    raise serializers.ValidationError(
                        {'is_end': f'阶段「{existing_name}」已是结束阶段, 全局只能有 1 个结束'},
                    )

        return attrs


class RecruitmentStageCreateSerializer(RecruitmentStageSerializer):
    """创建阶段"""
    class Meta(RecruitmentStageSerializer.Meta):
        read_only_fields = ['id', 'code'] + [
            f for f in RecruitmentStageSerializer.Meta.read_only_fields
            if f not in ['id', 'code']
        ]

    def create(self, validated_data):
        """2026-06-17: FE (RecruitmentStage.vue:221) 不发 code, 之前 BE 写入空串 → 第 2 个 stage 撞 UNIQUE 约束 → 500.
        改成缺省时自动生成 P + 3位流水号 (P001, P002, ...). 注意 code 在 read_only_fields 中, 序列化器不读 request['code'],
        所以这里直接读 validated_data.get('code') (默认 ''), 空就自填."""
        if not validated_data.get('code'):
            last = RecruitmentStage.objects.filter(code__regex=r'^P\d+$').order_by('-code').values_list('code', flat=True).first()
            next_num = (int(last[1:]) + 1) if last and last[1:].isdigit() else 1
            validated_data['code'] = f'P{next_num:03d}'
        return super().create(validated_data)


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
            # 2026-07-03: 扩字段对齐 FE StageRuleConfigModal
            'auto_advance_type', 'auto_advance_timing', 'auto_advance_days',
            'default_handler_type', 'default_handler_fields', 'default_handler_user_ids',
            'time_limit', 'time_limit_scope',
            'interview_round_ids',
            # 2026-09-07: 自动跳过 / 自动归档规则
            'skip_rules', 'archive_rules',
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
import json
import logging
log = logging.getLogger(__name__)


def _decode_entry_condition(raw: str | None) -> dict | None:
    """2026-07-03: EntryCondition (FE: matchType/conditionType/items[]) 没有专用 model,
    FE 之前调 /recruitment-rules/entry-conditions (stub, 不入库) → 配置后丢失.
    现在 JSON-encode 整段 EntryCondition 进 ProcessStageLink.entry_rule_expression
    (CharField max_length=500, 单条 item 约 60 字节, 可容纳 ~8 条 items).
    Returns None if blank/unparseable."""
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        # 兼容旧数据: raw 是表达式字符串 (1 AND 2), 包成 dict 让 FE 不崩
        log.warning('entry_rule_expression 不是 JSON, 当作表达式 fallback: %r', raw[:80])
        return {'matchType': 'ALL', 'conditionType': 'CANDIDATE', 'items': [], 'legacyExpression': raw}


def assert_within_start_end_bounds(process, order, exclude_link_id=None):
    """新增/移动阶段 link 时校验起止边界（BR-001 强化）。

    - 起始阶段(初评) 前不可添加前序阶段 → 新 order 必须严格大于起始 link.order
      （order <= start.order 一律拒绝：既不能插在起始阶段之前，也不能与起始阶段同序）
    - 结束阶段(正式录用) 后不可添加后续阶段 → 新 order 必须 <= 结束 link.order
      （order == end.order 允许：相当于「插在结束阶段的位置、把结束阶段顶下去」，
       即新增一条结束阶段的前序阶段；order > end.order 才拒绝）
    exclude_link_id 用于移动已有 link 自身时跳过它自己。
    """
    links = ProcessStageLink.objects.filter(process=process, deleted_at__isnull=True)
    if exclude_link_id:
        links = links.exclude(id=exclude_link_id)
    start_link = links.filter(stage__is_start=True).first()
    end_link = links.filter(stage__is_end=True).first()
    if start_link and order <= start_link.order:
        raise serializers.ValidationError({'order': '起始阶段(初评)前不可添加前序阶段'})
    if end_link and order > end_link.order:
        raise serializers.ValidationError({'order': '结束阶段(正式录用)后不可添加后续阶段'})


def renormalize_process_orders(process):
    """把某流程的 stage_links 重新归一化，保证不变量：
    - 起始阶段(初评) 永远 order=0（最小，打头）
    - 结束阶段(正式录用) 永远 order 最大（收尾）
    - 其余业务阶段按当前 order 升序填充中间空位（连续 1..N-1）
    解决「插入新阶段导致 order 撞序 / 起止被顶出边界」的问题。
    """
    links = list(ProcessStageLink.objects.filter(process=process, deleted_at__isnull=True).select_related('stage'))
    start = [l for l in links if l.stage_id and l.stage.is_start]
    end = [l for l in links if l.stage_id and l.stage.is_end]
    others = sorted(
        [l for l in links if not (l.stage_id and l.stage.is_start) and not (l.stage_id and l.stage.is_end)],
        key=lambda l: l.order,
    )
    ordered = []
    if start:
        ordered += start
    ordered += others
    if end:
        ordered += end
    for i, l in enumerate(ordered):
        if l.order != i:
            ProcessStageLink.objects.filter(id=l.id).update(order=i)


class ProcessStageLinkSerializer(serializers.ModelSerializer):
    """流程-阶段关联"""
    stage = RecruitmentStageSerializer(read_only=True)
    # 2026-09-20: 创建必填、更新放开。
    #   起止阶段(START_END) 由后端 createProcess 自动填充, FE 走「先 createProcess 再 addProcessLink
    #   补齐业务阶段」的流程, 起止 link 在创建时已存在; 后续 PUT 仅更新 stage_limit / custom_name
    #   等字段, 不应被逼着重传 process_id / stage_id (否则 400 导致时长/改名永远失败)。
    stage_id = serializers.CharField(write_only=True, required=False, help_text='阶段 ID (创建必填, 更新可不传)')
    # 2026-07-03: 用 PrimaryKeyRelatedField + source='process' 替代 auto-gen 的 process FK 字段,
    #   接受 'process_id' 作为入参 (FE send `processId` → drf-camel-case 转 `process_id`),
    #   写入到 model.process (FK). 之前用 'process' field 直接暴露 (read_only=False) 时 DRF
    #   要求入参 key 也叫 'process' → 400 "process: 该字段是必填项".
    # 2026-09-20: required=False — 更新时 process 已由 instance 提供, 不必重传。
    process_id = serializers.PrimaryKeyRelatedField(
        queryset=RecruitmentProcess.objects.all(),
        source='process',
        write_only=True,
        required=False,
        help_text='所属流程 ID (FE 发 processId, 创建必填, 更新可不传)',
    )
    stage_rule = StageRuleSerializer(read_only=True)
    # 流程内展示名：优先 custom_name，否则回退 stage.name（模型 property，字段名即属性名，勿加 source）
    display_name = serializers.CharField(read_only=True)
    # 2026-07-03: 反序列化 EntryCondition (FE: {matchType, conditionType, items[]}) →
    #   JSON-encode 到 entry_rule_expression 字段.
    #   序列化时还原为结构化 dict (FE 期望的 shape).
    entry_condition = serializers.SerializerMethodField()

    class Meta:
        model = ProcessStageLink
        fields = [
            'id', 'process', 'process_id', 'stage', 'stage_id',
            'order', 'is_required', 'is_mandatory', 'custom_name', 'display_name',
            'entry_rule_expression', 'entry_condition',
            'stage_rule',
            'created_at', 'updated_at',
        ]
        # 2026-07-03: 'process' 保留在 fields 用于 read 序列化 (response 包含 processId 字段),
        #   通过 read_only=True 屏蔽写入, 写入改用上面的 process_id (source='process').
        #   'entry_condition' 是 method field, 天然 read-only.
        read_only_fields = ['id', 'process', 'stage', 'stage_rule', 'entry_condition',
                              'display_name', 'created_at', 'updated_at']

    def get_entry_condition(self, obj) -> dict | None:
        return _decode_entry_condition(obj.entry_rule_expression)

    def create(self, validated_data):
        """创建后归一化顺序，保证起止不变量（start 最小、end 最大）。"""
        link = ProcessStageLink.objects.create(**validated_data)
        renormalize_process_orders(link.process)
        link.refresh_from_db()
        return link

    def update(self, instance, validated_data):
        """更新后若动了 order，同样归一化顺序。

        起止阶段(is_start/is_end) 的 is_mandatory 不可被取消：
        perform_destroy 靠 is_mandatory 拦删除, 若允许 PUT 把它置 False,
        则「系统起止不可删除」不变量会被绕过。
        """
        if (
            'is_mandatory' in validated_data
            and validated_data['is_mandatory'] is False
            and instance.stage_id
            and (instance.stage.is_start or instance.stage.is_end)
        ):
            raise serializers.ValidationError(
                {'is_mandatory': '系统起止阶段(初评/正式录用)不可取消必含标记'},
            )
        link = super().update(instance, validated_data)
        if 'order' in validated_data:
            renormalize_process_orders(link.process)
            link.refresh_from_db()
        return link

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
        except (AttributeError, TypeError):  # 表达式字符串预检异常统一 ValidationError 走 400
            raise serializers.ValidationError('表达式语法错误')
        return value.strip()

    def validate(self, attrs):
        """2026-07-03: 如果客户端传了 entry_condition (结构化), 优先 JSON-encode 入库.
        DRF 顺序: 单字段 validate → validate() → save().
        这里仅在 attrs 没同时设置 entry_rule_expression 时, 从 entry_condition 派生."""
        ec = self.initial_data.get('entry_condition') if hasattr(self, 'initial_data') else None
        if ec and isinstance(ec, dict) and 'entry_rule_expression' not in attrs:
            try:
                # 大小校验: items 太多会截断 (CharField max_length=500). 这里只 warn 不报错.
                encoded = json.dumps(ec, ensure_ascii=False)
                if len(encoded) > 500:
                    log.warning('entry_condition JSON 长度 %d > 500, 即将被截断', len(encoded))
                    raise serializers.ValidationError(
                        {'entry_condition': f'配置过大 ({len(encoded)} 字节), 最多 500, 请精简条件项'},
                    )
                attrs['entry_rule_expression'] = encoded
            except (TypeError, ValueError) as e:
                raise serializers.ValidationError({'entry_condition': f'JSON 编码失败: {e}'})
        # 起止边界校验（BR-001 强化）：新增/移动阶段 link 不可越出起止阶段
        #   - process 来自 update 的 self.instance，或 create 的 attrs['process']
        #   - order 优先用本次提交值，否则沿用实例原值（移动场景）
        #   - exclude_link_id 跳过「正在移动的那条」自身，避免和它自己比
        process = self.instance.process if self.instance else attrs.get('process')
        if process is not None:
            order = attrs.get('order')
            if order is None and self.instance is not None:
                order = self.instance.order
            if order is not None:
                assert_within_start_end_bounds(
                    process,
                    order,
                    exclude_link_id=self.instance.id if self.instance else None,
                )
        return attrs


# ============================================================
# 招聘流程（RecruitmentProcess）
# ============================================================
class RecruitmentProcessListSerializer(serializers.ModelSerializer):
    """招聘流程 - 列表

    2026-09-08: 新增 created_by / updated_by 嵌套 UserMinimalSerializer
    让 FE 列表「创建人/最后修改人」列可显示真实姓名（之前一直显示 "-"）
    """
    stage_count = serializers.SerializerMethodField()
    reference_count = serializers.IntegerField(read_only=True)
    created_by = UserMinimalSerializer(read_only=True)
    updated_by = UserMinimalSerializer(read_only=True)

    class Meta:
        model = RecruitmentProcess
        fields = [
            'id', 'code', 'name', 'current_version',
            'is_template', 'template_code',
            'is_enabled', 'validate_resume_score',
            'status', 'applicable_scope', 'description',
            'stage_count', 'reference_count',
            'created_at', 'updated_at',
            'created_by', 'updated_by',
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
# 面试轮次（InterviewRound）
# ============================================================
class InterviewRoundSerializer(serializers.ModelSerializer):
    """面试轮次 - 列表/详情/更新"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = InterviewRound
        fields = [
            'id', 'code', 'name', 'description',
            'evaluation_form_name', 'is_universal', 'status', 'status_display',
            'created_at', 'updated_at', 'created_by', 'updated_by',
        ]
        read_only_fields = [
            'id', 'code', 'created_at', 'updated_at', 'created_by', 'updated_by',
        ]

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('轮次名称必填')
        return value.strip()

    def validate_status(self, value):
        if value not in {InterviewRoundStatus.ACTIVE, InterviewRoundStatus.INACTIVE}:
            raise serializers.ValidationError(f'无效状态: {value}')
        return value


class InterviewRoundCreateSerializer(InterviewRoundSerializer):
    """创建面试轮次：自动生成 R+三位流水号"""

    class Meta(InterviewRoundSerializer.Meta):
        read_only_fields = ['id', 'code', 'created_at', 'updated_at', 'created_by', 'updated_by']

    def create(self, validated_data):
        if not validated_data.get('code'):
            last = (
                InterviewRound.objects.filter(code__regex=r'^R\d+$')
                .order_by('-code')
                .values_list('code', flat=True)
                .first()
            )
            next_num = (int(last[1:]) + 1) if last and last[1:].isdigit() else 1
            validated_data['code'] = f'R{next_num:03d}'
        return super().create(validated_data)


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
    code = serializers.CharField(max_length=20, required=False, allow_blank=True,
                                help_text='可选 — 缺省时自动生成 W+3位流水号')
    name = serializers.CharField(max_length=30)
    description = serializers.CharField(required=False, allow_blank=True, max_length=100)
    is_template = serializers.BooleanField(default=False)
    template_code = serializers.CharField(required=False, allow_blank=True, max_length=50)
    applicable_scope = serializers.JSONField(required=False, default=dict)
    validate_resume_score = serializers.BooleanField(default=True)
    stage_links = NestedStageLinkInputSerializer(many=True, required=False, default=list,
                                                help_text='可选 — FE 也可后续 addProcessLink 单独补')

    def validate_stage_links(self, value):
        if not value:
            return value  # 2026-06-17: 允许空 stage_links, FE 之后单独 addProcessLink
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
        stage_links_data = validated_data.pop('stage_links', [])
        request = self.context.get('request')
        actor = request.user if request and request.user.is_authenticated else None

        # 2026-06-17: code 缺省时自动生成 W + 3位流水号 (FE 的 CustomRecruitmentProcessModal 不发 code)
        if not validated_data.get('code'):
            last = RecruitmentProcess.objects.filter(code__startswith='W').order_by('-code').values_list('code', flat=True).first()
            next_num = (int(last[1:]) + 1) if last and last[1:].isdigit() else 1
            validated_data['code'] = f'W{next_num:03d}'

        process = RecruitmentProcess.objects.create(
            **validated_data,
            current_version='V1.0',
            is_enabled=True,
            status='ENABLED',
            created_by=actor,
            updated_by=actor,
        )

        # ---- 系统必含起止阶段（START_END 类型）：每个流程默认填充, 不可删 ----
        # 取全局唯一的起始阶段(初评) / 结束阶段(正式录用) —— 由 seed 设置 is_start / is_end.
        start_stage = RecruitmentStage.objects.filter(is_start=True, deleted_at__isnull=True).first()
        end_stage = RecruitmentStage.objects.filter(is_end=True, deleted_at__isnull=True).first()

        # FE 可能已在 stage_links 中自带起止阶段（或都不带），统一归一化顺序为：
        #   [起止阶段(若需)] → [FE 提供的其它阶段(保持相对序)] → [结束阶段(若需)]
        # 这样无论 FE 是否传起止，最终流程都「初评打头、正式录用收尾、二者 is_mandatory=True」。
        provided = sorted(stage_links_data, key=lambda v: v.get('order', 0))
        head, middle, tail = [], [], []
        for v in provided:
            if start_stage and v['stage_id'] == start_stage.id:
                head.append(v)
            elif end_stage and v['stage_id'] == end_stage.id:
                tail.append(v)
            else:
                middle.append(v)

        seq = []
        if start_stage:
            seq.append(('START', start_stage, head[0] if head else None))
        for v in middle:
            seq.append(('LINK', None, v))
        if end_stage:
            seq.append(('END', end_stage, tail[0] if tail else None))

        for i, (kind, stage_obj, provided_v) in enumerate(seq):
            if kind == 'START':
                # 起止阶段：即便 FE 已提供，也强制 mandatory + 固定首位（忽略 FE 自带的次要字段）
                ProcessStageLink.objects.create(
                    process=process, stage=stage_obj, order=i,
                    is_required=True, is_mandatory=True,
                    created_by=actor, updated_by=actor,
                )
            elif kind == 'END':
                ProcessStageLink.objects.create(
                    process=process, stage=stage_obj, order=i,
                    is_required=True, is_mandatory=True,
                    created_by=actor, updated_by=actor,
                )
            else:  # LINK: FE 提供的业务阶段（含可能已是起止阶段的强制项, 通过 provided_v 透出）
                v = dict(provided_v)
                stage_id = v.pop('stage_id')
                stage_rule_data = v.pop('stage_rule', None)
                is_mand = (
                    (start_stage and stage_id == start_stage.id)
                    or (end_stage and stage_id == end_stage.id)
                )
                link = ProcessStageLink.objects.create(
                    process=process, stage_id=stage_id, order=i,
                    is_required=v.get('is_required', True),
                    is_mandatory=is_mand,
                    entry_rule_expression=v.get('entry_rule_expression', ''),
                    created_by=actor, updated_by=actor,
                )
                if stage_rule_data:
                    StageRule.objects.create(
                        link=link, **stage_rule_data,
                        created_by=actor, updated_by=actor,
                    )
        return process
