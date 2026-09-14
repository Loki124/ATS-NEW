# apps.library models
# 2026-06-29 花无缺: stub. 真实 model 设计留给后续.
# School 字段: id, name, code, location, province, city, education_level, school_type, school_category, status
# Company 字段: id, name, code, industry, scale, is_benchmark, description, status
from django.db import models
from nanoid import generate as nanoid_generate
from apps.common.models import SoftDeleteModel, SoftDeleteManager


class School(SoftDeleteModel):
    id = models.CharField(max_length=32, primary_key=True)
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    location = models.CharField(max_length=200, blank=True, default='')
    province = models.CharField(max_length=50, blank=True, default='')
    city = models.CharField(max_length=50, blank=True, default='')
    education_level = models.CharField(max_length=50, blank=True, default='')
    school_type = models.CharField(max_length=50, blank=True, default='')
    school_category = models.CharField(max_length=50, blank=True, default='')
    status = models.CharField(max_length=20, default='ACTIVE')

    class Meta:
        db_table = 'library_school'
        verbose_name = '院校'

    def __str__(self):
        return self.name



    objects = SoftDeleteManager()
    all_objects = models.Manager()
class Major(SoftDeleteModel):
    """专业库（阳光高考专业库）— 院校库「专业」Tab 数据源。

    层级：门类(discipline) > 专业类(category) > 专业(name)。
    数据由 ``manage.py import_majors --file <csv>`` 导入（spec_id 唯一，幂等）。
    """

    id = models.CharField(max_length=32, primary_key=True)
    spec_id = models.CharField(max_length=64, unique=True, help_text='数据源网站唯一ID')
    code = models.CharField(max_length=50, db_index=True, help_text='专业代码')
    name = models.CharField(max_length=200, db_index=True, help_text='专业名称')
    education_level = models.CharField(max_length=50, blank=True, default='', help_text='学历层次，如 本科（普通教育）')
    education_level_code = models.CharField(max_length=20, blank=True, default='', help_text='学历层次代码')
    discipline = models.CharField(max_length=100, blank=True, default='', db_index=True, help_text='门类，如 哲学')
    discipline_code = models.CharField(max_length=20, blank=True, default='', help_text='门类代码')
    category = models.CharField(max_length=100, blank=True, default='', db_index=True, help_text='专业类，如 哲学类')
    category_code = models.CharField(max_length=20, blank=True, default='', help_text='专业类代码')
    data_year = models.CharField(max_length=10, blank=True, default='', help_text='数据年份')
    intro = models.TextField(blank=True, default='', help_text='专业介绍')
    detail_url = models.CharField(max_length=500, blank=True, default='', help_text='详情页 URL')

    class Meta:
        db_table = 'library_major'
        verbose_name = '专业'
        verbose_name_plural = '专业'

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = nanoid_generate(size=21)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.code} {self.name}'

    objects = SoftDeleteManager()
    all_objects = models.Manager()


class Company(SoftDeleteModel):
    id = models.CharField(max_length=32, primary_key=True)
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    industry = models.CharField(max_length=50, blank=True, default='')
    scale = models.CharField(max_length=50, blank=True, default='')
    is_benchmark = models.BooleanField(default=False)
    description = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, default='ACTIVE')

    class Meta:
        db_table = 'library_company'
        verbose_name = '公司'

    def __str__(self):
        return self.name


    objects = SoftDeleteManager()
    all_objects = models.Manager()