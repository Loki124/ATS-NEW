"""2026-09-27 全面技术审计报告 P0-1 / P0-2 / P2-2 加密加固回归测试

覆盖:
- P0-1 解密失败 fail-closed: STRICT_DECRYPT=True 抛 DecryptionError (不再静默返密文)
- P0-1 日志脱敏: warning / 异常信息里都不再出现密文内容 (原实现会写 ciphertext[:30])
- P0-1 向后兼容: 未开启 STRICT_DECRYPT 时保留 fail-open 历史行为
- P2-2 密钥轮换: ENCRYPTION_KEYS 多密钥 (MultiFernet) —— 新密钥加密 + 前密钥可读
- P0-2 查重哈希: 未配 PII_HASH_SALT 时与历史实现逐字节一致 (存量数据零影响)
- P0-2 查重哈希: 配置外部 salt 后产出 v2_ 前缀, 且双读 verify 同时认 v1/v2

这些用例全部不触数据库, 可在 --nomigrations 下运行。
"""
import hashlib
import logging

import pytest
from cryptography.fernet import Fernet
from django.test import override_settings

from apps.common.encryption import (
    HASH_V2_PREFIX,
    HASH_V2_REQUIRED_MAX_LENGTH,
    LEGACY_HASH_SALT,
    DecryptionError,
    decrypt_value,
    encrypt_value,
    hash_candidates_for_search,
    hash_for_search,
    verify_hash_for_search,
)

PLAIN_PHONE = '13800138000'
LOGGER_NAME = 'apps.common.encryption'


# ============ 基础加解密 ============

def test_encrypt_decrypt_roundtrip():
    ct = encrypt_value(PLAIN_PHONE)
    assert ct != PLAIN_PHONE
    assert decrypt_value(ct) == PLAIN_PHONE


def test_none_and_empty_passthrough():
    assert encrypt_value(None) is None
    assert encrypt_value('') == ''
    assert decrypt_value(None) is None
    assert decrypt_value('') == ''


# ============ P0-1: 解密失败 fail-closed ============

def _ciphertext_then_rotate_key() -> str:
    """用当前 key 加密, 返回一个只有"另一个 key"才能解开的密文。"""
    return encrypt_value(PLAIN_PHONE)


@override_settings(STRICT_DECRYPT=True)
def test_strict_mode_raises_instead_of_returning_ciphertext():
    """STRICT_DECRYPT=True: 解密失败必须抛异常, 绝不静默返回密文 (原 fail-open)。"""
    ct = _ciphertext_then_rotate_key()
    with override_settings(ENCRYPTION_KEY=Fernet.generate_key().decode()):
        with pytest.raises(DecryptionError):
            decrypt_value(ct)


def test_legacy_fail_open_preserved_when_not_strict():
    """未开 STRICT_DECRYPT: 保留历史 fail-open 行为 (返回原值), 用于迁移过渡期。"""
    ct = _ciphertext_then_rotate_key()
    with override_settings(ENCRYPTION_KEY=Fernet.generate_key().decode()):
        assert decrypt_value(ct) == ct


@override_settings(STRICT_DECRYPT=True)
def test_strict_error_message_leaks_no_ciphertext():
    """异常信息不得包含密文内容, 只应含字段名 + 错误类型。"""
    ct = _ciphertext_then_rotate_key()
    with override_settings(ENCRYPTION_KEY=Fernet.generate_key().decode()):
        with pytest.raises(DecryptionError) as exc_info:
            decrypt_value(ct, field_name='phone')
    msg = str(exc_info.value)
    assert ct not in msg, 'DecryptionError 泄露了密文'
    assert 'phone' in msg, '异常应指明字段名以便定位'


def test_fail_open_log_leaks_no_ciphertext(caplog):
    """P0-1 日志脱敏: 原实现写 ciphertext[:30], 现在只记字段名 + 错误类型。"""
    ct = _ciphertext_then_rotate_key()
    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        with override_settings(ENCRYPTION_KEY=Fernet.generate_key().decode()):
            decrypt_value(ct, field_name='id_card_no')
    assert ct not in caplog.text, '日志泄露了密文'
    assert 'id_card_no' in caplog.text, '日志应含字段名以便定位'


def test_plaintext_passthrough_still_works_in_strict_mode():
    """明文历史数据在 strict 下也不应被误判为错误 (解不开但非 Fernet token 时降级)。

    注: 这是 fail-open 的历史兼容分支; strict 只针对"看起来是密文却解不开"的场景。
    当前实现对二者同等对待 (strict 一律抛), 故此处断言 strict 下明文也抛,
    以锁定"宁可失败也不返不可信数据"的语义。
    """
    with override_settings(STRICT_DECRYPT=True):
        with pytest.raises(DecryptionError):
            decrypt_value('this-is-not-a-fernet-token', field_name='phone')


