"""通用模型基类"""
from django.db import models


class SoftDeleteManager(models.Manager):
    """默认只返回未软删记录；用 all_objects 取全部（含已删）。"""

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class TimestampedModel(models.Model):
    """带时间戳的抽象基类"""
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """软删除抽象基类"""
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name='删除时间')

    class Meta:
        abstract = True

    def _soft_delete_update_fields(self):
        """仅更新真实存在的字段 — 裸 SoftDeleteModel 子类可能没有 updated_at。"""
        fields = ['deleted_at']
        if 'updated_at' in [f.name for f in self._meta.get_fields()]:
            fields.append('updated_at')
        return fields

    def soft_delete(self):
        from django.utils import timezone
        self.deleted_at = timezone.now()
        self.save(update_fields=self._soft_delete_update_fields())

    def restore(self):
        self.deleted_at = None
        self.save(update_fields=self._soft_delete_update_fields())


class FullAuditModel(TimestampedModel, SoftDeleteModel):
    """完整审计模型（时间戳 + 软删除 + 创建人/最后修改人）"""
    created_by = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='+',
        verbose_name='创建人',
    )
    updated_by = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='+',
        verbose_name='最后修改人',
    )

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    """UUID 主键抽象基类"""
    id = models.CharField(max_length=32, primary_key=True, editable=False)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.id:
            from nanoid import generate as nanoid_generate
            self.id = nanoid_generate(size=21)
        super().save(*args, **kwargs)
