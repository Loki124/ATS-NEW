"""数据字典 — 枚举值 single source of truth。

支持按字典类型（DictionaryType）分组维护字典项（DictionaryItem），
业务模型引用字典项的 key，显示值从字典实时读取。
字典项支持树形结构（parent 自引用），系统预置字典与自定义字典差异化约束。
"""
import re

from django.db import models

from apps.common.models import FullAuditModel, UUIDModel
from apps.dictionary.seed_context import is_seed_active

CODE_PATTERN = re.compile(r'^[A-Za-z0-9_]+$')
DICT_NUMBER_PATTERN = re.compile(r'^D(\d+)$')


class DictionaryType(FullAuditModel, UUIDModel):
    """字典类型 / 分类。"""

    code = models.CharField(max_length=64, unique=True, verbose_name='类型编码')
    name = models.CharField(max_length=128, verbose_name='类型名称')
    english_name = models.CharField(max_length=128, blank=True, default='', verbose_name='英文名称')
    description = models.TextField(blank=True, default='', verbose_name='说明')
    dict_number = models.CharField(max_length=32, blank=True, default='', verbose_name='字典编号')
    is_system = models.BooleanField(default=False, verbose_name='是否系统预置')
    is_enabled = models.BooleanField(default=True, verbose_name='是否启用')

    class Meta:
        verbose_name = '字典类型'
        verbose_name_plural = '字典类型'
        ordering = ['code']

    def __str__(self):
        return f'{self.code} · {self.name}'

    def save(self, *args, **kwargs):
        # 种子注入期间自动标记为系统预置字典
        if is_seed_active():
            self.is_system = True
        # 字典编号自动生成: D + 当前最大序号 + 1（软删行不参与计数）
        if not self.dict_number:
            self.dict_number = self._next_dict_number()
        super().save(*args, **kwargs)

    @staticmethod
    def _next_dict_number():
        max_n = 0
        qs = DictionaryType.objects.filter(
            deleted_at__isnull=True
        ).values_list('dict_number', flat=True)
        for dn in qs:
            if dn and DICT_NUMBER_PATTERN.match(dn):
                n = int(dn[1:])
                if n > max_n:
                    max_n = n
        return f'D{max_n + 1}'


class DictionaryItem(FullAuditModel, UUIDModel):
    """字典项（支持树形结构）。"""

    type = models.ForeignKey(
        DictionaryType,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='所属类型',
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='children',
        verbose_name='父级元素',
    )
    key = models.CharField(max_length=64, verbose_name='项编码')
    value = models.CharField(max_length=128, verbose_name='项名称')
    english_name = models.CharField(max_length=128, blank=True, default='', verbose_name='英文名称')
    description = models.TextField(blank=True, default='', verbose_name='描述')
    sort_order = models.IntegerField(default=0, verbose_name='排序')
    is_active = models.BooleanField(default=True, verbose_name='启用')

    class Meta:
        verbose_name = '字典项'
        verbose_name_plural = '字典项'
        ordering = ['type__code', 'sort_order', 'key']
        unique_together = [('type', 'key')]

    def __str__(self):
        return f'{self.type.code}.{self.key} · {self.value}'
