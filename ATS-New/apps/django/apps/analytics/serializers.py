"""Analytics Serializers (PRD v4 §14.9 数据中心)"""
from rest_framework import serializers

from .models import ExportTask, ReportSnapshot


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
