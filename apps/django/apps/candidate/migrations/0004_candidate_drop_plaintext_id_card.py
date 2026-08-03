"""Candidate 删旧明文 id_card_no (2026-08-03 S3, 收尾)

0003 已经把 id_card_no 加密写到 id_card_no_encrypted, 这里:
1. RemoveField id_card_no (旧明文列) —— 必须先删, 否则 rename 撞名
2. RenameField id_card_no_encrypted → id_card_no (应用层代码不变, 透明)
3. AlterField 对齐 model 定义 (EncryptedCharField, 去掉 db_index)

⚠️ 重要: 跑前确认 0003 已成功完成, id_card_no_encrypted 列有完整数据.
   跑完此 migration 后, 旧明文 id_card_no 数据被删除, 不可逆.

2026-08-03 R1 修复记录 (寇豆码):
- 原文件 `from django.db import migrations` 缺 `models` 导入, 但 :33 用了
  `models.CharField` → migration 图加载即 NameError, manage.py migrate 直接崩.
- 更深的问题: 原文件只有 RenameField + AlterField, 没有 RemoveField, 而
  0003 并未删除旧的明文 id_card_no 列 → SQLite 报
  "error in table candidates after rename: duplicate column name: id_card_no".
  按本文件 docstring 声明的意图补回 RemoveField, 并调整为"先删后改名".
- AlterField 改用真实的 EncryptedCharField (它只依赖 django.db.models /
  cryptography, 不会与 candidate.models 循环 import), 使 migration state 与
  model 定义一致, `makemigrations --check` 不再报漂移.
"""
from django.db import migrations

import apps.common.encryption


class Migration(migrations.Migration):

    dependencies = [
        ('candidate', '0003_candidate_pii_encrypt'),
    ]

    operations = [
        # 1. 先删旧明文列 (0001_initial 建的 CharField(max_length=20)).
        #    数据已由 0003 的 RunPython 回填进 id_card_no_encrypted.
        migrations.RemoveField(
            model_name='candidate',
            name='id_card_no',
        ),
        # 2. 把加密列 rename 回原名, 业务代码 / 序列化器 / view 都不用改
        migrations.RenameField(
            model_name='candidate',
            old_name='id_card_no_encrypted',
            new_name='id_card_no',
        ),
        # 3. 对齐 model: EncryptedCharField(max_length=512, blank=True), 无 db_index.
        #    加密值不可做前缀/等值检索, 索引没有意义 (查重走 phone_hash/email_hash).
        migrations.AlterField(
            model_name='candidate',
            name='id_card_no',
            field=apps.common.encryption.EncryptedCharField(
                blank=True, max_length=512, verbose_name='身份证号 (加密存储)',
            ),
        ),
    ]
