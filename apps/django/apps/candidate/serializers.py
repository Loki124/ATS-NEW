"""Candidate Serializers (PRD v4 §14.3)"""
from __future__ import annotations

from rest_framework import serializers

from apps.field_acl.mixins import FieldAclSerializerMixin

from .models import Candidate, CandidateHistory, CandidateTag
from .services import (
    CandidateCreateData,
    validate_email,
    validate_id_card,
    validate_phone,
)


# ============================================================
# Tag
# ============================================================
class CandidateTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateTag
        fields = ['id', 'name', 'color', 'category']


# ============================================================
# Candidate
# ============================================================
class CandidateListSerializer(FieldAclSerializerMixin, serializers.ModelSerializer):
    """候选人列表 - 精简字段

    2026-08-03 R2 (寇豆码): 接上 FieldAclSerializerMixin。
    此前列表接口对任意登录用户直吐明文 phone / email。
    """
    acl_entity = 'candidate'
    acl_strict = True  # HTTP API 序列化器: 即便意外没拿到 request context 也 fail-closed 脱敏

    state_display = serializers.CharField(source='get_current_state_display', read_only=True)
    source_channel_name = serializers.CharField(
        source='source_channel.name', read_only=True, default='',
    )
    application_count = serializers.SerializerMethodField()

    class Meta:
        model = Candidate
        fields = [
            'id', 'code', 'recruit_type', 'name', 'phone', 'email', 'gender', 'age',
            'highest_education', 'work_years', 'current_city',
            'current_state', 'state_display',
            'source_channel', 'source_channel_name',
            'referral_type', 'tags',
            'current_company', 'current_position',
            'created_at', 'application_count',
        ]

    def get_application_count(self, obj) -> int:
        return obj.applications.filter(deleted_at__isnull=True).count()


class CandidateHistorySerializer(serializers.ModelSerializer):
    # 模型审计字段为 created_by (FullAuditModel), 无 operator 字段
    operator_name = serializers.CharField(source='created_by.username', read_only=True, default='')

    class Meta:
        model = CandidateHistory
        fields = ['id', 'seq', 'action', 'detail', 'created_by', 'operator_name', 'created_at']


class CandidateDetailSerializer(FieldAclSerializerMixin, serializers.ModelSerializer):
    """候选人详情

    2026-08-03 R2 (寇豆码): 接上 FieldAclSerializerMixin。
    此前详情接口对任意登录用户直吐明文 phone / email / id_card_no
    (id_card_no 虽然在 DB 里是密文, 但序列化时 EncryptedCharField 已解密, 等于白加密)。
    """
    acl_entity = 'candidate'
    acl_strict = True  # HTTP API 序列化器: 即便意外没拿到 request context 也 fail-closed 脱敏

    state_display = serializers.CharField(source='get_current_state_display', read_only=True)
    source_channel_name = serializers.CharField(
        source='source_channel.name', read_only=True, default='',
    )
    referrer_name = serializers.CharField(source='referrer.username', read_only=True, default='')
    # 锁定人：优先招聘官（候选人级负责人），为空时由前端回退到投递记录认领人
    recruiter_name = serializers.CharField(source='recruiter.username', read_only=True, default='')
    # 简历来源：由真实入库形态推导（摩卡同步 / 附件上传 / 手动录入），非虚构枚举
    resume_source = serializers.SerializerMethodField()
    histories = CandidateHistorySerializer(many=True, read_only=True)
    applications = serializers.SerializerMethodField()
    soft_reject_stats = serializers.SerializerMethodField()

    class Meta:
        model = Candidate
        fields = [
            'id', 'code', 'recruit_type', 'name', 'phone', 'email', 'gender', 'age', 'birth_date', 'id_card_no',
            'highest_education', 'work_years',
            'current_city', 'expected_city', 'current_company', 'current_position',
            'expected_salary', 'resume_file_url', 'resume_text',
            'source_channel', 'source_channel_name',
            'referrer', 'referrer_name', 'referral_type',
            'recruiter', 'recruiter_name', 'resume_source',
            'resume_score', 'tags', 'current_state', 'state_display',
            'is_blacklisted', 'blacklist_reason',
            'moka_candidate_id', 'extra',
            'created_at', 'updated_at',
            'histories', 'applications', 'soft_reject_stats',
        ]
        read_only_fields = ['code', 'current_state', 'created_at', 'updated_at']

    def get_resume_source(self, obj) -> str:
        """简历来源（按真实数据推导，禁止虚构）：

        - moka_candidate_id 有值 → 第三方（摩卡）同步入库
        - resume_file_url 有值 → 附件上传
        - 其余 → 手动录入
        """
        if obj.moka_candidate_id:
            return '摩卡同步'
        if obj.resume_file_url:
            return '附件上传'
        return '手动录入'

    def get_applications(self, obj):
        # retrieve 路径已 Prefetch（含 deleted_at 过滤 + -created_at 排序），直接走缓存，
        # 避免 position/process/current_stage/grabbed_by/stage_links 逐行 N+1；
        # create/update 等无预取路径回落过滤查询，保证软删记录不泄漏。
        apps = (getattr(obj, '_prefetched_objects_cache', {}) or {}).get('applications')
        if apps is None:
            apps = obj.applications.filter(deleted_at__isnull=True).order_by('-created_at')
        return [
            {
                'id': app.id,
                'code': app.code,
                'position_title': app.position.title if app.position else None,
                # 所属流程（应聘职位对应的招聘流程）与流程版本
                'process_name': app.process.name if app.process else None,
                'workflow_version': app.workflow_version or '',
                'state': app.state,
                'current_stage': app.current_stage.name if app.current_stage else None,
                # 锁定人兜底：抢单/认领人（候选人级招聘官为空时展示）
                'grabbed_by_name': app.grabbed_by.username if app.grabbed_by else '',
                # 流程阶段有序列表（按 order 升序），供前端渲染「当前阶段」步骤条
                # 2026-10-16 补软删口径：反向 stage_links 是原生 Manager 不过滤软删，
                #   流程里「移除阶段」留下的软删 link 会混进步骤条（同 stage_count 一族）。
                'stage_list': [
                    link.display_name
                    for link in (
                        app.process.stage_links.filter(deleted_at__isnull=True)
                        if app.process else []
                    )
                ],
                'created_at': app.created_at.isoformat(),
            }
            for app in apps[:20]
        ]

    def get_soft_reject_stats(self, obj):
        from apps.application.services.soft_reject import SoftRejectService
        return SoftRejectService.get_soft_reject_stats(obj.id)


