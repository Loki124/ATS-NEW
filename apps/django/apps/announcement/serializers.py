"""制度公告序列化器。"""
from rest_framework import serializers

from apps.notification.models import NotificationLog

from .models import Announcement, AnnouncementAttachment, AnnouncementConfig, AnnouncementPushRecord


class AnnouncementAttachmentSerializer(serializers.ModelSerializer):
    """附件只读展示；file_url 为可下载的绝对地址。"""

    file_url = serializers.SerializerMethodField()

    class Meta:
        model = AnnouncementAttachment
        fields = ['id', 'original_name', 'file_size', 'content_type', 'file_url', 'created_at']
        read_only_fields = fields

    def get_file_url(self, obj):
        if obj.file:
            try:
                return obj.file.url
            except Exception:
                return ''
        return ''


class AnnouncementPushRecordSerializer(serializers.ModelSerializer):
    """推送记录序列化器 — 含已读/未读统计与推送人信息。"""

    pushed_by_name = serializers.CharField(source='pushed_by.username', read_only=True, default='')
    read_count = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    is_history = serializers.SerializerMethodField()

    class Meta:
        model = AnnouncementPushRecord
        fields = [
            'id', 'channel', 'total_count', 'context',
            'pushed_by', 'pushed_by_name',
            'read_count', 'unread_count', 'is_history',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_read_count(self, obj: AnnouncementPushRecord) -> int:
        ids = obj.log_ids
        if not ids:
            return 0
        return NotificationLog.objects.filter(
            id__in=ids, read_at__isnull=False, deleted_at__isnull=True,
        ).count()

    def get_unread_count(self, obj: AnnouncementPushRecord) -> int:
        ids = obj.log_ids
        if not ids:
            return 0
        return NotificationLog.objects.filter(
            id__in=ids, read_at__isnull=True, deleted_at__isnull=True,
        ).count()

    def get_is_history(self, obj: AnnouncementPushRecord) -> bool:
        """超过 24 小时或非最新一条的推送标记为「历史推送」。"""
        from django.utils import timezone
        return (timezone.now() - obj.created_at).total_seconds() > 24 * 3600


class AnnouncementSerializer(serializers.ModelSerializer):
    """读 / 写共用展示字段；写时仅暴露可编辑字段。"""

    category_display = serializers.CharField(source='get_category_display', read_only=True)
    audience_display = serializers.CharField(source='get_audience_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True, default='')
    updated_by_name = serializers.CharField(source='updated_by.username', read_only=True, default='')
    attachments = AnnouncementAttachmentSerializer(many=True, read_only=True)
    push_records = AnnouncementPushRecordSerializer(many=True, read_only=True)

    class Meta:
        model = Announcement
        fields = [
            'id', 'title', 'category', 'category_display',
            'audience', 'audience_display',
            'summary', 'body', 'pinned', 'published_at', 'is_active',
            'show_on_workbench', 'show_in_more',
            'created_by', 'created_by_name', 'updated_by', 'updated_by_name',
            'attachments', 'push_records',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'updated_by']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 列表/详情只读场景仅暴露可读字段；写场景（由视图 get_serializer_class
        # 切换为 AnnouncementWriteSerializer）才放开编辑字段。
        if self.context.get('write_mode'):
            for _f in ('title', 'category', 'audience', 'summary', 'body', 'pinned', 'published_at', 'is_active'):
                self.fields[_f].required = False


class AnnouncementWriteSerializer(serializers.ModelSerializer):
    """创建 / 更新专用：仅可编辑字段。"""

    class Meta:
        model = Announcement
        fields = [
            'title', 'category', 'audience', 'summary', 'body',
            'pinned', 'published_at', 'is_active',
            'show_on_workbench', 'show_in_more',
        ]
        # 展示位置开关有模型默认值，创建/部分更新时均非必填
        extra_kwargs = {
            'show_on_workbench': {'required': False},
            'show_in_more': {'required': False},
        }

    def validate_title(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('标题不能为空')
        return value.strip()

    def validate_body(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('正文不能为空')
        return value

    def save(self, **kwargs):
        # 业务规则：已发布的公告都要在「更多」中展示；未发布则不在更多展示。
        if self.instance is None:
            is_active = self.validated_data.get('is_active', True)
        else:
            is_active = self.validated_data.get('is_active', self.instance.is_active)
        self.validated_data['show_in_more'] = bool(is_active)
        return super().save(**kwargs)


class AnnouncementConfigSerializer(serializers.ModelSerializer):
    """模块级配置（工作台模块总开关）。"""

    class Meta:
        model = AnnouncementConfig
        fields = ['show_on_workbench']
