"""GDPR verification_code 字段 hash 化 (2026-08-03 S2)

旧字段 verification_code (CharField max_length=10, 明文) 删除
新字段:
  - verification_code_hash (CharField max_length=128, SHA-256 hex)
  - verification_code_expires_at (DateTimeField, 15 分钟 TTL)
  - verification_code_attempts (IntegerField, 5 次锁定)
  - verified_at (DateTimeField, 候选人验证通过时间)
status 字段 max_length 16 → 24 (容纳 EXPIRED/LOCKED 新枚举)

⚠️ 重要: 旧 verification_code 字段是明文存, 数据已不可信 (GDPR 风险),
    这里直接 DROP 不保留。生产环境跑此 migration 前:
    1) 通知候选人重新提交 GDPR 请求
    2) 或手动迁移: SELECT * FROM gdpr_requests WHERE verification_code != '' 然后人工 verify
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gdpr', '0001_initial'),
    ]

    operations = [
        # 1. status 字段 max_length 16 → 24
        migrations.AlterField(
            model_name='gdprrequest',
            name='status',
            field=models.CharField(
                choices=[
                    ('PENDING', '待验证'),
                    ('AWAITING_VERIFICATION', '待候选人验证'),
                    ('PROCESSING', '处理中'),
                    ('COMPLETED', '已完成'),
                    ('REJECTED', '已拒绝'),
                    ('EXPIRED', '已过期'),
                    ('LOCKED', '已锁定'),
                ],
                db_index=True,
                default='AWAITING_VERIFICATION',
                max_length=24,
                verbose_name='状态',
            ),
        ),
        # 2. 加新 hash 化字段
        migrations.AddField(
            model_name='gdprrequest',
            name='verification_code_hash',
            field=models.CharField(
                blank=True, db_index=True, max_length=128,
                verbose_name='验证码 SHA-256',
            ),
        ),
        migrations.AddField(
            model_name='gdprrequest',
            name='verification_code_expires_at',
            field=models.DateTimeField(
                null=True, blank=True, verbose_name='验证码过期时间',
            ),
        ),
        migrations.AddField(
            model_name='gdprrequest',
            name='verification_code_attempts',
            field=models.IntegerField(
                default=0, verbose_name='错误尝试次数',
            ),
        ),
        migrations.AddField(
            model_name='gdprrequest',
            name='verified_at',
            field=models.DateTimeField(
                null=True, blank=True, verbose_name='候选人验证通过时间',
            ),
        ),
        # 3. 删旧明文 verification_code 字段
        migrations.RemoveField(
            model_name='gdprrequest',
            name='verification_code',
        ),
        # 4. 加 expires_at 索引 (cleanup cron 用)
        migrations.AddIndex(
            model_name='gdprrequest',
            index=models.Index(
                fields=['verification_code_expires_at'],
                name='idx_gdpr_expires',
            ),
        ),
    ]
