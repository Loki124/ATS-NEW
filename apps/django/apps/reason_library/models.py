"""Reason Library 数据模型 (T01).

5 张表 + 2 个枚举 (SceneOption / TagType):
1. ReasonTag                — 全局标签池 (软删, SoftDeleteManager)
2. SceneRule                — 场景规则 (system / custom)
3. RuleCategory             — 规则分类 (树形, level 1..4)
4. CategoryAssignment       — 分类 ↔ 标签 多对多 (UNIQUE)
5. RuleSceneAssignment      — 场景 → 规则 (UNIQUE(scene), Q6)

约束 (架构师方案):
- reason_tag.name           UNIQUE (含软删, Q-A4)
- idx(reason_tag.type, reason_tag.enabled)
- CHECK (rule_category.level BETWEEN 1 AND 4)
- UNIQUE (category_assignment.category_id, tag_id)
- UNIQUE (rule_scene_assignment.scene)
"""
from __future__ import annotations

from enum import Enum

from django.conf import settings
from django.db import models
from django.db.models import CheckConstraint, Q, UniqueConstraint

from .managers import ReasonTagManager, SceneRuleManager


class TagType(str, Enum):
    """标签类型枚举 - DB 存枚举 value (str)。"""
    SYSTEM = 'system'
    CUSTOM = 'custom'

    @classmethod
    def choices(cls):
        return [(m.value, m.value) for m in cls]


class SceneOption(str, Enum):
    """6 大业务场景选项 - 与前端 SCENE_OPTIONS 完全对齐。"""
    SCREEN_FAIL = '筛选不通过'
    CANCEL_INTERVIEW = '取消面试'
    ADD_TALENT_POOL = '放入人才库'
    ELIMINATE = '淘汰'
    MARK_FAILED = '标记失败'
    INVITE_TAG = '邀约标注'


SCENE_OPTIONS = [s.value for s in SceneOption]

# 全场景统一: 单次选择标签上限 (Q-A1)
MAX_PICK = 5

# 分类层级上限 (前端常量 MAX_CATEGORY_LEVEL = 4 同步)
MAX_CATEGORY_LEVEL = 4


class ReasonTag(models.Model):
    """原因标签 - 全局池, 软删。"""

    id = models.CharField(max_length=32, primary_key=True, editable=False)
    name = models.CharField(max_length=32, unique=True, verbose_name='标签名')
    code = models.CharField(
        max_length=24, unique=True, editable=False,
        verbose_name='原因代码', help_text='系统自动生成, 供开发在代码中引用 (如 R4fKq2xB9zW3)',
    )
    en_name = models.CharField(max_length=64, blank=True, default='', verbose_name='英文名')
    tip = models.CharField(max_length=128, blank=True, default='', verbose_name='提示文案')
    type = models.CharField(
        max_length=16, choices=TagType.choices(), default=TagType.CUSTOM.value,
        verbose_name='类型',
    )
    enabled = models.BooleanField(default=True, verbose_name='启用')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name='创建人',
    )
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name='删除时间')

    objects = ReasonTagManager()

    class Meta:
        db_table = 'reason_tag'
        verbose_name = '原因标签'
        verbose_name_plural = '原因标签'
        ordering = ['type', 'name']
        indexes = [
            models.Index(fields=['type', 'enabled'], name='idx_rtag_type_enabled'),
        ]
        # Q-A4: name UNIQUE 含软删记录 (不复用) — DB 层 UNIQUE(name) 即满足

    def __str__(self) -> str:
        return f'[{self.type}] {self.name}'

    def save(self, *args, **kwargs):
        if not self.id:
            from nanoid import generate as nanoid_generate
            self.id = nanoid_generate(size=21)
        if not self.code:
            from nanoid import generate as nanoid_generate
            self.code = 'R' + nanoid_generate('0123456789abcdefghijklmnopqrstuvwxyz', size=11)
        super().save(*args, **kwargs)

    def soft_delete(self):
        from django.utils import timezone
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at', 'updated_at'])

    @property
    def ref_count(self) -> int:
        """被 CategoryAssignment 引用的次数 (T03 详情使用)。"""
        return CategoryAssignment.objects.filter(tag=self).count()