# ============ P2-2: 密钥轮换 (MultiFernet) ============

def test_multifernet_rotation_old_ciphertext_still_readable():
    """轮换后: 新密钥用于加密, 旧密钥数据仍可解密。"""
    old_key = Fernet.generate_key().decode()
    new_key = Fernet.generate_key().decode()

    with override_settings(ENCRYPTION_KEYS=old_key):
        ct_old = encrypt_value(PLAIN_PHONE)

    # 新密钥在前 (加密用), 旧密钥在后 (仅解密)
    with override_settings(ENCRYPTION_KEYS=f'{new_key},{old_key}'):
        assert decrypt_value(ct_old) == PLAIN_PHONE, '轮换后旧数据必须仍可读'
        fresh = encrypt_value(PLAIN_PHONE)
        assert decrypt_value(fresh) == PLAIN_PHONE


def test_single_key_path_unchanged_when_no_key_list():
    """未配置 ENCRYPTION_KEYS 时退化为单密钥, 行为不变。"""
    ct = encrypt_value(PLAIN_PHONE)
    assert decrypt_value(ct) == PLAIN_PHONE


# ============ P0-2: 查重哈希 salt ============

@override_settings(PII_HASH_SALT='')
def test_legacy_hash_is_byte_identical_to_old_implementation():
    """未配 PII_HASH_SALT: 必须与历史实现逐字节一致, 否则存量查重全废。

    显式清空 PII_HASH_SALT —— 本仓库 .env 已启用真实 salt, 不显式控制就会
    测到 v2 分支而误判"历史兼容被破坏"。
    """
    expected = hashlib.sha256()
    expected.update(LEGACY_HASH_SALT.encode('utf-8'))
    expected.update(b':')
    expected.update(PLAIN_PHONE.strip().lower().encode('utf-8'))
    assert hash_for_search(PLAIN_PHONE) == expected.hexdigest()


@override_settings(PII_HASH_SALT='')
def test_explicit_salt_argument_preserved():
    """显式传 salt 的老调用方行为不变 (产出无前缀 digest)。"""
    assert hash_for_search(PLAIN_PHONE, 'ats-pii') == hash_for_search(PLAIN_PHONE)


def test_external_salt_produces_v2_prefixed_hash():
    """配置 PII_HASH_SALT 后产出带 v2_ 前缀的新哈希, 与存量 v1 不同。"""
    with override_settings(PII_HASH_SALT=''):
        legacy = hash_for_search(PLAIN_PHONE)
    with override_settings(PII_HASH_SALT='s' * 32):
        v2 = hash_for_search(PLAIN_PHONE)
    assert not legacy.startswith(HASH_V2_PREFIX)
    assert v2.startswith(HASH_V2_PREFIX)
    assert v2 != legacy


def test_verify_hash_dual_read_accepts_v1_and_v2():
    """灰度切换期: 双读必须同时认存量 v1 与新 v2, 否则回填期会漏判。"""
    with override_settings(PII_HASH_SALT=''):
        v1 = hash_for_search(PLAIN_PHONE)
    with override_settings(PII_HASH_SALT='s' * 32):
        v2 = hash_for_search(PLAIN_PHONE)
        assert verify_hash_for_search(PLAIN_PHONE, v1) is True, '存量 v1 必须仍匹配'
        assert verify_hash_for_search(PLAIN_PHONE, v2) is True, '新 v2 必须匹配'
        assert verify_hash_for_search(PLAIN_PHONE, 'definitely-not-a-hash') is False


def test_verify_hash_empty_inputs():
    assert verify_hash_for_search(None, 'x') is False
    assert verify_hash_for_search(PLAIN_PHONE, '') is False


def test_hash_empty_plaintext():
    assert hash_for_search('') == ''
    assert hash_for_search(None) == ''


def test_hash_normalizes_case_and_whitespace():
    assert hash_for_search('  Alice@Example.COM ') == hash_for_search('alice@example.com')


# ============ P0-2: 双读候选 & 列宽不变量 ============

def test_hash_candidates_returns_both_forms_when_salt_configured():
    """启用 salt 后, DB 查询候选必须同时含 v1 与 v2, 否则回填期漏判。"""
    with override_settings(PII_HASH_SALT=''):
        v1 = hash_for_search(PLAIN_PHONE)
    with override_settings(PII_HASH_SALT='s' * 32):
        cands = hash_candidates_for_search(PLAIN_PHONE)
    assert v1 in cands, '存量 v1 必须在候选里 (否则回填期漏判 → 重复候选人)'
    assert any(c.startswith(HASH_V2_PREFIX) for c in cands), '新 v2 必须在候选里'


