"""campus_assessment 序列化器。

- 字段暴露（camelCase 由 djangorestframework-camel-case 自动转换，前端直接消费）；
- 写时业务校验：
  · 人员必须在**当前用户可见范围**内（否则可给不可见的人建记录 = 越权写入）；
  · 模板 items 嵌套写入（新增 / 更新 / 删除三态，见契约 §2.2「含 items 嵌套写入」）；
  · 月度考核一旦「核对通过」即锁定（逆向清单 §4.3「核对通过（锁定当月…）」）。
"""
from rest_framework import serializers

from . import ranking as R
from .models import (
    AssessmentTemplate,
    AssessmentTemplateItem,
    AttendanceMonthly,
    AttendanceRecord,
    FeedbackRecord,
    FiveForceScore,
    MonthlyAssessment,
    MonthlyReport,
    MonthlyReportScore,
    Probation,
)


class VisiblePersonMixin:
    """写时校验：目标人员必须在当前用户可见范围内。

    🔴 为什么必须校验：列表端点做了可见范围收窄，但**写端点**若不校验，
    带教导师只要猜到 Person.id 就能给别人的徒弟建考核/反馈记录 ——
    「看不到却能改」是比「看得到」更严重的越权。
    """

    def _validate_person_visible(self, person):
        request = self.context.get('request')
        if request is None or not getattr(request, 'user', None):
            return
        from .services import visible_person_qs

        if not visible_person_qs(request.user).filter(pk=person.pk).exists():
            raise serializers.ValidationError({'person': '该校招生不在你的可见范围内'})


class PersonNameMixin(serializers.Serializer):
    """人员姓名 / 班级名等展示字段（只读，不落库）。

    ⚠️ 必须继承 `serializers.Serializer`：DRF 的 `SerializerMetaclass` 只从
    **Serializer 子类**的 `_declared_fields` 里收集已声明字段 —— 若 mixin 是普通
    对象基类，`person_name` / `class_name` 不会进入字段表，ModelSerializer 会去
    模型上找同名字段并抛 `ImproperlyConfigured: Field name 'person_name' is not valid`。
    """

    person_name = serializers.SerializerMethodField()
    class_name = serializers.SerializerMethodField()

    def get_person_name(self, obj):
        return obj.person.name if obj.person_id else ''

    def get_class_name(self, obj):
        person = getattr(obj, 'person', None)
        if person is None or not person.class_room_id:
            return ''
        return person.class_room.name


# ---------------------------------------------------------------------------
# 考核模板
# ---------------------------------------------------------------------------
class AssessmentTemplateItemSerializer(serializers.ModelSerializer):
    """模板维度（权重百分比 + 目标要求）。"""

    class Meta:
        model = AssessmentTemplateItem
        fields = ['id', 'template', 'name', 'weight', 'target']
        read_only_fields = ['id', 'template']


