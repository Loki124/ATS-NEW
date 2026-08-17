"""数据字典 — 枚举值 single source of truth。

支持按字典类型（DictionaryType）分组维护字典项（DictionaryItem），
业务模型引用字典项的 key，显示值从字典实时读取。
"""
from django.db import models

from apps.common.models import FullAuditModel, UUIDModel


class DictionaryType(FullAuditModel, UUIDModel):
    """字典类型 / 分类。"""

    code = models.CharField(max_length=64, unique=True, verbose_name='类型编码')
    name = models.CharField(max_length=128, verbose_name='类型名称')
    description = models.TextField(blank=True, default='', verbose_name='说明')

    class Meta:
        verbose_name = '字典类型'
        verbose_name_plural = '字典类型'
        ordering = ['code']

    def __str__(self):
        return f'{self.code} · {self.name}'


class DictionaryItem(FullAuditModel, UUIDModel):
    """字典项。"""

    type = models.ForeignKey(
        DictionaryType,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='所属类型',
    )
    key = models.CharField(max_length=64, verbose_name='项编码')
    value = models.CharField(max_length=128, verbose_name='项名称')
    sort_order = models.IntegerField(default=0, verbose_name='排序')
    is_active = models.BooleanField(default=True, verbose_name='启用')

    class Meta:
        verbose_name = '字典项'
        verbose_name_plural = '字典项'
        ordering = ['type__code', 'sort_order', 'key']
        unique_together = [('type', 'key')]

    def __str__(self):
        return f'{self.type.code}.{self.key} · {self.value}'