class CandidateCreateSerializer(serializers.Serializer):
    """创建候选人入参"""
    name = serializers.CharField(max_length=50)
    phone = serializers.CharField(max_length=20)
    email = serializers.EmailField(required=False, allow_blank=True)
    gender = serializers.CharField(required=False, allow_blank=True, max_length=8)
    age = serializers.IntegerField(required=False, allow_null=True)
    birth_date = serializers.DateField(required=False, allow_null=True)
    highest_education = serializers.CharField(required=False, allow_blank=True, max_length=50)
    work_years = serializers.DecimalField(required=False, allow_null=True, max_digits=4, decimal_places=1)
    current_city = serializers.CharField(required=False, allow_blank=True, max_length=50)
    expected_city = serializers.CharField(required=False, allow_blank=True, max_length=50)
    current_company = serializers.CharField(required=False, allow_blank=True, max_length=100)
    current_position = serializers.CharField(required=False, allow_blank=True, max_length=100)
    expected_salary = serializers.DecimalField(required=False, allow_null=True, max_digits=10, decimal_places=2)
    resume_file_url = serializers.URLField(required=False, allow_blank=True, max_length=500)
    resume_text = serializers.CharField(required=False, allow_blank=True)
    id_card_no = serializers.CharField(required=False, allow_blank=True, max_length=20)
    source_channel_id = serializers.CharField(required=False, allow_blank=True)
    referrer_id = serializers.CharField(required=False, allow_blank=True)
    referral_type = serializers.CharField(required=False, allow_blank=True, max_length=16)
    tags = serializers.ListField(child=serializers.CharField(), required=False)
    moka_candidate_id = serializers.CharField(required=False, allow_blank=True, max_length=100)
    extra = serializers.DictField(required=False)

    def validate_phone(self, value):
        try:
            return validate_phone(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))

    def validate_email(self, value):
        if not value:
            return value
        try:
            return validate_email(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))

    def validate_id_card_no(self, value):
        if not value:
            return value
        try:
            return validate_id_card(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))

    def to_data(self) -> CandidateCreateData:
        return CandidateCreateData(
            name=self.validated_data['name'],
            phone=self.validated_data['phone'],
            **{k: v for k, v in self.validated_data.items() if k not in ('name', 'phone')},
        )


class CandidateUpdateSerializer(serializers.ModelSerializer):
    """更新候选人基本信息（不可改手机号/状态）"""
    class Meta:
        model = Candidate
        fields = [
            'email', 'gender', 'age', 'birth_date', 'id_card_no',
            'highest_education', 'work_years',
            'current_city', 'expected_city', 'current_company', 'current_position',
            'expected_salary', 'resume_file_url', 'resume_text',
            'tags', 'extra',
        ]


class CandidateStateTransitionSerializer(serializers.Serializer):
    """候选人状态转换入参"""
    ACTION_CHOICES = [
        ('enter_process', 'enter_process'),
        ('send_offer', 'send_offer'),
        ('mark_onboarded', 'mark_onboarded'),
        ('withdraw', 'withdraw'),
        ('move_to_talent_pool', 'move_to_talent_pool'),
        ('mark_process_failed', 'mark_process_failed'),
        ('pause_process', 'pause_process'),
        ('resume_process', 'resume_process'),
    ]
    action = serializers.ChoiceField(choices=ACTION_CHOICES)
    reason = serializers.CharField(required=False, allow_blank=True)
    offer_id = serializers.CharField(required=False, allow_blank=True)
    onboarding_id = serializers.CharField(required=False, allow_blank=True)
    entry_source = serializers.CharField(required=False, allow_blank=True)
    extra = serializers.DictField(required=False)


class CandidateMergeSerializer(serializers.Serializer):
    """合并候选人"""
    primary_id = serializers.CharField()
    duplicate_ids = serializers.ListField(child=serializers.CharField())


class CandidateImportSerializer(serializers.Serializer):
    """批量导入"""
    candidates = serializers.ListField(child=CandidateCreateSerializer(), allow_empty=False)


class CandidateMokaSyncSerializer(serializers.Serializer):
    """摩卡同步"""
    moka_data = serializers.DictField()
