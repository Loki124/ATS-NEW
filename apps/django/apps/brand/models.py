"""品牌信息管理 (G43) 数据模型。

雇主品牌信息属于「全局配置」性质 —— 整个租户只有一份, 因此采用**单例**语义:
``BrandInfoView`` 在 GET 时若不存在则惰性创建一条, 之后所有 GET/PUT/PATCH 都作用于
该唯一行。模型本身不引入软删(单例配置删除无意义), 仅继承时间戳基类。
"""
from django.db import models
from nanoid import generate as nanoid_generate

from apps.common.models import TimestampedModel


class BrandInfo(TimestampedModel):
    """雇主品牌信息 —— 公司品牌文案、Logo、招聘门户展示信息（单例）。"""

    id = models.CharField(
        max_length=32, primary_key=True, editable=False, help_text='唯一标识',
    )
    company_name = models.CharField(max_length=255, default='', blank=True, help_text='雇主 / 公司名称')
    brand_slogan = models.CharField(max_length=255, default='', blank=True, help_text='品牌标语 / Slogan')
    # 雇主品牌文案(长文本): 招聘门户「关于我们」等展示文案
    brand_intro = models.TextField(default='', blank=True, help_text='雇主品牌文案')

    # Logo: 当前仅保存 URL(对外可访问的图片地址), 不内置上传通道(无文件端点)
    logo_url = models.CharField(max_length=512, default='', blank=True, help_text='Logo 图片 URL')

    # 招聘门户展示信息
    portal_title = models.CharField(max_length=255, default='', blank=True, help_text='招聘门户标题')
    portal_subtitle = models.CharField(max_length=255, default='', blank=True, help_text='招聘门户副标题')
    portal_banner_url = models.CharField(max_length=512, default='', blank=True, help_text='招聘门户 Banner 图 URL')
    # 门户主题主色(hex), 用于门户品牌化着色
    primary_color = models.CharField(max_length=32, default='', blank=True, help_text='门户主题主色 (hex)')

    # 联系信息
    contact_email = models.CharField(max_length=255, default='', blank=True, help_text='招聘联系邮箱')
    contact_phone = models.CharField(max_length=64, default='', blank=True, help_text='招聘联系电话')

    # 社交 / 官网链接: [{ platform, label, url }]
    #   platform: wechat / weibo / linkedin / official_site / other
    #   label:    展示名称
    #   url:      链接地址
    social_links = models.JSONField(default=list, blank=True, help_text='社交 / 官网链接列表')

    class Meta:
        db_table = 'brand_info'
        ordering = ['created_at']
        verbose_name = '品牌信息'
        verbose_name_plural = '品牌信息'

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = nanoid_generate(size=21)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'BrandInfo({self.company_name or "未命名"})'
