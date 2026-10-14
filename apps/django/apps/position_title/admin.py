"""职务管理 Admin 注册。"""
from django.contrib import admin

from .models import JobTitle


@admin.register(JobTitle)
class JobTitleAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'job_family', 'job_category', 'is_key_position',
        'is_management', 'sort_order', 'is_enabled', 'created_at',
    )
    search_fields = ('name',)
    list_filter = ('is_key_position', 'is_management', 'is_enabled')
    raw_id_fields = ('job_family', 'job_category', 'job_subcategory')
