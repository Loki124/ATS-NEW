"""campus_rotation 后台管理（轻量，便于运营录入）。"""
from django.contrib import admin

from .models import ClassRoom, RotationArrangement, RotationResource


@admin.register(RotationResource)
class RotationResourceAdmin(admin.ModelAdmin):
    """轮岗资源（2026-10-22 直播间 + 客服部门整合后的统一台账）。"""

    list_display = ('resource_no', 'name', 'resource_type', 'department', 'bu', 'platform', 'is_active')
    list_filter = ('is_active', 'resource_type', 'platform')
    search_fields = ('resource_no', 'name')


@admin.register(ClassRoom)
class ClassRoomAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'head_teacher', 'batch')
    search_fields = ('code', 'name')


@admin.register(RotationArrangement)
class RotationArrangementAdmin(admin.ModelAdmin):
    list_display = ('id', 'person_id', 'stage', 'current_dept', 'mentor', 'head_teacher')
    list_filter = ('stage',)
    search_fields = ('person_id', 'note')
