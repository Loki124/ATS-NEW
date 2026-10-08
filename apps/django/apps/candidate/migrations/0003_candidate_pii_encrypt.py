"""Candidate PII 字段加密 (2026-08-03 S3)

Step 1: 加新列
  - phone_hash: sha256(phone), 用于查重/匿名查询
  - email_hash: sha256(email), 同上
  - id_card_no_encrypted: Fernet 加密, 替代旧 id_card_no 明文

Step 2: RunPython 回填已有数据
  - phone_hash = hash_for_search(phone)
  - email_hash = hash_for_search(email)
  - id_card_no_encrypted = Fernet.encrypt(id_card_no)

Step 3 (后续 0004 migration): 删旧 id_card_no 列, rename id_card_no_encrypted → id_card_no

⚠️ 重要: 此 migration 在生产环境跑前, 必须先:
  1) 设置 ENCRYPTION_KEY 或 INTEGRATION_FERNET_KEY 环境变量
  2) 备份 candidates 表
  3) 通知候选人可能短期无法 search by id_card_no
"""
from django.db import migrations, models


def hash_for_search_py(plaintext, salt='ats-pii'):
    """Python 版 hash_for_search, 不依赖 apps.common.encryption (避免 migration 阶段循环 import)"""
    if not plaintext:
        return ''
    import hashlib
    h = hashlib.sha256()
    h.update(salt.encode('utf-8'))
    h.update(b':')
    h.update(plaintext.strip().lower().encode('utf-8'))
    return h.hexdigest()


def encrypt_py(plaintext):
    """Python 版 Fernet encrypt, 同样避免循环 import"""
    if not plaintext:
        return plaintext
    from cryptography.fernet import Fernet
    from django.conf import settings
    key = (
        getattr(settings, 'ENCRYPTION_KEY', None)
        or getattr(settings, 'INTEGRATION_FERNET_KEY', None)
        or ''
    )
    if not key:
        raise RuntimeError('ENCRYPTION_KEY / INTEGRATION_FERNET_KEY 未设置, 无法迁移加密数据')
    f = Fernet(key.encode() if isinstance(key, str) else key)
    return f.encrypt(plaintext.encode('utf-8')).decode('ascii')


def backfill_pii(apps, schema_editor):
    """回填 phone_hash / email_hash / id_card_no_encrypted"""
    Candidate = apps.get_model('candidate', 'Candidate')
    qs = Candidate.objects.filter(deleted_at__isnull=True)
    total = qs.count()
    if total == 0:
        return
    # 批量处理, 每次 1000 条
    for cand in qs.iterator(chunk_size=1000):
        cand.phone_hash = hash_for_search_py(cand.phone)
        cand.email_hash = hash_for_search_py(cand.email)
        if cand.id_card_no:
            cand.id_card_no_encrypted = encrypt_py(cand.id_card_no)
        cand.save(update_fields=['phone_hash', 'email_hash', 'id_card_no_encrypted'])


def reverse_backfill(apps, schema_editor):
    """rollback 不需要反向 (数据迁移是无损的, 旧字段还在)"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('candidate', '0002_candidate_extra'),
    ]

    operations = [
        # 1. 加新列 (nullable, 避免破坏已有行)
        migrations.AddField(
            model_name='candidate',
            name='phone_hash',
            field=models.CharField(
                blank=True, db_index=True, max_length=64,
                verbose_name='手机号 hash (sha256, 用于查重)',
            ),
        ),
        migrations.AddField(
            model_name='candidate',
            name='email_hash',
            field=models.CharField(
                blank=True, db_index=True, max_length=64,
                verbose_name='邮箱 hash (sha256, 用于查重)',
            ),
        ),
        migrations.AddField(
            model_name='candidate',
            name='id_card_no_encrypted',
            field=models.CharField(
                blank=True, db_index=True, max_length=512,
                verbose_name='身份证号 (Fernet 加密)',
                help_text='2026-08-03 S3: PII 加密, 老数据已回填',
            ),
        ),
        # 2. 回填数据
        migrations.RunPython(backfill_pii, reverse_backfill),
    ]
