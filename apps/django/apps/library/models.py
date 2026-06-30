# apps.library models
# 2026-06-29 花无缺: stub. 真实 model 设计留给后续.
# School 字段: id, name, code, location, province, city, education_level, school_type, school_category, status
# Company 字段: id, name, code, industry, scale, is_benchmark, description, status
from django.db import models


class School(models.Model):
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


class Company(models.Model):
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
