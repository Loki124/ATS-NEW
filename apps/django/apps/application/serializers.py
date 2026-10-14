"""Application Serializers (PRD v4 §6, §13, §14.4)"""
from __future__ import annotations

from rest_framework import serializers

from apps.field_acl.mixins import FieldAclSerializerMixin
from apps.position.serializers import PositionListSerializer
from apps.process.serializers import (
    RecruitmentProcessDetailSerializer,
    RecruitmentStageSerializer,
)

# 2026-08-06 寇豆码: ApplicationState 是 models.py 的**模块级** TextChoices，
#   不是 Application 的内部类。原 get_is_in_grab_pool 写
#   `Application.ApplicationState.ACTIVE` → AttributeError；只要 applications 表非空，
#   GET /api/v1/applications/ 就会 500（表为空时该方法不执行，才侥幸返回 200）。
from .models import (
    Application,
    ApplicationHistory,
    ApplicationStageRecord,
    ApplicationState,
)


# ============================================================
# Stage Record
# ============================================================
class ApplicationStageRecordSerializer(serializers.ModelSerializer):
    """阶段记录"""
    stage_name = serializers.CharField(source='stage.name', read_only=True)
    stage_type = serializers.CharField(source='stage.stage_type', read_only=True)
    state_display = serializers.CharField(source='get_state_display', read_only=True)
    duration_days_computed = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = ApplicationStageRecord
        fields = [
            'id', 'application', 'link', 'stage', 'stage_name', 'stage_type',
            'state', 'state_display',
            'entered_at', 'exited_at', 'duration_days', 'duration_days_computed',
            'time_limit_rule_id', 'total_time_limit_days', 'deadline', 'is_overdue',
            'current_handlers', 'auto_promoted', 'automation_rule_id',
            'note', 'created_at',
        ]
        read_only_fields = fields

    def get_duration_days_computed(self, obj) -> int:
        if obj.exited_at and obj.entered_at:
            return max(0, (obj.exited_at - obj.entered_at).days)
        return obj.duration_days or 0

    def get_is_overdue(self, obj) -> bool:
        from django.utils import timezone
        if obj.state in (
            ApplicationStageRecord.StageState.PASSED,
            ApplicationStageRecord.StageState.FAILED,
            ApplicationStageRecord.StageState.ARCHIVED,
            ApplicationStageRecord.StageState.SKIPPED,
            ApplicationStageRecord.StageState.REJECTED,
            ApplicationStageRecord.StageState.TIMEOUT,
        ):
            return False
        if obj.deadline:
            return timezone.now() > obj.deadline
        return False


# ============================================================
# Application
# ============================================================
class ApplicationListSerializer(FieldAclSerializerMixin, serializers.ModelSerializer):
    """申请列表"""
    acl_entity = 'application'
    # 2026-10-14 P0-4：脱敏职责**唯一收口**到 FieldAclSerializerMixin。
    # 此前本类有一个硬编码 get_candidate_phone（只看 is_super_admin 做两档脱敏），
    # 它完全不受 ACL 规则影响 → 管理员在字段 ACL 页为该角色配的规则对该字段无效，
    # 与P0-2「可配」的承诺直接矛盾，故删除（见下方 candidate_phone 字段说明）。
    candidate_name = serializers.CharField(source='candidate.name', read_only=True)
    # P0-4 关键：`acl_entity='application'` 而不是 'candidate' —— apply_acl 只遍历
    # **序列化输出**的键名，这里输出的键是 `candidate_phone`，而它已被登记在
    # DEFAULT_SENSITIVE_FIELDS['application'] 下（services.py）。若 entity 用
    # 'candidate'，默认脱敏清单里虽有 candidate_phone，但管理员配的 application 规则
    # 就永远命中不到本字段。详见 field_acl/mixins.py 顶部的三条接入硬要求。
    candidate_phone = serializers.CharField(
        source='candidate.phone', read_only=True, default='',
    )
    candidate_email = serializers.CharField(
        source='candidate.email', read_only=True, default='',
    )
    position_title = serializers.CharField(source='position.title', read_only=True)
    position_code = serializers.CharField(source='position.code', read_only=True)
    process_name = serializers.CharField(source='process.name', read_only=True)
    current_stage_name = serializers.CharField(source='current_stage.name', read_only=True)
    state_display = serializers.CharField(source='get_state_display', read_only=True)
    is_overdue = serializers.SerializerMethodField()
    is_in_grab_pool = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = [
            'id', 'code', 'candidate', 'candidate_name',
            'candidate_phone', 'candidate_email',
            'position', 'position_code', 'position_title',
            'process', 'process_name', 'workflow_version',
            'current_link', 'current_stage', 'current_stage_name',
            'state', 'state_display',
            'stage_entered_at', 'stage_deadline', 'is_overdue',
            'total_time_limit_days',
            'is_grabbed', 'grabbed_by', 'grabbed_at', 'is_in_grab_pool',
            'created_at', 'last_advanced_at',
        ]

    def get_is_overdue(self, obj) -> bool:
        from django.utils import timezone
        if not obj.stage_deadline:
            return False
        if obj.state in ('ONBOARDED', 'WITHDRAWN', 'TIMEOUT', 'REJECTED'):
            return False
        return timezone.now() > obj.stage_deadline

    def get_is_in_grab_pool(self, obj) -> bool:
        # bool() 包裹: and 链在中途短路时会返回 None / 模型实例而非 bool，
        # 与 `-> bool` 注解（drf-spectacular 据此生成 schema）不符
        return bool(
            obj.state == ApplicationState.ACTIVE
            and not obj.is_grabbed
            and obj.current_link
            and getattr(obj.current_link, 'stage_rule', None)
            and obj.current_link.stage_rule.is_grab_mode
        )


