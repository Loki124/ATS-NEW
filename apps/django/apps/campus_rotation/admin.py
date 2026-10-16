"""campus_rotation 后台管理（轻量，便于运营录入）。"""
from django.contrib import admin

from .models import ClassRoom, LiveRoom, RotationArrangement


@admin.register(LiveRoom)
class LiveRoomAdmin(admin.ModelAdmin):
    list_display = ('room_no', 'name', 'department', 'bu', 'platform', 'is_active')
    list_filter = ('is_active', 'platform')
    search_fields = ('room_no', 'name')


@admin.register(ClassRoom)
class ClassRoomAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'head_teacher', 'batch')
    search_fields = ('code', 'name')


@admin.register(RotationArrangement)
class RotationArrangementAdmin(admin.ModelAdmin):
    list_display = ('id', 'person_id', 'stage', 'current_dept', 'mentor', 'head_teacher')
    list_filter = ('stage',)
    search_fields = ('person_id', 'note')
