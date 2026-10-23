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


@pytest.mark.django_db
def test_reencrypt_pii_reports_plaintext_row_clearly():
    """2026-10-23: **历史明文行**必须得到**可行动**的明确报错。

    原实现把明文行丢给 decrypt_value → strict 下抛 DecryptionError →
    报错只说「解密失败」，会把排障方向引向「检查 ENCRYPTION_KEYS 配置」，
    而真正的问题是「这行压根就没加密」。
    ⇒ 现在必须报错说「明文」并给出 --include-plaintext 开关。
    """
    from django.core.management import call_command
    from django.core.management.base import CommandError

    from apps.candidate.models import Candidate

    key = Fernet.generate_key().decode()
    with override_settings(ENCRYPTION_KEYS=key, STRICT_DECRYPT=True):
        cand = Candidate.objects.create(name='历史明文行')
        # 用底层 UPDATE 写明文，绕过 ORM 的自动加密（模拟"加密上线前写入的历史行"）
        tbl = Candidate._meta.db_table
        with connection.cursor() as cur:
            cur.execute(
                f'UPDATE {tbl} SET id_card_no=%s WHERE id=%s',
                ['110101199001011234', cand.pk],
            )

        with pytest.raises(CommandError) as exc:
            call_command('reencrypt_pii')
        msg = str(exc.value)
        assert '明文' in msg, f'报错必须指出是明文行: {msg}'
        assert '--include-plaintext' in msg, f'报错必须给出可行动开关: {msg}'


@pytest.mark.django_db
def test_reencrypt_pii_can_encrypt_plaintext_row():
    """--include-plaintext: 历史明文行被主密钥收敛成密文，且能解回原明文。"""
    from django.core.management import call_command

    from apps.candidate.models import Candidate
    from apps.common.encryption import decrypt_value

    key = Fernet.generate_key().decode()
    plain = '110101199001011234'
    with override_settings(ENCRYPTION_KEYS=key, STRICT_DECRYPT=True):
        cand = Candidate.objects.create(name='历史明文行2')
        tbl = Candidate._meta.db_table
        with connection.cursor() as cur:
            cur.execute(
                f'UPDATE {tbl} SET id_card_no=%s WHERE id=%s',
                [plain, cand.pk],
            )

        call_command('reencrypt_pii', include_plaintext=True)

        raw = _raw_id_card(cand.pk, Candidate)
        assert raw.startswith('gAAAAA'), f'明文行必须被加密成 Fernet 密文: {raw!r}'
        assert decrypt_value(raw) == plain, '加密后必须能解回原明文'
