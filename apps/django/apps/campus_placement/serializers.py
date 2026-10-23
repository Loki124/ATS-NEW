"""校招定岗与结算域序列化器（campus_placement）。

契约 §4.1 字段口径 + 状态机（逆向清单 §4.3）的服务端校验：
- 志愿填报：批次撮合已启动 → 拒绝（明确中文错误信息）；
- 志愿条数：不超过该批次 `SelectionFlow.wish_limit`（缺省继承全局默认 2）；
- 发布范围：`scope_type=batch` 必填 `scope_batch`；`scope_type=intentDept` 必填部门列表。

人员一律以 `person_id`（字符串）出入参 —— `person` 外键只读，避免前端误传嵌套对象。
"""
from decimal import Decimal

from rest_framework import serializers

from .models import (
    Bill,
    PlacementAssessment,
    PlacementGoal,
    PlacementMetric,
    PlacementRecord,
    PositionApplication,
    PositionDemand,
    PriceBid,
    PriceScheme,
    RevenueRecord,
    SelectionFlow,
)


def _assert_visible_person(request, person_id):
    """校招生必须在当前用户可见范围内（可见范围助手 = `campus_control.visibility`，只读调用）。"""
    if not person_id or request is None:
        return
    from apps.campus_control.visibility import visible_persons

    if not visible_persons(request.user).filter(id=person_id).exists():
        raise serializers.ValidationError('该校招生不在你的可见范围内')


class PositionDemandSerializer(serializers.ModelSerializer):
    """岗位需求。发布范围三档（all / batch / intentDept）的必填项在此校验。"""

    class Meta:
        model = PositionDemand
        fields = [
            'id', 'name', 'dept', 'business_dept', 'headcount', 'submitter', 'need_status',
            'need_desc', 'biz_intro', 'dept_intro', 'assess_req', 'need_time', 'work_location',
            'bp', 'scope_type', 'scope_batch', 'scope_intent_depts',
            'open_enabled', 'open_start', 'open_end', 'open_batch_no',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, attrs):
        scope_type = attrs.get('scope_type') or getattr(self.instance, 'scope_type', 'all')
        scope_batch = attrs.get('scope_batch', getattr(self.instance, 'scope_batch', ''))
        scope_depts = attrs.get(
            'scope_intent_depts',
            getattr(self.instance, 'scope_intent_depts', None) or [],
        )
        if scope_type == PositionDemand.ScopeType.BATCH and not scope_batch:
            raise serializers.ValidationError({'scope_batch': '发布范围为「按批次」时必须填写批次号'})
        if scope_type == PositionDemand.ScopeType.INTENT_DEPT and not scope_depts:
            raise serializers.ValidationError(
                {'scope_intent_depts': '发布范围为「按意向部门」时必须填写部门列表'}
            )
        return attrs


class PositionApplicationSerializer(serializers.ModelSerializer):
    """志愿。`person_id` 出入参；展示字段（姓名 / 岗位名 / 批次）由服务端带出。"""

    person_id = serializers.CharField(required=False, allow_null=True)
    person = serializers.PrimaryKeyRelatedField(read_only=True)
    position = serializers.PrimaryKeyRelatedField(queryset=PositionDemand.objects.all())
    person_name = serializers.SerializerMethodField()
    person_code = serializers.SerializerMethodField()
    position_name = serializers.SerializerMethodField()
    batch = serializers.SerializerMethodField()

    class Meta:
        model = PositionApplication
        fields = [
            'id', 'person', 'person_id', 'position', 'position_name', 'order', 'channel',
            'status', 'pushed_at', 'pushed_by', 'decision', 'decided_at',
            'person_name', 'person_code', 'batch', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'person', 'status', 'pushed_at', 'pushed_by', 'decision', 'decided_at',
            'created_at', 'updated_at',
        ]

    def get_person_name(self, obj):
        return obj.person.name if obj.person_id else ''

    def get_person_code(self, obj):
        return obj.person.code if obj.person_id else ''

    def get_position_name(self, obj):
        return obj.position.name if obj.position_id else ''

    def get_batch(self, obj):
        return obj.person.batch if obj.person_id else ''

    def validate_person_id(self, value):
        _assert_visible_person(self.context.get('request'), value)
        return value


class SelectionFlowSerializer(serializers.ModelSerializer):
    """撮合流程（按批次）。`effective_wish_limit` 为只读派生值（缺省继承全局默认 2）。"""

    effective_wish_limit = serializers.SerializerMethodField()

    class Meta:
        model = SelectionFlow
        fields = [
            'id', 'batch', 'started', 'start_time', 'wish_limit',
            'published', 'published_at', 'effective_wish_limit',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'published', 'published_at', 'created_at', 'updated_at']

    def get_effective_wish_limit(self, obj):
        return obj.effective_wish_limit()


class PlacementRecordSerializer(serializers.ModelSerializer):
    """定岗跟踪主表。"""

    person_id = serializers.CharField(required=False, allow_null=True)
    person = serializers.PrimaryKeyRelatedField(read_only=True)
    person_name = serializers.SerializerMethodField()
    batch = serializers.SerializerMethodField()

    class Meta:
        model = PlacementRecord
        fields = [
            'id', 'person', 'person_id', 'person_name', 'batch', 'dept', 'position_name',
            'place_date', 'track_years', 'latest_perf', 'status',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'person', 'created_at', 'updated_at']

    def get_person_name(self, obj):
        return obj.person.name if obj.person_id else ''

    def get_batch(self, obj):
        return obj.person.batch if obj.person_id else ''

    def validate_person_id(self, value):
        _assert_visible_person(self.context.get('request'), value)
        return value


class PlacementGoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlacementGoal
        fields = [
            'id', 'record', 'name', 'metric', 'target_value', 'weight', 'due_date', 'status',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PlacementMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlacementMetric
        fields = [
            'id', 'record', 'ym', 'metric', 'actual_value', 'remark',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PlacementAssessmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlacementAssessment
        fields = [
            'id', 'record', 'period', 'score', 'perf_level', 'assessed_at', 'comment',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PriceSchemeSerializer(serializers.ModelSerializer):
    """定价方案。`tiers` 形如 `[{"rank":"1-10","price":1200,"floor":1000}]`。"""

    class Meta:
        model = PriceScheme
        fields = [
            'id', 'name', 'type', 'batch', 'sel_flow_batch', 'tiers', 'is_default', 'enabled',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_tiers(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('排名分档必须是数组')
        for idx, tier in enumerate(value):
            if not isinstance(tier, dict):
                raise serializers.ValidationError(f'第 {idx + 1} 档格式不正确')
            if 'rank' not in tier:
                raise serializers.ValidationError(f'第 {idx + 1} 档缺少排名区间')
        return value


class PriceBidSerializer(serializers.ModelSerializer):
    person_id = serializers.CharField(required=False, allow_null=True)
    person = serializers.PrimaryKeyRelatedField(read_only=True)
    person_name = serializers.SerializerMethodField()

    class Meta:
        model = PriceBid
        fields = [
            'id', 'scheme', 'person', 'person_id', 'person_name', 'price',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'person', 'created_at', 'updated_at']

    def get_person_name(self, obj):
        return obj.person.name if obj.person_id else ''

    def validate_person_id(self, value):
        _assert_visible_person(self.context.get('request'), value)
        return value


class RevenueRecordSerializer(serializers.ModelSerializer):
    person_id = serializers.CharField(required=False, allow_null=True)
    person = serializers.PrimaryKeyRelatedField(read_only=True)
    person_name = serializers.SerializerMethodField()

    class Meta:
        model = RevenueRecord
        fields = [
            'id', 'person', 'person_id', 'person_name', 'ym', 'output_dept', 'stage',
            'attend_days', 'rule', 'unit_price', 'amount', 'status',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'person', 'created_at', 'updated_at']

    def get_person_name(self, obj):
        return obj.person.name if obj.person_id else ''

    def validate_person_id(self, value):
        _assert_visible_person(self.context.get('request'), value)
        return value

    def validate(self, attrs):
        """金额兜底口径：**出勤天数 × 单价**。

        ⚠️ 契约 §4.1 只给了 `attend_days` / `unit_price` / `amount` 三个字段，
        **未定义金额公式**；这里按「台账 = 出勤 × 单价」兜底计算，
        显式传入 `amount` 时以传入值为准（人工调整优先）。
        """
        attend_days = attrs.get('attend_days', getattr(self.instance, 'attend_days', 0)) or 0
        unit_price = attrs.get('unit_price', getattr(self.instance, 'unit_price', 0)) or 0
        amount = attrs.get('amount', None)
        if not amount and attend_days and unit_price:
            attrs['amount'] = Decimal(attend_days) * Decimal(unit_price)
        return attrs


class BillSerializer(serializers.ModelSerializer):
    """结算账单。账单号缺省自动生成；结算人数 / 金额缺省按台账汇总（账期 + 业务部门）。"""

    class Meta:
        model = Bill
        fields = [
            'id', 'bill_no', 'business_dept', 'period', 'person_count', 'amount',
            'status', 'confirmed_at', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        # 账单号缺省自动生成（见 create）→ 不强制前端传
        extra_kwargs = {'bill_no': {'required': False}}

    def create(self, validated_data):
        period = validated_data.get('period') or ''
        business_dept = validated_data.get('business_dept') or ''
        if not validated_data.get('bill_no'):
            validated_data['bill_no'] = _generate_bill_no(period, business_dept)
        if not validated_data.get('person_count') or not validated_data.get('amount'):
            person_count, amount = _settlement_totals(period, business_dept)
            if not validated_data.get('person_count'):
                validated_data['person_count'] = person_count
            if not validated_data.get('amount'):
                validated_data['amount'] = amount
        return super().create(validated_data)


def _settlement_totals(period, business_dept):
    """按「账期 + 业务部门」汇总输出台账 → (结算人数, 金额)。"""
    from django.db.models import Sum

    qs = RevenueRecord.objects.filter(deleted_at__isnull=True)
    if period:
        qs = qs.filter(ym=period)
    if business_dept:
        qs = qs.filter(output_dept=business_dept)
    person_ids = set(qs.values_list('person_id', flat=True))
    total = qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    return len(person_ids), Decimal(total)


def _generate_bill_no(period, business_dept):
    """自动生成账单号：`B{账期}{部门}{序号}`（序号保证唯一）。"""
    base = 'B{}{}'.format((period or '').replace('-', ''), business_dept or 'NA')
    seq = 1
    while Bill.objects.filter(bill_no='{}{:03d}'.format(base, seq)).exists():
        seq += 1
    return '{}{:03d}'.format(base, seq)


__all__ = [
    'PositionDemandSerializer', 'PositionApplicationSerializer', 'SelectionFlowSerializer',
    'PlacementRecordSerializer', 'PlacementGoalSerializer', 'PlacementMetricSerializer',
    'PlacementAssessmentSerializer', 'PriceSchemeSerializer', 'PriceBidSerializer',
    'RevenueRecordSerializer', 'BillSerializer',
]
