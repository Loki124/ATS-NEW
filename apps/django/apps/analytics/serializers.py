"""Analytics Serializers (PRD v4 §14.9 数据中心)"""
from rest_framework import serializers

from .models import ExportTask, ReportSnapshot
from .models_data import DataSubscription


class DataSubscriptionSerializer(serializers.ModelSerializer):
    """字段对齐 FE api/data.ts:DataSubscription interface.

    用 snake_case 字段名, 由 camel-case 渲染器自动转驼峰输出 (userId/scheduleTime/...),
    入参由 camel-case 解析器转回 snake_case, 避免 camelCase source 字段导致的解析错位.
    """
    class Meta:
        model = DataSubscription
        fields = [
            'id', 'name', 'user_id', 'user_name', 'resource', 'metric',
            'filters', 'channel', 'schedule', 'schedule_time', 'recipients',
            'is_active', 'last_run_at', 'next_run_at', 'run_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'last_run_at', 'next_run_at', 'run_count', 'created_at', 'updated_at']


class ReportSnapshotSerializer(serializers.ModelSerializer):
    report_type_display = serializers.CharField(source='get_report_type_display', read_only=True)
    generated_by_name = serializers.CharField(source='generated_by.username', read_only=True, default='')

    class Meta:
        model = ReportSnapshot
        fields = [
            'id', 'name', 'report_type', 'report_type_display',
            'scope', 'data', 'generated_at', 'generated_by', 'generated_by_name',
            'created_at',
        ]
        read_only_fields = ['id', 'generated_at', 'created_at']


class ExportTaskSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    format_display = serializers.CharField(source='get_format_display', read_only=True)
    requested_by_name = serializers.CharField(source='requested_by.username', read_only=True, default='')

    class Meta:
        model = ExportTask
        fields = [
            'id', 'name', 'entity', 'filters', 'fields',
            'format', 'format_display',
            'status', 'status_display',
            'file_url', 'file_size', 'row_count',
            'requested_by', 'requested_by_name',
            'started_at', 'completed_at', 'error_message',
            'created_at',
        ]
        read_only_fields = [
            'id', 'status', 'file_url', 'file_size', 'row_count',
            'started_at', 'completed_at', 'error_message', 'created_at',
        ]


class ExportTaskCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExportTask
        fields = ['name', 'entity', 'filters', 'fields', 'format']