class AssessmentTemplateSerializer(serializers.ModelSerializer):
    """考核模板（items 嵌套写入）。

    嵌套写入口径（契约 §2.2「assessment-templates/（含 items 嵌套写入）」）：
    - 传了 `items` → 整体替换该模板的维度集合（带 id 的更新、不带 id 的新增、
      本次未出现的删除）；
    - 没传 `items` → 不动已有维度（部分更新语义）。
    """

    items = AssessmentTemplateItemSerializer(many=True, required=False)

    class Meta:
        model = AssessmentTemplate
        fields = [
            'id', 'name', 'scope_type', 'scope_values', 'stage', 'period_type',
            'enabled', 'items', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_scope_values(self, value):
        """适用范围取值必须是列表（契约 §1.1：JSON 字段 default=list）。"""
        if value in (None, ''):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError('适用范围取值必须是列表')
        return value

    def create(self, validated_data):
        items = validated_data.pop('items', None)
        template = AssessmentTemplate.objects.create(**validated_data)
        if items is not None:
            self._write_items(template, items)
        return template

    def update(self, instance, validated_data):
        items = validated_data.pop('items', None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        if items is not None:
            self._write_items(instance, items)
        return instance

    @staticmethod
    def _write_items(template, items):
        """整体替换模板维度（带 id 更新 / 不带 id 新增 / 缺失删除）。"""
        keep_ids = []
        for payload in items:
            item_id = payload.pop('id', None)
            if item_id:
                AssessmentTemplateItem.objects.filter(pk=item_id, template=template).update(**payload)
                keep_ids.append(item_id)
            else:
                AssessmentTemplateItem.objects.create(template=template, **payload)
        if keep_ids:
            AssessmentTemplateItem.objects.filter(template=template).exclude(id__in=keep_ids).delete()
        else:
            AssessmentTemplateItem.objects.filter(template=template).delete()


# ---------------------------------------------------------------------------
# 月度考核
# ---------------------------------------------------------------------------
class MonthlyAssessmentSerializer(PersonNameMixin, VisiblePersonMixin, serializers.ModelSerializer):
    """月度考核。

    `total_score` 是**只读**聚合字段：按 A1 实时算
    `round(KPI×0.6 + 考试×0.4) + 加减分`，不落库（避免与公式漂移）。
    """

    total_score = serializers.SerializerMethodField()
    checked_by_name = serializers.SerializerMethodField()

    class Meta:
        model = MonthlyAssessment
        fields = [
            'id', 'person', 'person_name', 'class_name', 'ym', 'kpi', 'exam',
            'adjust', 'total_score', 'status', 'note', 'checked_by',
            'checked_by_name', 'checked_at', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'total_score', 'checked_by', 'checked_at', 'created_at', 'updated_at',
        ]

    def get_total_score(self, obj):
        return R.monthly_total_score(obj.kpi, obj.exam, obj.adjust)

    def get_checked_by_name(self, obj):
        return obj.checked_by.full_name if obj.checked_by_id else ''

    def validate(self, attrs):
        person = attrs.get('person') or getattr(self.instance, 'person', None)
        if person is not None:
            self._validate_person_visible(person)
        # 已核对的月份被锁定：不允许再改分数（逆向清单 §4.3「核对通过（锁定当月…）」）
        if self.instance and self.instance.status == MonthlyAssessment.Status.CHECKED:
            locked = {'kpi', 'exam', 'adjust', 'status', 'ym'}
            touched = locked.intersection(set(attrs.keys()))
            if touched:
                raise serializers.ValidationError(
                    {'detail': f'该月已核对通过，不可再修改（{"/".join(sorted(touched))}）'})
        return attrs


# ---------------------------------------------------------------------------
# 五行五力
# ---------------------------------------------------------------------------
class FiveForceScoreSerializer(PersonNameMixin, VisiblePersonMixin, serializers.ModelSerializer):
    """五行五力（含只读均值 `force_avg` = A5 公式）。"""

    force_avg = serializers.SerializerMethodField()
    scorer_name = serializers.SerializerMethodField()

    class Meta:
        model = FiveForceScore
        fields = [
            'id', 'person', 'person_name', 'class_name', 'learning', 'execution',
            'collaboration', 'innovation', 'resilience', 'force_avg', 'scored_at',
            'scorer', 'scorer_name', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'force_avg', 'scorer', 'created_at', 'updated_at']

    def get_force_avg(self, obj):
        return R.dim_force(obj.dimension_values)

    def get_scorer_name(self, obj):
        return obj.scorer.full_name if obj.scorer_id else ''

    def validate(self, attrs):
        person = attrs.get('person') or getattr(self.instance, 'person', None)
        if person is not None:
            self._validate_person_visible(person)
        return attrs


# ---------------------------------------------------------------------------
# 考勤
# ---------------------------------------------------------------------------
class AttendanceRecordSerializer(PersonNameMixin, VisiblePersonMixin, serializers.ModelSerializer):
    """每日打卡。"""

    class Meta:
        model = AttendanceRecord
        fields = [
            'id', 'person', 'person_name', 'class_name', 'date', 'punch_time',
            'status', 'remark', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, attrs):
        person = attrs.get('person') or getattr(self.instance, 'person', None)
        if person is not None:
            self._validate_person_visible(person)
        return attrs


class AttendanceMonthlySerializer(PersonNameMixin, VisiblePersonMixin, serializers.ModelSerializer):
    """月度考勤汇总（含只读 `attendance_dim` = A9 公式）。"""

    attendance_dim = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceMonthly
        fields = [
            'id', 'person', 'person_name', 'class_name', 'ym', 'attend_days',
            'late_count', 'leave_days', 'status', 'attendance_dim',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'attendance_dim', 'created_at', 'updated_at']

    def get_attendance_dim(self, obj):
        return R.attendance_dim([
            {'attend_days': obj.attend_days, 'late_count': obj.late_count},
        ])

    def validate(self, attrs):
        person = attrs.get('person') or getattr(self.instance, 'person', None)
        if person is not None:
            self._validate_person_visible(person)
        return attrs


# ---------------------------------------------------------------------------
# 反馈记录
# ---------------------------------------------------------------------------
class FeedbackRecordSerializer(PersonNameMixin, VisiblePersonMixin, serializers.ModelSerializer):
    """反馈 / 异常记录（问题·情况记录 + 导师带教反馈）。"""

    reporter_name = serializers.SerializerMethodField()
    handler_name = serializers.SerializerMethodField()
    has_evidence = serializers.SerializerMethodField()

    class Meta:
        model = FeedbackRecord
        fields = [
            'id', 'person', 'person_name', 'class_name', 'date', 'reporter',
            'reporter_name', 'category', 'type', 'content', 'handling', 'status',
            'attachments', 'has_evidence', 'handler', 'handler_name', 'handled_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'reporter', 'handler', 'handled_at', 'has_evidence',
            'created_at', 'updated_at',
        ]

    def get_reporter_name(self, obj):
        return obj.reporter.full_name if obj.reporter_id else ''

    def get_handler_name(self, obj):
        return obj.handler.full_name if obj.handler_id else ''

    def get_has_evidence(self, obj):
        return bool(obj.attachments)

    def validate_attachments(self, value):
        if value in (None, ''):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError('证据附件必须是列表')
        return value

    def validate(self, attrs):
        person = attrs.get('person') or getattr(self.instance, 'person', None)
        if person is not None:
            self._validate_person_visible(person)
        return attrs


# ---------------------------------------------------------------------------
# 月报
# ---------------------------------------------------------------------------
class MonthlyReportScoreSerializer(serializers.ModelSerializer):
    """月报评分明细（五子项 + 角色总分）。"""

    scorer_name = serializers.SerializerMethodField()

    class Meta:
        model = MonthlyReportScore
        fields = [
            'id', 'report', 'role', 'case', 'insight', 'problem', 'clarity',
            'executable', 'total', 'scorer', 'scorer_name', 'comment', 'scored_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'report', 'total', 'scorer', 'scored_at', 'created_at', 'updated_at']

    def get_scorer_name(self, obj):
        return obj.scorer.full_name if obj.scorer_id else ''


class MonthlyReportSerializer(PersonNameMixin, VisiblePersonMixin, serializers.ModelSerializer):
    """月报（scores 只读嵌套；综合分由评分动作回算，不接受前端直写）。"""

    scores = MonthlyReportScoreSerializer(many=True, read_only=True)

    class Meta:
        model = MonthlyReport
        fields = [
            'id', 'person', 'person_name', 'class_name', 'ym', 'submitted_at',
            'status', 'business_score', 'growth_score', 'final_score', 'comment',
            'scores', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'submitted_at', 'status', 'business_score', 'growth_score',
            'final_score', 'created_at', 'updated_at',
        ]

    def validate(self, attrs):
        person = attrs.get('person') or getattr(self.instance, 'person', None)
        if person is not None:
            self._validate_person_visible(person)
        return attrs


# ---------------------------------------------------------------------------
# 试用期
# ---------------------------------------------------------------------------
class ProbationSerializer(PersonNameMixin, VisiblePersonMixin, serializers.ModelSerializer):
    """试用期考核。"""

    decided_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Probation
        fields = [
            'id', 'person', 'person_name', 'class_name', 'rotation_result',
            'rotation_level', 'p3m_kpi', 'p3m_competency', 'decision',
            'decided_by', 'decided_by_name', 'decided_at', 'decision_note',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'decision', 'decided_by', 'decided_at', 'created_at', 'updated_at',
        ]

    def get_decided_by_name(self, obj):
        return obj.decided_by.full_name if obj.decided_by_id else ''

    def validate(self, attrs):
        person = attrs.get('person') or getattr(self.instance, 'person', None)
        if person is not None:
            self._validate_person_visible(person)
        return attrs
