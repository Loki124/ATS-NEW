"""Audit Models (PRD v4 §4.4, §13)"""
from django.db import models
from apps.common.models import TimestampedModel
from nanoid import generate as nanoid_generate


def gen_id():
    return nanoid_generate(size=21)


class AuditLog(TimestampedModel):
    """审计日志 - 记录所有写操作 + 敏感字段访问"""
    class ActionType(models.TextChoices):
        CREATE = 'CREATE', '创建'
        UPDATE = 'UPDATE', '更新'
        DELETE = 'DELETE', '删除'
        READ = 'READ', '读取（敏感字段）'
        EXPORT = 'EXPORT', '导出'
        LOGIN = 'LOGIN', '登录'
        LOGOUT = 'LOGOUT', '登出'
        PERMISSION_DENIED = 'PERMISSION_DENIED', '权限拒绝'

    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    user = models.ForeignKey(
        'core.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+', verbose_name='操作人',
    )

    action = models.CharField(max_length=20, choices=ActionType.choices, db_index=True, verbose_name='操作类型')
    entity = models.CharField(max_length=64, db_index=True, verbose_name='实体名')
    entity_id = models.CharField(max_length=32, null=True, blank=True, db_index=True, verbose_name='实体ID')
    field = models.CharField(max_length=64, blank=True, db_index=True, verbose_name='字段名')

    old_value = models.TextField(blank=True, verbose_name='旧值')
    new_value = models.TextField(blank=True, verbose_name='新值')

    ip = models.GenericIPAddressField(null=True, blank=True, db_index=True, verbose_name='IP')
    user_agent = models.TextField(blank=True, verbose_name='User Agent')
    request_id = models.CharField(max_length=32, blank=True, verbose_name='Request ID')

    class Meta:
        db_table = 'audit_logs'
        verbose_name = '审计日志'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['entity', 'entity_id', 'created_at']),
            models.Index(fields=['action', 'created_at']),
        ]

    def __str__(self):
        return f'Audit[{self.user_id if self.user_id else "anon"}] {self.action} {self.entity}'