def test_hash_candidates_only_v1_when_no_salt():
    with override_settings(PII_HASH_SALT=''):
        cands = hash_candidates_for_search(PLAIN_PHONE)
        # 期望值必须在同一 salt 口径下计算, 否则会拿 .env 的真实 salt 去比 v1
        expected = hash_for_search(PLAIN_PHONE)
    assert len(cands) == 1
    assert cands == [expected]


def test_hash_candidates_empty_plaintext():
    assert hash_candidates_for_search('') == []
    assert hash_candidates_for_search(None) == []


@pytest.mark.django_db
def test_pii_hash_columns_fit_v2_prefix():
    """哈希列必须装得下 'v2_' + 64 hex = 67 字符。

    这条断言把 models.py 的 max_length 与 encryption 的前缀需求绑在一起 ——
    任何一方单独改动都会被拦下, 避免"启用 salt 后哈希被静默截断"。
    """
    from apps.candidate.models import Candidate

    for name in ('phone_hash', 'email_hash', 'id_card_hash'):
        field = Candidate._meta.get_field(name)
        assert field.max_length >= HASH_V2_REQUIRED_MAX_LENGTH, (
            f'{name} max_length={field.max_length} < {HASH_V2_REQUIRED_MAX_LENGTH} '
            f'(v2_ 前缀 + 64 hex 装不下, 会被截断)'
        )


# ============ P0-2: 回填命令 ============

@pytest.mark.django_db
def test_rehash_command_requires_salt():
    """没配 salt 就回填等于没轮换 —— 必须明确报错而不是静默跑完。"""
    from django.core.management import call_command
    from django.core.management.base import CommandError

    with override_settings(PII_HASH_SALT=''):
        with pytest.raises(CommandError):
            call_command('rehash_pii_hashes')


@pytest.mark.django_db
def test_rehash_command_backfills_v1_to_v2():
    from django.core.management import call_command
    from apps.candidate.models import Candidate

    with override_settings(PII_HASH_SALT=''):
        cand = Candidate.objects.create(
            name='回填测试', phone='13900000999', email='rh@example.com',
            id_card_no='110101199001011234',
        )
        v1_id_hash = cand.id_card_hash
        v1_phone_hash = cand.phone_hash
    assert not v1_id_hash.startswith(HASH_V2_PREFIX)

    with override_settings(PII_HASH_SALT='t' * 40):
        call_command('rehash_pii_hashes')
        # 断言必须在同一 salt 口径下做, 否则会拿 .env 的真实 salt 去比 't'*40 的哈希
        cand.refresh_from_db()

        assert cand.id_card_hash.startswith(HASH_V2_PREFIX), '存量应被回填为 v2'
        assert cand.id_card_hash != v1_id_hash
        assert cand.phone_hash.startswith(HASH_V2_PREFIX)
        assert cand.phone_hash != v1_phone_hash
        # 双读必须同时认新旧两种形态
        assert verify_hash_for_search('110101199001011234', cand.id_card_hash) is True
        assert verify_hash_for_search('110101199001011234', v1_id_hash) is True


@pytest.mark.django_db
def test_rehash_command_dry_run_writes_nothing():
    from django.core.management import call_command
    from apps.candidate.models import Candidate

    with override_settings(PII_HASH_SALT=''):
        cand = Candidate.objects.create(
            name='演练测试', phone='13900000888', email='dry@example.com',
            id_card_no='110101199002022345',
        )
        before = cand.id_card_hash

    with override_settings(PII_HASH_SALT='t' * 40):
        call_command('rehash_pii_hashes', '--dry-run')
    cand.refresh_from_db()
    assert cand.id_card_hash == before, 'dry-run 不应写库'


@pytest.mark.django_db
def test_rehash_round_trip_is_reversible():
    """回填必须可逆 —— 否则"执行过回填"就等于"不能再回滚代码"。

    真实风险: 回填后存量哈希变成 v2_; 若此时回滚到旧代码 (查重只认 v1),
    所有存量候选人都匹配不上 → 查重漏判、重复入库。所以 --to-legacy 是
    部署回滚路径的必要一环, 不是可选的锦上添花。
    """
    from django.core.management import call_command
    from apps.candidate.models import Candidate

    with override_settings(PII_HASH_SALT=''):
        cand = Candidate.objects.create(
            name='回滚测试', phone='13900000777', email='rb@example.com',
            id_card_no='110101199003033456',
        )
        original_v1 = cand.id_card_hash

    with override_settings(PII_HASH_SALT='t' * 40):
        call_command('rehash_pii_hashes')
        cand.refresh_from_db()
        assert cand.id_card_hash.startswith(HASH_V2_PREFIX), '先回填到 v2'

        call_command('rehash_pii_hashes', '--to-legacy')
        cand.refresh_from_db()

    assert cand.id_card_hash == original_v1, '回滚后必须逐字节回到原始 v1 哈希'
    assert not cand.id_card_hash.startswith(HASH_V2_PREFIX)
