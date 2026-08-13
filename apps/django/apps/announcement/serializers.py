"""制度公告序列化器。"""
from rest_framework import serializers

from .models import Announcement, AnnouncementAttachment, AnnouncementConfig


class AnnouncementAttachmentSerializer(serializers.ModelSerializer):
    """附件只读展示；file_url 为可下载的绝对地址。"""

    file_url = serializers.SerializerMethodField()

    class Meta:
        model = AnnouncementAttachment
        fields = ['id', 'original_name', 'file_size', 'content_type', 'file_url', 'created_at']
        read_only_fields = fields

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file:
            try:
                url = obj.file.url
                return request.build_absolute_uri(url) if request else url
            except Exception:
                return ''
        return ''


class AnnouncementSerializer(serializers.ModelSerializer):
    """读 / 写共用展示字段；写时仅暴露可编辑字段。"""

    category_display = serializers.CharField(source='get_category_display', read_only=True)
    audience_display = serializers.CharField(source='get_audience_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True, default='')
    updated_by_name = serializers.CharField(source='updated_by.username', read_only=True, default='')
    attachments = AnnouncementAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Announcement
        fields = [
            'id', 'title', 'category', 'category_display',
            'audience', 'audience_display',
            'summary', 'body', 'pinned', 'published_at', 'is_active',
            'created_by', 'created_by_name', 'updated_by', 'updated_by_name',
            'attachments',
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
        fields = ['title', 'category', 'audience', 'summary', 'body', 'pinned', 'published_at', 'is_active']

    def validate_title(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('标题不能为空')
        return value.strip()

    def validate_body(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('正文不能为空')
        return value


class AnnouncementConfigSerializer(serializers.ModelSerializer):
    """模块级配置（工作台展示开关）。"""

    class Meta:
        model = AnnouncementConfig
        fields = ['show_on_workbench']
