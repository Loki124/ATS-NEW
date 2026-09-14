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

from apps.common.models import TimestampedModel

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
