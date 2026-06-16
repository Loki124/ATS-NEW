"""Position Serializers (PRD v4 §14.2)"""
from rest_framework import serializers

from .models import Position


class PositionListSerializer(serializers.ModelSerializer):
    """职位列表 - 精简字段"""
    department_name = serializers.CharField(source='department.name', read_only=True, default='')
    hiring_manager_name = serializers.CharField(source='hiring_manager.username', read_only=True, default='')
    owner_name = serializers.CharField(source='owner.username', read_only=True, default='')
    state_display = serializers.CharField(source='get_state_display', read_only=True)
    headcount_remaining = serializers.SerializerMethodField()
    application_count = serializers.SerializerMethodField()

    class Meta:
        model = Position
        fields = [
            'id', 'code', 'title', 'department', 'department_name',
            'hiring_manager', 'hiring_manager_name',
            'owner', 'owner_name', 'level', 'location',
            'salary_min', 'salary_max', 'headcount', 'filled_count',
            'headcount_remaining', 'application_count',
            'state', 'state_display', 'process', 'process_version',
            'published_at', 'closed_at', 'created_at',
        ]

    def get_headcount_remaining(self, obj) -> int:
        return max(0, obj.headcount - obj.filled_count)

    def get_application_count(self, obj) -> int:
        return obj.applications.filter(deleted_at__isnull=True).count()


class PositionDetailSerializer(serializers.ModelSerializer):
    """职位详情"""
    department_name = serializers.CharField(source='department.name', read_only=True, default='')
    hiring_manager_name = serializers.CharField(source='hiring_manager.username', read_only=True, default='')
    owner_name = serializers.CharField(source='owner.username', read_only=True, default='')
    assistants_names = serializers.SerializerMethodField()
    state_display = serializers.CharField(source='get_state_display', read_only=True)
    process_name = serializers.CharField(source='process.name', read_only=True, default='')

    class Meta:
        model = Position
        fields = [
            'id', 'code', 'title', 'description', 'requirements',
            'department', 'department_name',
            'hiring_manager', 'hiring_manager_name',
            'owner', 'owner_name',
            'assistants', 'assistants_names',
            'level', 'position_title', 'location',
            'salary_min', 'salary_max', 'headcount', 'filled_count',
            'state', 'state_display',
            'process', 'process_name', 'process_version',
            'published_at', 'closed_at', 'created_at', 'updated_at',
        ]
        read_only_fields = ['code', 'state', 'published_at', 'closed_at', 'created_at', 'updated_at']

    def get_assistants_names(self, obj):
        return [u.username for u in obj.assistants.all()]


class PositionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = [
            'title', 'description', 'requirements',
            'department', 'hiring_manager', 'owner', 'assistants',
            'level', 'position_title', 'location',
            'salary_min', 'salary_max', 'headcount',
            'process',
        ]


class PositionTransitionSerializer(serializers.Serializer):
    """职位状态转换"""
    ACTION_CHOICES = [
        ('submit_publish', 'submit_publish'),
        ('publish', 'publish'),
        ('start_recruiting', 'start_recruiting'),
        ('pause', 'pause'),
        ('resume', 'resume'),
        ('close', 'close'),
    ]
    action = serializers.ChoiceField(choices=ACTION_CHOICES)
    reason = serializers.CharField(required=False, allow_blank=True)