# 2026-10-09 (#20): 惰性导入, 去掉 application → candidate 模块级边, 切断循环依赖。
#   candidate 侧仅方法内引用 application, 此处晚于 candidate 包加载, 不构成环。
from apps.candidate.serializers import CandidateListSerializer


class ApplicationDetailSerializer(FieldAclSerializerMixin, serializers.ModelSerializer):
    """申请详情"""
    # P0-4：详情端接 mixin。此前详情端**完全不受字段 ACL 约束** —— 列表端有那个
    # 硬编码 get_candidate_phone 挡一下，详情端却直接吐明文（P0-2 核心泄漏面）。
    # 注意内嵌的 CandidateListSerializer 已自带 mixin(entity='candidate')，
    # 两层不冲突：外层管本类自己输出的顶层键，内层管 candidate 子对象。
    acl_entity = 'application'
    candidate = CandidateListSerializer(read_only=True)
    position = PositionListSerializer(read_only=True)
    process = RecruitmentProcessDetailSerializer(read_only=True)
    current_stage = RecruitmentStageSerializer(read_only=True)
    current_stage_records = serializers.SerializerMethodField()
    all_records = serializers.SerializerMethodField()
    histories = serializers.SerializerMethodField()
    state_display = serializers.CharField(source='get_state_display', read_only=True)
    grabbed_by_name = serializers.CharField(source='grabbed_by.username', read_only=True, default='')
    is_overdue = serializers.SerializerMethodField()
    soft_reject_count = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = [
            'id', 'code',
            'candidate', 'position', 'process', 'workflow_version',
            'current_link', 'current_stage', 'current_stage_records', 'all_records',
            'state', 'state_display', 'histories',
            'time_limit_rule_id', 'total_time_limit_days',
            'stage_entered_at', 'stage_deadline', 'is_overdue',
            'is_grabbed', 'grabbed_by', 'grabbed_by_name', 'grabbed_at',
            'soft_reject_count',
            'last_advanced_at', 'created_at', 'updated_at',
        ]

    def get_current_stage_records(self, obj):
        if not obj.current_link:
            return []
        recs = obj.stage_records.filter(
            link=obj.current_link, deleted_at__isnull=True,
        ).order_by('-entered_at')
        return ApplicationStageRecordSerializer(recs, many=True).data

    def get_all_records(self, obj):
        recs = obj.stage_records.filter(deleted_at__isnull=True).order_by('entered_at')
        return ApplicationStageRecordSerializer(recs, many=True).data

    def get_histories(self, obj):
        histories = obj.histories.filter(deleted_at__isnull=True).order_by('-created_at')[:50]
        return ApplicationHistorySerializer(histories, many=True).data

    def get_is_overdue(self, obj) -> bool:
        from django.utils import timezone
        if not obj.stage_deadline:
            return False
        if obj.state in ('ONBOARDED', 'WITHDRAWN', 'TIMEOUT', 'REJECTED'):
            return False
        return timezone.now() > obj.stage_deadline

    def get_soft_reject_count(self, obj) -> int:
        from apps.application.services.soft_reject import SoftRejectService
        return SoftRejectService.count_soft_rejects(obj)


