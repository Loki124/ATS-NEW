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
