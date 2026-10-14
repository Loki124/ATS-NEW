"""职级管理数据模型。

职级域四个实体:
- ``JobLevelCategory``      职级类别 (职级的分组维度)
- ``JobLevel``              职级 (职等受全局上限约束)
- ``JobLevelGradeSetting``  职等上限 — 全局单例 (固定 id=GLOBAL)
- ``JobLevelSequence``      职级序列开关 — 全局单例 (固定 id=GLOBAL;
                            专业序列系统内置固定、恒开, 故不入表)

单例实现: 两张单例表各以固定 id 播种一行 (见 migration 0001 的 RunPython),
模型 ``save()`` 恒把主键钉死为该固定值, 从 ORM 层面杜绝误建多行。
"""
from django.db import models

from apps.common.models import FullAuditModel, UUIDModel

# 单例行固定主键
SINGLETON_ID = 'GLOBAL'


class JobLevelCategory(FullAuditModel, UUIDModel):
    """职级类别 — 职级的分组维度 (如 专业序列 P / 管理序列 M 的分组)。"""

    name = models.CharField(max_length=128, unique=True, verbose_name='类别名称')
    sort_order = models.IntegerField(default=0, verbose_name='顺序')
    is_enabled = models.BooleanField(default=True, db_index=True, verbose_name='是否启用')

    class Meta:
        verbose_name = '职级类别'
        verbose_name_plural = '职级类别'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name

    @property
    def status(self) -> str:
        """启停状态派生值 (ACTIVE/INACTIVE), 序列化层只读透出。"""
        return 'ACTIVE' if self.is_enabled else 'INACTIVE'


class JobLevel(FullAuditModel, UUIDModel):
    """职级 — 职等取值受 ``JobLevelGradeSetting.max_grade`` 约束 (1-999)。"""

    name = models.CharField(max_length=128, unique=True, verbose_name='职级名称')
    category = models.ForeignKey(
        JobLevelCategory,
        on_delete=models.PROTECT,
        related_name='job_levels',
        db_index=True,
        verbose_name='类别',
    )
    grade = models.IntegerField(default=1, verbose_name='职等')
    sort_order = models.IntegerField(default=0, verbose_name='顺序')
    remark = models.TextField(blank=True, default='', verbose_name='备注')
    is_enabled = models.BooleanField(default=True, db_index=True, verbose_name='是否启用')

    class Meta:
        verbose_name = '职级'
        verbose_name_plural = '职级'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name

    @property
    def status(self) -> str:
        """启停状态派生值 (ACTIVE/INACTIVE), 序列化层只读透出。"""
        return 'ACTIVE' if self.is_enabled else 'INACTIVE'


class JobLevelGradeSetting(FullAuditModel, UUIDModel):
    """职等上限 — 全局单例配置 (固定 id=GLOBAL)。

    新建/编辑职级时, 职等 (grade) 取值上限即本行 ``max_grade`` (1-999)。
    """

    max_grade = models.IntegerField(default=40, verbose_name='职等上限')

    class Meta:
        verbose_name = '职等上限设置'
        verbose_name_plural = '职等上限设置'

    def __str__(self):
        return f'职等上限({self.max_grade})'

    def save(self, *args, **kwargs):
        # 单例行: 主键恒为固定值, 防止误建多行
        self.id = SINGLETON_ID
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls) -> 'JobLevelGradeSetting':
        """取全局唯一行; 不存在则按默认值惰性创建 (migration 已播种, 双保险)。"""
        obj, _ = cls.objects.get_or_create(id=SINGLETON_ID)
        return obj


class JobLevelSequence(FullAuditModel, UUIDModel):
    """职级序列开关 — 全局单例配置 (固定 id=GLOBAL)。

    专业序列为系统内置、恒开, 不建模; 本表仅持久化管理序列开关
    (``management_enabled``), 供职级序列管理弹窗读写。
    """

    management_enabled = models.BooleanField(default=False, verbose_name='管理序列开关')

    class Meta:
        verbose_name = '职级序列设置'
        verbose_name_plural = '职级序列设置'

    def __str__(self):
        return f'管理序列({"开" if self.management_enabled else "关"})'

    def save(self, *args, **kwargs):
        # 单例行: 主键恒为固定值, 防止误建多行
        self.id = SINGLETON_ID
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls) -> 'JobLevelSequence':
        """取全局唯一行; 不存在则按默认值惰性创建 (migration 已播种, 双保险)。"""
        obj, _ = cls.objects.get_or_create(id=SINGLETON_ID)
        return obj
