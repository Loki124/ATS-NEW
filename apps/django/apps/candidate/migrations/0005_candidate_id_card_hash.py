"""Candidate 新增 id_card_hash 列 + 存量回填 (2026-08-03 BUG-1 修复, 寇豆码)

背景 (QA 严过关独立验证):
  id_card_no 在 0003/0004 被改成 Fernet 非确定性加密字段, 但查重逻辑
  (apps/candidate/services.py:_find_duplicate) 仍用 `Q(id_card_no=id_card)` 明文
  精确匹配 —— 密文每次加密结果都不同, 永远 0 命中, 等于身份证查重永久失效,
  同一人可无限重复入库。

  修复同 phone_hash / email_hash 的既有方案: 新增不可逆的 id_card_hash 列
  (sha256(plaintext), 见 apps.common.encryption.hash_for_search), 查重走 hash 列。

本 migration:
1. AddField id_card_hash (CharField max_length=64, db_index=True)
2. RunPython 回填存量: 读解密后的明文身份证号, 写 hash

⚠️ BUG-7 修复 (2026-08-03, QA-4 复现): 原版本模块级 `import apps.common.encryption`
加函数形参 `apps` 形成变量遮蔽 —— 当 Candidate 表里有数据时,
`apps.common.encryption.hash_for_search(...)` 实际访问 StateApps.common
(不存在), 抛 AttributeError, 导致任何带存量数据的部署 migrate 死锁。
之前的全绿是因为测试 DB 是 :memory: 且从未插候选人行, for 循环空跑,
遮蔽从未被求值 → 假绿。修复方式 (与 0003_candidate_pii_encrypt.py 一致):
  - 完全去掉对 apps.common.encryption 的模块级 import
  - 在文件内本地定义 hash_for_search_py, 自包含实现
  - 函数体内不再访问 `apps.<module>`, 只用 `apps.get_model(...)`
"""
import hashlib

from django.db import migrations, models


def hash_for_search_py(plaintext, salt='ats-pii'):
    """本地版 hash_for_search, 与 apps.common.encryption.hash_for_search 完全等价。

    实现细节保持一致 (salt + ':' + normalize(lowercase+strip) -> sha256):
      apps.common.encryption.hash_for_search = lambda: hashlib.sha256()...
    注: apps.common.encryption 的 docstring 写的是 HMAC-SHA256 但实际实现
    是 raw sha256, 这里忠实复制实现, 保证历史回填与未来 insert 产出同一
    hash, 查重链路不断。
    """
    if not plaintext:
        return ''
    h = hashlib.sha256()
    h.update(salt.encode('utf-8'))
    h.update(b':')
    h.update(plaintext.strip().lower().encode('utf-8'))
    return h.hexdigest()


def backfill_id_card_hash(apps, schema_editor):
    """存量候选人: 用解密后的明文身份证号回填 id_card_hash."""
    Candidate = apps.get_model('candidate', 'Candidate')
    for c in Candidate.objects.all().iterator():
        id_card = c.id_card_no  # EncryptedCharField 读出即自动解密
        if not id_card:
            continue
        c.id_card_hash = hash_for_search_py(id_card)
        c.save(update_fields=['id_card_hash'])


def reverse_backfill_id_card_hash(apps, schema_editor):
    """回滚: 清空 hash (列随后会被删掉)。"""
    Candidate = apps.get_model('candidate', 'Candidate')
    Candidate.objects.update(id_card_hash='')


class Migration(migrations.Migration):

    dependencies = [
        ('candidate', '0004_candidate_drop_plaintext_id_card'),
    ]

    operations = [
        migrations.AddField(
            model_name='candidate',
            name='id_card_hash',
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=64,
                verbose_name='身份证号 hash (sha256, 用于查重/匿名查询)',
            ),
        ),
        migrations.RunPython(backfill_id_card_hash, reverse_backfill_id_card_hash),
    ]