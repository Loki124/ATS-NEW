"""Django admin for 制度公告 (方便运维兜底, 主维护入口在前端设置页)."""
from django.contrib import admin

from .models import Announcement, AnnouncementConfig


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'audience', 'summary', 'pinned', 'is_active', 'published_at')
    list_filter = ('category', 'audience', 'pinned', 'is_active')
    search_fields = ('title', 'summary', 'body')
    ordering = ('-pinned', '-published_at')


@admin.register(AnnouncementConfig)
class AnnouncementConfigAdmin(admin.ModelAdmin):
    list_display = ('show_on_workbench', 'created_at', 'updated_at')
