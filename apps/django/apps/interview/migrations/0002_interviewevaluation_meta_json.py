"""v2 (2026-09-03)：InterviewEvaluation 新增 meta_json JSONField
存储评价 meta（4 维符合性 + 文字依据 + 建议职级/薪资 + 3 档 finalResult），
避免污染 scores 真实分数 key。前端 v2 (af10812) 用 packEvalScores() 把 meta
塞 scores['__meta'] 临时方案，新字段就位后改写为 meta_json 字段。
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('interview', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='interviewevaluation',
            name='meta_json',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='{"compliances": {...}, "suggestedLevel": "...", "suggestedSalary": "...", "finalResult": "PASS|FAIL|PENDING"}',
                verbose_name='评价 meta',
            ),
        ),
    ]