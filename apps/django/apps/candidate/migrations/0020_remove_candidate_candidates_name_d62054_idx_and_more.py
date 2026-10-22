"""2026-10-21 卡 C4 —— 候选人 phone / email 改字段级加密（Fernet）。

**为什么是数据迁移而不是只改字段**：列里存着**存量明文**。只改字段类型的话，
ORM 之后写入的是密文，但存量行仍是明文 → 同一列两种格式，读出来一半是明文一半是密文，
且按明文查会**静默**只命中存量行。故必须先把存量明文加密，再改字段类型。

**顺序不可换**：
1. 撤掉 phone/email 上的 FULLTEXT 索引（加密后索引的是密文，必然失效；且改名/改类型会重建它）；
2. RunPython：把存量明文加密成 Fernet 密文（此时列还是明文，用历史模型读写，读明文写密文）；
3. RemoveIndex / AlterField：改列类型与索引。

**反向迁移**：用 `decrypt_value` 把密文还原成明文（Fernet 可逆），保证回滚可用。
"""
from django.db import migrations, models

import apps.common.encryption

BATCH_SIZE = 500

#: phone/email 上的 FULLTEXT 索引（apps/candidate/migrations/0013 建）——
#: 加密后索引的是密文，搜索已改走 hash 盲索引列精确匹配，这两个索引纯属浪费写入。
_FULLTEXT_ON_ENCRYPTED = ('ft_candidate_phone', 'ft_candidate_email')


def _encrypt_column(model, column: str) -> int:
    """把某列的存量明文逐批加密写回。返回处理行数。

    用历史模型读写：此时列还是普通 CharField → 读出来是明文、写进去不会被二次加密。
    """
    from apps.common.encryption import encrypt_value

    total = 0
    last_pk = ''
    while True:
        batch = list(
            model.objects.exclude(**{f'{column}__isnull': True})
            .exclude(**{column: ''})
            .filter(pk__gt=last_pk)
            .order_by('pk')[:BATCH_SIZE]
        )
        if not batch:
            break
        last_pk = batch[-1].pk
        for row in batch:
            model.objects.filter(pk=row.pk).update(
                **{column: encrypt_value(getattr(row, column))}
            )
            total += 1
    return total


def _decrypt_column(model, column: str) -> int:
    """反向：把密文还原成明文（仅回滚用）。"""
    from apps.common.encryption import decrypt_value

    total = 0
    last_pk = ''
    while True:
        batch = list(
            model.objects.exclude(**{f'{column}__isnull': True})
            .exclude(**{column: ''})
            .filter(pk__gt=last_pk)
            .order_by('pk')[:BATCH_SIZE]
        )
        if not batch:
            break
        last_pk = batch[-1].pk
        for row in batch:
            model.objects.filter(pk=row.pk).update(
                **{column: decrypt_value(getattr(row, column), field_name=column)}
            )
            total += 1
    return total


def drop_fulltext_on_encrypted(apps, schema_editor):
    """撤掉 phone/email 上的 FULLTEXT 索引（加密后失效）。"""
    if schema_editor.connection.vendor != 'mysql':
        return
    table = apps.get_model('candidate', 'Candidate')._meta.db_table
    with schema_editor.connection.cursor() as cur:
        for index_name in _FULLTEXT_ON_ENCRYPTED:
            try:
                cur.execute(f'DROP INDEX {index_name} ON {table}')
            except Exception:  # noqa: BLE001 — 索引不存在(DBA 已手工处理/非 MySQL 路径)时忽略
                pass


def widen_pii_columns(apps, schema_editor):
    """把 phone / email 列先加宽到 512 —— 必须在「加密写回」之前。

    为什么（2026-10-21 实测修）：Fernet 密文约 140 字符，而存量列是
    phone varchar(20) / email varchar(100)。原迁移把 AlterField(加宽) 放在
    RunPython(加密) **之后** ⇒ 严格模式（STRICT_TRANS_TABLES）下把密文写回窄列
    直接报 `Data too long for column 'phone' at row 1`，迁移整条卡死
    （连带把依赖 candidate app 的后续迁移全部堵住）。

    这里用裸 SQL 先加宽，**不改 migration state** —— 后面的 RunPython 仍按
    「旧模型 = 明文 CharField」读写，不会把已加密的密文二次加密。
    反向：随 AlterField 回滚自动收窄，本步骤反向为 no-op。
    """
    if schema_editor.connection.vendor != 'mysql':
        return
    table = apps.get_model('candidate', 'Candidate')._meta.db_table
    with schema_editor.connection.cursor() as cur:
        cur.execute(f'ALTER TABLE {table} MODIFY phone VARCHAR(512) NOT NULL')
        cur.execute(f'ALTER TABLE {table} MODIFY email VARCHAR(512) NULL')


def encrypt_existing_pii(apps, schema_editor):
    """把存量明文 phone / email 加密成 Fernet 密文。"""
    model = apps.get_model('candidate', 'Candidate')
    _encrypt_column(model, 'phone')
    _encrypt_column(model, 'email')


def decrypt_existing_pii(apps, schema_editor):
    """反向：密文还原明文。"""
    model = apps.get_model('candidate', 'Candidate')
    _decrypt_column(model, 'phone')
    _decrypt_column(model, 'email')


class Migration(migrations.Migration):

    dependencies = [
        ('candidate', '0019_candidatefollow_candidateforward'),
    ]

    operations = [
        migrations.RunPython(
            drop_fulltext_on_encrypted,
            migrations.RunPython.noop,
        ),
        # 2026-10-21：先加宽列，再加密写回（顺序反了会 "Data too long for column 'phone'"）
        migrations.RunPython(
            widen_pii_columns,
            migrations.RunPython.noop,
        ),
        migrations.RunPython(
            encrypt_existing_pii,
            decrypt_existing_pii,
        ),
        migrations.RemoveIndex(
            model_name='candidate',
            name='candidates_name_d62054_idx',
        ),
        migrations.AlterField(
            model_name='candidate',
            name='email',
            field=apps.common.encryption.EncryptedCharField(
                blank=True,
                help_text='Fernet 加密存储; 查重走 email_hash 列',
                max_length=512,
                null=True,
                verbose_name='邮箱',
            ),
        ),
        migrations.AlterField(
            model_name='candidate',
            name='email_hash',
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text='hash_for_search(email) 写入, 同明文 → 同 hash',
                max_length=80,
                verbose_name='邮箱 hash (sha256, 用于查重/匿名查询)',
            ),
        ),
        migrations.AlterField(
            model_name='candidate',
            name='phone',
            field=apps.common.encryption.EncryptedCharField(
                max_length=512, verbose_name='手机号'
            ),
        ),
    ]
