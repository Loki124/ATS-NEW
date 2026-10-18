"""邮箱验证码 Admin (仅供后台排查)."""
from django.contrib import admin

from .models import EmailVerificationCode


@admin.register(EmailVerificationCode)
class EmailVerificationCodeAdmin(admin.ModelAdmin):
    list_display = ('email', 'purpose', 'status', 'expires_at', 'attempts', 'created_at')
    list_filter = ('status', 'purpose')
    search_fields = ('email',)
    readonly_fields = ('code_hash',)
