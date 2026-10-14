"""职级管理序列化器。"""
from rest_framework import serializers

from .models import (
    JobLevel,
    JobLevelCategory,
    JobLevelGradeSetting,
    JobLevelSequence,
)

# 职等合法区间 (与前端职等输入框提示一致)
GRADE_MIN = 1
GRADE_MAX = 999

# 写入的类别 id 仅允许取未软删的类别, 防止引用已删除数据
_LIVE_CATEGORIES = JobLevelCategory.objects.filter(deleted_at__isnull=True)


def _display_name(user) -> str:
    """审计人展示名, 无创建人/修改人时返空串。"""
    return user.full_name if user else ''


class JobLevelCategorySerializer(serializers.ModelSerializer):
    """职级类别 — 含 ``job_level_count`` (该类下启用职级数, 供"包含 N 个职级"展示)。"""

    status = serializers.SerializerMethodField()
    job_level_count = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = JobLevelCategory
        fields = [
            'id', 'name', 'sort_order', 'is_enabled', 'status', 'job_level_count',
            'created_by_name', 'created_at', 'updated_by_name', 'updated_at',
        ]
        read_only_fields = [
            'id', 'status', 'job_level_count',
            'created_by_name', 'created_at', 'updated_by_name', 'updated_at',
        ]

    def validate_name(self, value: str) -> str:
        """类别名称非空 (去掉纯空白)。"""
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError('类别名称不能为空')
        return value

    def validate(self, attrs: dict) -> dict:
        """类别名称全局唯一 (含软删占位行), DB unique 约束双重兜底。"""
        attrs = super().validate(attrs)
        name = attrs.get('name') or getattr(self.instance, 'name', None)
        if not name:
            return attrs
        qs = JobLevelCategory.objects.filter(name=name)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError({'name': ['该类别名称已存在']})
        return attrs

    def get_status(self, obj) -> str:
        return obj.status

    def get_job_level_count(self, obj) -> int:
        return JobLevel.objects.filter(
            category=obj, is_enabled=True, deleted_at__isnull=True,
        ).count()

    def get_created_by_name(self, obj) -> str:
        return _display_name(getattr(obj, 'created_by', None))

    def get_updated_by_name(self, obj) -> str:
        return _display_name(getattr(obj, 'updated_by', None))


class JobLevelSerializer(serializers.ModelSerializer):
    """职级 — 类别写入收 ``JobLevelCategory`` id, 输出附带类别展示名。"""

    category = serializers.PrimaryKeyRelatedField(
        queryset=_LIVE_CATEGORIES, label='类别',
    )
    category_name = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = JobLevel
        fields = [
            'id', 'name', 'category', 'category_name', 'grade',
            'sort_order', 'remark', 'is_enabled', 'status',
            'created_by_name', 'created_at', 'updated_by_name', 'updated_at',
        ]
        read_only_fields = [
            'id', 'status', 'category_name',
            'created_by_name', 'created_at', 'updated_by_name', 'updated_at',
        ]

    def validate_name(self, value: str) -> str:
        """职级名称非空 (去掉纯空白)。"""
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError('职级名称不能为空')
        return value

    def validate_grade(self, value):
        """职等必须落在 [1, 999], 且不超过全局职等上限。"""
        if value is None:
            return value
        if not (GRADE_MIN <= value <= GRADE_MAX):
            raise serializers.ValidationError(f'职等必须在 {GRADE_MIN}-{GRADE_MAX} 之间')
        max_grade = JobLevelGradeSetting.get_solo().max_grade
        if value > max_grade:
            raise serializers.ValidationError(f'职等不能超过职等上限（当前上限 {max_grade}）')
        return value

    def validate(self, attrs: dict) -> dict:
        """职级名称全局唯一 (含软删占位行), DB unique 约束双重兜底。"""
        attrs = super().validate(attrs)
        name = attrs.get('name') or getattr(self.instance, 'name', None)
        if not name:
            return attrs
        qs = JobLevel.objects.filter(name=name)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError({'name': ['该职级名称已存在']})
        return attrs

    def get_category_name(self, obj) -> str:
        return obj.category.name if obj.category_id else ''

    def get_status(self, obj) -> str:
        return obj.status

    def get_created_by_name(self, obj) -> str:
        return _display_name(getattr(obj, 'created_by', None))

    def get_updated_by_name(self, obj) -> str:
        return _display_name(getattr(obj, 'updated_by', None))


class JobLevelGradeSettingSerializer(serializers.ModelSerializer):
    """职等上限单例 — ``GET/PUT /job-level-grade-settings/current/`` 读写。"""

    updated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = JobLevelGradeSetting
        fields = ['id', 'max_grade', 'updated_by_name', 'updated_at']
        read_only_fields = ['id', 'updated_by_name', 'updated_at']

    def validate_max_grade(self, value):
        """职等上限必须落在 [1, 999]。"""
        if not (GRADE_MIN <= value <= GRADE_MAX):
            raise serializers.ValidationError(f'职等上限必须在 {GRADE_MIN}-{GRADE_MAX} 之间')
        return value

    def get_updated_by_name(self, obj) -> str:
        return _display_name(getattr(obj, 'updated_by', None))


class JobLevelSequenceSerializer(serializers.ModelSerializer):
    """职级序列开关单例 — ``GET/PUT /job-level-sequences/current/`` 读写。"""

    updated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = JobLevelSequence
        fields = ['id', 'management_enabled', 'updated_by_name', 'updated_at']
        read_only_fields = ['id', 'updated_by_name', 'updated_at']

    def get_updated_by_name(self, obj) -> str:
        return _display_name(getattr(obj, 'updated_by', None))
