"""2026-10-02 P2-2: reencrypt_pii 密钥轮换闭环命令测试

验证:
- 轮换后 DB 列里密文确实改变 (用新主 key 加密), 且仍能解密出原明文
- --dry-run 不写库
- 旧 key 漏配时命令必须中断 (零写入, 不静默损坏数据)

用 Candidate.id_card_no (EncryptedCharField) 作载体。密文比对用原生 cursor 读列,
绕过 ORM from_db_value, 才能确认"列内字节变了"。
"""
import pytest
from cryptography.fernet import Fernet
from django.db import connection
from django.test import override_settings

from apps.common.encryption import DecryptionError


def _raw_id_card(pk, model):
    tbl = model._meta.db_table
    with connection.cursor() as cur:
        cur.execute(f'SELECT id_card_no FROM {tbl} WHERE id=%s', [pk])
        return cur.fetchone()[0]


@pytest.mark.django_db
def test_reencrypt_pii_rotates_ciphertext():
    from django.core.management import call_command
    from apps.candidate.models import Candidate

    old_key = Fernet.generate_key().decode()
    new_key = Fernet.generate_key().decode()

    with override_settings(ENCRYPTION_KEYS=old_key, STRICT_DECRYPT=True):
        cand = Candidate.objects.create(name='轮换', id_card_no='110101199001011234')
        raw_old = _raw_id_card(cand.pk, Candidate)
        assert raw_old.startswith('gAAAAA'), '创建时应已加密存储'

    # 轮换: 新 key 在前 (加密用), 旧 key 在后 (仅解密)
    with override_settings(ENCRYPTION_KEYS=f'{new_key},{old_key}', STRICT_DECRYPT=True):
        call_command('reencrypt_pii')
        raw_new = _raw_id_card(cand.pk, Candidate)
        assert raw_new != raw_old, '密文必须改变 (已用新主 key 重写)'
        assert raw_new.startswith('gAAAAA')
        # 用新 key 单读能解回原明文
        assert Candidate.objects.get(pk=cand.pk).id_card_no == '110101199001011234'


@pytest.mark.django_db
def test_reencrypt_pii_dry_run_writes_nothing():
    from django.core.management import call_command
    from apps.candidate.models import Candidate

    old_key = Fernet.generate_key().decode()
    new_key = Fernet.generate_key().decode()

    with override_settings(ENCRYPTION_KEYS=old_key, STRICT_DECRYPT=True):
        cand = Candidate.objects.create(name='dry', id_card_no='110101199002022345')
        raw_old = _raw_id_card(cand.pk, Candidate)

    with override_settings(ENCRYPTION_KEYS=f'{new_key},{old_key}', STRICT_DECRYPT=True):
        call_command('reencrypt_pii', '--dry-run')
        raw_after = _raw_id_card(cand.pk, Candidate)
        assert raw_after == raw_old, 'dry-run 不应写库'


@pytest.mark.django_db
def test_reencrypt_pii_fails_without_old_key():
    """只设新 key (漏旧 key) → 旧密文解不开 → 命令必须中断, 零写入。"""
    from django.core.management import call_command
    from apps.candidate.models import Candidate

    old_key = Fernet.generate_key().decode()
    new_key = Fernet.generate_key().decode()

    with override_settings(ENCRYPTION_KEYS=old_key, STRICT_DECRYPT=True):
        Candidate.objects.create(name='x', id_card_no='110101199003033456')

    with override_settings(ENCRYPTION_KEYS=new_key, STRICT_DECRYPT=True):
        with pytest.raises(DecryptionError):
            call_command('reencrypt_pii')
