"""Field ACL Models (PRD v4 §4.4)"""
from django.db import models
from apps.common.models import TimestampedModel
from nanoid import generate as nanoid_generate


def gen_id():
    return nanoid_generate(size=21)


class FieldPermission(models.TextChoices):
    READ = 'READ', '可读'
    MASK = 'MASK', '脱敏可见'
    NONE = 'NONE', '不可见'


class FieldACL(TimestampedModel):
    """字段级 ACL 配置"""
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    entity = models.CharField(max_length=64, db_index=True, verbose_name='实体名', help_text='如 candidate / offer')
    field = models.CharField(max_length=64, db_index=True, verbose_name='字段名', help_text='如 phone / salary')
    role_code = models.CharField(max_length=50, db_index=True, verbose_name='角色编码')

    permission = models.CharField(max_length=8, choices=FieldPermission.choices, verbose_name='权限')

    class Meta:
        db_table = 'field_acls'
        verbose_name = '字段级 ACL'
        verbose_name_plural = verbose_name
        unique_together = [('entity', 'field', 'role_code')]

    def __str__(self):
        return f'ACL[{self.entity}.{self.field}] {self.role_code}={self.permission}'


class FieldAclAccessLog(TimestampedModel):
    """字段级 ACL 访问审计日志 (合规审计 / 泄露溯源)。

    记录「谁 / 何时 / 通过哪个接口 / 访问了哪个实体的哪些敏感字段，
    其中哪些被脱敏(MASK)、哪些被隐藏(NONE)」。由 FieldAclSerializerMixin
    在 HTTP 序列化时按 (request, entity) 去重埋点写入。追加写、不可软删。
    """

    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    entity = models.CharField(max_length=64, db_index=True, verbose_name='实体名')
    user_id = models.CharField(max_length=64, db_index=True, blank=True, default='', verbose_name='用户ID')
    username = models.CharField(max_length=128, blank=True, default='', verbose_name='用户名')
    role_codes = models.JSONField(default=list, verbose_name='访问时角色')
    masked_fields = models.JSONField(default=list, verbose_name='脱敏字段')
    hidden_fields = models.JSONField(default=list, verbose_name='隐藏字段')
    request_path = models.CharField(max_length=255, blank=True, default='', verbose_name='请求路径')
    client_ip = models.CharField(max_length=64, blank=True, default='', verbose_name='客户端IP')

    class Meta:
        db_table = 'field_acl_access_logs'
        verbose_name = '字段级访问审计'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'FieldAclAccessLog[{self.entity}] user={self.user_id} masked={self.masked_fields}'
