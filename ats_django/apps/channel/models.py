"""Channel Models (PRD v4 §14.5 渠道管理)"""
from django.db import models
from apps.common.models import FullAuditModel
from nanoid import generate as nanoid_generate


def gen_id():
    return nanoid_generate(size=21)


class Channel(FullAuditModel):
    """招聘渠道"""
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    name = models.CharField(max_length=100, verbose_name='渠道名')
    code = models.CharField(max_length=50, unique=True, verbose_name='渠道编码')

    category = models.CharField(max_length=50, verbose_name='渠道分类',
        help_text='CAMPUS/SOCIAL/HEADHUNTER/REFERRAL/AGENCY/OTHER')

    cost_per_resume = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='单简历成本')
    cost_per_hire = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='单入职成本')
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='总投入')

    contact_name = models.CharField(max_length=50, blank=True, verbose_name='联系人')
    contact_phone = models.CharField(max_length=20, blank=True, verbose_name='联系电话')

    is_active = models.BooleanField(default=True, db_index=True, verbose_name='启用')

    class Meta:
        db_table = 'channels'
        verbose_name = '招聘渠道'
        verbose_name_plural = verbose_name
        ordering = ['name']

    def __str__(self):
        return self.name


class ChannelCost(FullAuditModel):
    """渠道成本记录"""
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name='costs', verbose_name='渠道')
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='金额')
    cost_type = models.CharField(max_length=32, verbose_name='费用类型', help_text='POSTER/BOOTH/AGENT_FEE/OTHER')
    description = models.TextField(blank=True, verbose_name='说明')
    incurred_at = models.DateField(verbose_name='发生日期')

    class Meta:
        db_table = 'channel_costs'
        verbose_name = '渠道成本'
        verbose_name_plural = verbose_name
        ordering = ['-incurred_at']