class ApplicationCreateSerializer(serializers.Serializer):
    """创建申请入参"""
    candidate_id = serializers.CharField()
    position_id = serializers.CharField()
    process_id = serializers.CharField(required=False, allow_blank=True)
    initial_stage_id = serializers.CharField(required=False, allow_blank=True)
    extra = serializers.DictField(required=False)


class ApplicationHistorySerializer(serializers.ModelSerializer):
    from_stage_name = serializers.CharField(source='from_stage.name', read_only=True, default='')
    to_stage_name = serializers.CharField(source='to_stage.name', read_only=True, default='')
    operator_name = serializers.CharField(source='operator.username', read_only=True, default='')

    class Meta:
        model = ApplicationHistory
        fields = [
            'id', 'application', 'action',
            'from_stage', 'from_stage_name',
            'to_stage', 'to_stage_name',
            'detail', 'operator', 'operator_name', 'is_auto',
            'created_at',
        ]


class ApplicationAdvanceSerializer(serializers.Serializer):
    """推进申请"""
    reason = serializers.CharField(required=False, allow_blank=True)
    skip_entry_condition = serializers.BooleanField(default=False)


class ApplicationJumpSerializer(serializers.Serializer):
    """跳到指定阶段"""
    target_stage_id = serializers.CharField()
    reason = serializers.CharField(required=False, allow_blank=True)
    skip_entry_condition = serializers.BooleanField(default=False)


class ApplicationChangeProcessSerializer(serializers.Serializer):
    """跨流程线迁移入参（T8 / §3.1）。

    三个字段全部 required —— 落点不允许由服务端猜（§3.3：两条流程线的 order
    编号体系彼此独立，自动映射会得到"看起来有、实则错"的落点）。

    ``reason`` 强制非空白：跨流程线是 correction 操作，审计里没有理由等于没有审计。
    这一层只管入参形态（缺参 / 空白 → 400）；"目标流程是否可用""阶段是否属于目标
    流程"这类业务校验属服务层，抛 StateTransitionError → 409。
    """
    target_process_id = serializers.CharField(required=True, allow_blank=False)
    target_stage_id = serializers.CharField(required=True, allow_blank=False)
    reason = serializers.CharField(required=True, allow_blank=False, max_length=500)


class ApplicationSoftRejectSerializer(serializers.Serializer):
    """软拒"""
    reason = serializers.CharField()


class ApplicationWithdrawSerializer(serializers.Serializer):
    """撤回"""
    reason = serializers.CharField()


class ApplicationPauseSerializer(serializers.Serializer):
    """暂停"""
    reason = serializers.CharField(required=False, allow_blank=True)


class ApplicationGrabSerializer(serializers.Serializer):
    """抢单"""
    pass


class ApplicationReleaseSerializer(serializers.Serializer):
    """释放抢单"""
    reason = serializers.CharField(required=False, allow_blank=True)


class GrabPoolQuerySerializer(serializers.Serializer):
    """抢单池查询"""
    stage_id = serializers.CharField(required=False, allow_blank=True)
    position_id = serializers.CharField(required=False, allow_blank=True)
    limit = serializers.IntegerField(default=50, min_value=1, max_value=200)


class InvitationCreateSerializer(serializers.Serializer):
    """创建邀请入参"""
    application_id = serializers.CharField()
    channel = serializers.ChoiceField(
        choices=['EMAIL', 'SMS', 'WECOM', 'IN_APP'],
        default='EMAIL',
    )
    template_code = serializers.CharField(required=False, allow_blank=True)
    custom_message = serializers.CharField(required=False, allow_blank=True)
    expires_hours = serializers.IntegerField(default=72, min_value=1, max_value=720)


class InvitationRespondSerializer(serializers.Serializer):
    """候选人响应"""
    code = serializers.CharField()
    accept = serializers.BooleanField()
    note = serializers.CharField(required=False, allow_blank=True)