class SceneRule(models.Model):
    """场景规则 - 头部。is_system=True 仅超管可改 (Q1/Q2)。"""

    id = models.CharField(max_length=32, primary_key=True, editable=False)
    name = models.CharField(max_length=64, verbose_name='规则名')
    is_system = models.BooleanField(default=False, db_index=True, verbose_name='系统预置')
    enabled = models.BooleanField(default=True, db_index=True, verbose_name='启用')
    description = models.CharField(max_length=200, blank=True, default='', verbose_name='描述')
    max_selectable_tags = models.PositiveSmallIntegerField(
        default=5, verbose_name='可选标签上限',
        help_text='用户在实际使用弹窗中最多可选的原因标签条数 (0 表示不限制)',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    objects = SceneRuleManager()

    class Meta:
        db_table = 'scene_rule'
        verbose_name = '场景规则'
        verbose_name_plural = '场景规则'
        ordering = ['-is_system', '-updated_at']

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.id:
            from nanoid import generate as nanoid_generate
            self.id = nanoid_generate(size=21)
        super().save(*args, **kwargs)

    @property
    def assigned_scenes(self) -> list:
        """当前规则引用的所有场景字符串。"""
        return list(self.scene_assignments.values_list('scene', flat=True))


class RuleCategory(models.Model):
    """规则分类树 - 同规则内可多层 (level 1..4)。"""

    id = models.CharField(max_length=32, primary_key=True, editable=False)
    rule = models.ForeignKey(
        SceneRule, on_delete=models.CASCADE,
        related_name='categories', verbose_name='所属规则',
    )
    parent = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='children', verbose_name='父分类',
    )
    name = models.CharField(max_length=32, verbose_name='分类名')
    order = models.IntegerField(default=0, verbose_name='排序')
    allow_custom = models.BooleanField(default=False, verbose_name='允许业务自定义')
    level = models.IntegerField(default=1, verbose_name='层级 1..4')

    class Meta:
        db_table = 'rule_category'
        verbose_name = '规则分类'
        verbose_name_plural = '规则分类'
        ordering = ['rule', 'parent__id', 'order']
        indexes = [
            models.Index(fields=['rule', 'parent'], name='idx_rcat_rule_parent'),
        ]
        constraints = [
            CheckConstraint(
                condition=Q(level__gte=1) & Q(level__lte=4),
                name='ck_rcat_level_1_4',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.rule.name} / {self.name}'

    def save(self, *args, **kwargs):
        if not self.id:
            from nanoid import generate as nanoid_generate
            self.id = nanoid_generate(size=21)
        super().save(*args, **kwargs)


class CategoryAssignment(models.Model):
    """分类 ↔ 标签 多对多关系。"""

    id = models.CharField(max_length=32, primary_key=True, editable=False)
    category = models.ForeignKey(
        RuleCategory, on_delete=models.CASCADE,
        related_name='assignments', verbose_name='分类',
    )
    tag = models.ForeignKey(
        ReasonTag, on_delete=models.PROTECT,
        related_name='category_assignments', verbose_name='标签',
    )
    order = models.IntegerField(default=0, verbose_name='排序')

    class Meta:
        db_table = 'category_assignment'
        verbose_name = '分类标签绑定'
        verbose_name_plural = '分类标签绑定'
        ordering = ['category', 'order']
        # Item4 (2026-09-21 修订): 唯一性收窄为【规则内】— 同一规则内标签不可跨分类
        # 重复; 跨规则共享标签池是合法业务需求 (如两条预置规则都用同一系统标签)。
        # 规则内唯一由 wizard_service 保存时应用层校验 (写入口集中), 不设 DB 全局约束。
        constraints = []

    def __str__(self) -> str:
        return f'{self.category.name} ↔ {self.tag.name}'

    def save(self, *args, **kwargs):
        if not self.id:
            from nanoid import generate as nanoid_generate
            self.id = nanoid_generate(size=21)
        super().save(*args, **kwargs)


class RuleSceneAssignment(models.Model):
    """场景 → 规则 单向引用。UNIQUE(scene) 兜底 Q6 一场景一规则。"""

    id = models.CharField(max_length=32, primary_key=True, editable=False)
    rule = models.ForeignKey(
        SceneRule, on_delete=models.CASCADE,
        related_name='scene_assignments', verbose_name='规则',
    )
    scene = models.CharField(max_length=32, choices=[(s, s) for s in SCENE_OPTIONS], verbose_name='场景')

    class Meta:
        db_table = 'rule_scene_assignment'
        verbose_name = '规则场景引用'
        verbose_name_plural = '规则场景引用'
        constraints = [
            UniqueConstraint(fields=['scene'], name='uniq_scene'),
        ]

    def __str__(self) -> str:
        return f'{self.rule.name} @ {self.scene}'

    def save(self, *args, **kwargs):
        if not self.id:
            from nanoid import generate as nanoid_generate
            self.id = nanoid_generate(size=21)
        super().save(*args, **kwargs)
