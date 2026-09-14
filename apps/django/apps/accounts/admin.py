"""注册审核 Admin (仅供后台排查, 审核操作走 API + 前端审核台)."""
from django.contrib import admin

from .models import EmailVerificationCode, RegistrationApplication


@admin.register(EmailVerificationCode)
class EmailVerificationCodeAdmin(admin.ModelAdmin):
    list_display = ('email', 'purpose', 'status', 'expires_at', 'attempts', 'created_at')
    list_filter = ('status', 'purpose')
    search_fields = ('email',)
    readonly_fields = ('code_hash',)


@admin.register(RegistrationApplication)
class RegistrationApplicationAdmin(admin.ModelAdmin):
    list_display = ('email', 'full_name', 'status', 'email_verified', 'reviewed_by', 'created_at')
    list_filter = ('status', 'email_verified')
    search_fields = ('email', 'full_name')
    readonly_fields = ('user',)
