"""职务管理数据模型。

职务（JobTitle）是组织管理域的基础设置实体, 与字典模块联动:
职位族 / 职位类 / 职位子类三级下拉的数据源为 ``apps.dictionary`` 的字典项
(字典类型码 POSITION_FAMILY / POSITION_CATEGORY / POSITION_SUBCATEGORY,
初始种子见 ``apps/dictionary/seeds.py``), 本模型仅存引用,
外键一律 PROTECT —— 字典项被职务引用时禁止直接删除, 保护历史数据。
"""
from django.db import models

from apps.common.models import FullAuditModel, UUIDModel
from apps.dictionary.models import DictionaryItem


class JobTitle(FullAuditModel, UUIDModel):
    """职务 — 职位族三级分类下的职务定义。"""

    name = models.CharField(max_length=128, unique=True, verbose_name='职务')
    job_family = models.ForeignKey(
        DictionaryItem,
        on_delete=models.PROTECT,
        related_name='job_title_family',
        db_index=True,
        verbose_name='职位族',
    )
    job_category = models.ForeignKey(
        DictionaryItem,
        on_delete=models.PROTECT,
        related_name='job_title_category',
        db_index=True,
        null=True, blank=True,
        verbose_name='职位类',
    )
    job_subcategory = models.ForeignKey(
        DictionaryItem,
        on_delete=models.PROTECT,
        related_name='job_title_subcategory',
        db_index=True,
        null=True, blank=True,
        verbose_name='职位子类',
    )
    is_key_position = models.BooleanField(default=False, verbose_name='关键职务')
    # 职责说明: 富文本编辑, 存原始 HTML 字符串
    responsibility = models.TextField(blank=True, default='', verbose_name='职责说明')
    is_management = models.BooleanField(
        null=True, blank=True, default=False, verbose_name='是否为管理岗',
    )
    # 岗位层级: 本期内置简单层级文本 (初级/中级/高级/专家), P1-4 再做字典化
    job_level_tier = models.CharField(
        max_length=64, null=True, blank=True, verbose_name='岗位层级',
    )
    sort_order = models.IntegerField(default=0, verbose_name='顺序')
    is_enabled = models.BooleanField(default=True, db_index=True, verbose_name='是否启用')

    class Meta:
        verbose_name = '职务'
        verbose_name_plural = '职务'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name

    @property
    def status(self) -> str:
        """启停状态派生值 (ACTIVE/INACTIVE)。

        序列化层只读透出, 使前端直接复用统一 UI 的 status 列渲染与筛选逻辑
        (DB 侧仍以 is_enabled 为唯一真相源)。
        """
        return 'ACTIVE' if self.is_enabled else 'INACTIVE'
