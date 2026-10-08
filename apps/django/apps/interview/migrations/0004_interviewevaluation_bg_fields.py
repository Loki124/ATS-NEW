# 面试评价新增 综合评价 / 背调建议 字段 (2026-10-08)
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('interview', '0003_interview_recruit_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='interviewevaluation',
            name='overall_eval',
            field=models.CharField(
                max_length=255, blank=True, verbose_name='综合评价',
                help_text='面试官对候选人的总体评价，≤255 字',
            ),
        ),
        migrations.AddField(
            model_name='interviewevaluation',
            name='bg_suggestion',
            field=models.CharField(
                max_length=255, blank=True, verbose_name='背调建议',
                help_text='针对背景调查的关注点/问题，以面试官为单位；驱动 offer 背景调查问答题与招聘专家通知，≤255 字',
            ),
        ),
    ]
