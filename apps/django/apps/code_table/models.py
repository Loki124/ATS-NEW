"""码表库 (G46) 数据模型。

统一存放国家/行业标准的只读码表，供候选人信息、招聘需求等表单字段直接关联复用：

- ``Region``     中国行政区划（省 / 市 / 区县 / 镇乡 四级，国家统计局口径）
- ``Country``    国家与地区（ISO 3166-1 + 国际电话区号）
- ``Ethnicity``  中国民族（GB/T 3304-1991，含字母码）
- ``Language``   语言（ISO 639，中英双语名）

设计约定：
- 均为**只读参考数据**，不引入软删（无业务删除语义），仅继承时间戳基类。
- 主键直接用标准代码（自然主键），便于按 code 直接关联与导入幂等。
- 数据由 ``manage.py import_code_tables`` 导入，支持重复执行（update_or_create）。
"""
from django.db import models
from nanoid import generate as nanoid_generate

from apps.common.models import SoftDeleteModel, SoftDeleteManager, TimestampedModel

# 行政区划层级：1省 2地级市 3区县 4镇/乡/街道
LEVEL_PROVINCE = 1
LEVEL_CITY = 2
LEVEL_COUNTY = 3
LEVEL_TOWN = 4

LEVEL_CHOICES = (
    (LEVEL_PROVINCE, '省级'),
    (LEVEL_CITY, '地级'),
    (LEVEL_COUNTY, '县级'),
    (LEVEL_TOWN, '乡级'),
)


class Region(TimestampedModel):
    """中国行政区划（省 / 市 / 区县 / 镇乡）。

    数据来源：国家统计局《统计用区划代码》（经 sinlmao/regions_data 整理）。
    code 为 12 位数字；parent_code 指向上级（省级为空）。
    """

    code = models.CharField(max_length=12, primary_key=True, help_text='区划代码')
    name = models.CharField(max_length=200, help_text='区划名称')
    level = models.SmallIntegerField(choices=LEVEL_CHOICES, db_index=True, help_text='层级 1省/2市/3县/4镇')
    parent_code = models.CharField(
        max_length=12, blank=True, default='', db_index=True, help_text='上级区划代码（省级为空）',
    )

    class Meta:
        db_table = 'code_region'
        ordering = ['code']
        verbose_name = '行政区划'
        verbose_name_plural = '行政区划'

    def __str__(self):
        return f'{self.code} {self.name}'


class Country(TimestampedModel):
    """国家 / 地区（ISO 3166-1 + 国际电话区号）。"""

    code = models.CharField(max_length=2, primary_key=True, help_text='ISO 3166-1 alpha-2')
    code3 = models.CharField(max_length=3, blank=True, default='', help_text='ISO 3166-1 alpha-3')
    name_cn = models.CharField(max_length=200, help_text='中文名称')
    name_en = models.CharField(max_length=200, blank=True, default='', help_text='英文名称')
    phone_code = models.CharField(max_length=10, blank=True, default='', help_text='国际电话区号，如 +86')

    class Meta:
        db_table = 'code_country'
        ordering = ['code']
        verbose_name = '国家/地区'
        verbose_name_plural = '国家/地区'

    def __str__(self):
        return f'{self.phone_code} {self.name_cn}'


class Ethnicity(TimestampedModel):
    """中国民族（GB/T 3304-1991）。"""

    code = models.CharField(max_length=2, primary_key=True, help_text='数字代码，如 01')
    name = models.CharField(max_length=50, help_text='民族名称')
    letter_code = models.CharField(max_length=2, blank=True, default='', help_text='罗马字母代码，如 HA')

    class Meta:
        db_table = 'code_ethnicity'
        ordering = ['code']
        verbose_name = '民族'
        verbose_name_plural = '民族'

    def __str__(self):
        return self.name


class Language(TimestampedModel):
    """语言类型（ISO 639，中英双语名）。"""

    code = models.CharField(max_length=8, primary_key=True, help_text='ISO 639 代码')
    name_cn = models.CharField(max_length=200, help_text='中文名称')
    name_en = models.CharField(max_length=200, blank=True, default='', help_text='英文名称')

    class Meta:
        db_table = 'code_language'
        ordering = ['code']
        verbose_name = '语言'
        verbose_name_plural = '语言'

    def __str__(self):
        return self.name_cn


class BusinessCode(SoftDeleteModel):
    """业务码表（自定义枚举）。

    与上面的**标准码表**（国标/行标、只读）相对：本表承载业务侧需要自行维护的
    枚举值——学历、职位类别、招聘渠道、离职原因、合同类型、币种、行业等。
    用户可增改删（完整 CRUD），标准码表仍保持只读 + 重新导入更新，二者互不污染。

    设计约定：
    - 软删（继承 SoftDeleteModel），枚举值可能被候选人/职位数据引用，物理删除会断引用。
    - ``is_customized`` 与院校库/专业库同义：用户在页面自建=True；未来若从标准集同步
      可置 False 并锁定编辑（当前全部为用户自建，恒为 True）。
    - (category, code) 同类唯一：唯一性由序列化器在应用层校验（软删场景下不便用 DB 唯一约束，
      否则删除后再建同 code 会撞唯一键）。查询默认过滤已软删行。
    - 主键用 nanoid（业务枚举无固定自然主键，且 code 同类唯一但跨类可重复）。
    """

    CATEGORY_CHOICES = (
        ('EDUCATION', '学历'),
        ('JOB_CATEGORY', '职位类别'),
        ('RECRUIT_CHANNEL', '招聘渠道'),
        ('OFFBOARD_REASON', '离职原因'),
        ('CONTRACT_TYPE', '合同类型'),
        ('CURRENCY', '币种'),
        ('INDUSTRY', '行业'),
    )

    id = models.CharField(max_length=32, primary_key=True, editable=False)
    category = models.CharField(
        max_length=40, choices=CATEGORY_CHOICES, db_index=True, help_text='业务枚举类别',
    )
    code = models.CharField(max_length=64, db_index=True, help_text='枚举值编码（同类下唯一）')
    name = models.CharField(max_length=200, help_text='枚举值名称')
    description = models.TextField(blank=True, default='', help_text='说明（可选）')
    parent_code = models.CharField(
        max_length=64, blank=True, default='', db_index=True, help_text='上级编码（可选层级，如行业→子行业）',
    )
    sort_order = models.IntegerField(default=0, help_text='排序（同类别内升序）')
    is_customized = models.BooleanField(
        default=True,
        help_text='True = 用户在页面自建；标准同步项可置 False 并锁定编辑',
    )
    updated_at = models.DateTimeField(auto_now=True, help_text='最后更新时间')

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        db_table = 'code_business'
        verbose_name = '业务码表'
        verbose_name_plural = '业务码表'
        ordering = ['category', 'sort_order', 'code']

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = nanoid_generate(size=21)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'[{self.get_category_display()}] {self.code} {self.name}'
