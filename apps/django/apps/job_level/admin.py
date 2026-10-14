"""职级管理 Admin 注册。"""
from django.contrib import admin

from .models import (
    JobLevel,
    JobLevelCategory,
    JobLevelGradeSetting,
    JobLevelSequence,
)


@admin.register(JobLevelCategory)
class JobLevelCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'sort_order', 'is_enabled', 'created_at')
    search_fields = ('name',)
    list_filter = ('is_enabled',)


@admin.register(JobLevel)
class JobLevelAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'grade', 'sort_order', 'is_enabled', 'created_at')
    search_fields = ('name',)
    list_filter = ('is_enabled', 'category')
    raw_id_fields = ('category',)


@admin.register(JobLevelGradeSetting)
class JobLevelGradeSettingAdmin(admin.ModelAdmin):
    list_display = ('id', 'max_grade', 'updated_at')

    def has_add_permission(self, request):
        # 单例行: 仅允许编辑, 不允许再新增
        return not JobLevelGradeSetting.objects.exists()


@admin.register(JobLevelSequence)
class JobLevelSequenceAdmin(admin.ModelAdmin):
    list_display = ('id', 'management_enabled', 'updated_at')

    def has_add_permission(self, request):
        # 单例行: 仅允许编辑, 不允许再新增
        return not JobLevelSequence.objects.exists()
