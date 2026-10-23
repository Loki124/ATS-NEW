"""候选人审计体系测试（Task 1 基础 + 后续挂钩）。

覆盖：哈希链生成、不可篡改守卫（禁改/禁删）、compute_row_hash 确定性。
字段级 diff / 跨模块阶段写入 / 解析溯源 / verify 端点的用例在对应挂钩就位后补充。
"""
import pytest

from apps.candidate.audit import (
    AUDIT_HASH_REQUIRED_MAX_LENGTH,
    AuditImmutabilityError,
    compute_row_hash,
)
from apps.candidate.models import Candidate, CandidateHistory


def _make_candidate(phone='13800001001'):
    return Candidate.objects.create(name='审计测试', phone=phone)


@pytest.mark.django_db
def test_hash_chain_links_rows():
    c = _make_candidate()
    h1 = CandidateHistory.objects.create(candidate=c, action='CREATED', detail={'a': 1})
    h2 = CandidateHistory.objects.create(candidate=c, action='INFO_UPDATED', detail={'changes': []})
    h1.refresh_from_db()
    h2.refresh_from_db()
    assert (h1.seq, h2.seq) == (1, 2)
    assert h1.prev_hash == '' and h1.row_hash
    assert h2.prev_hash == h1.row_hash, '第二行 prev_hash 应链到第一行 row_hash'
    assert h2.row_hash and h2.row_hash != h1.row_hash


@pytest.mark.django_db
def test_immutability_blocks_update_and_delete():
    c = _make_candidate()
    h = CandidateHistory.objects.create(candidate=c, action='CREATED', detail={})
    h.refresh_from_db()
    h.action = 'TAMPERED'
    with pytest.raises(AuditImmutabilityError):
        h.save()
    with pytest.raises(AuditImmutabilityError):
        h.delete()
    with pytest.raises(AuditImmutabilityError):
        h.soft_delete()
    # 库里原值未变
    assert CandidateHistory.objects.get(pk=h.pk).action == 'CREATED'


@pytest.mark.django_db
def test_compute_row_hash_deterministic_and_sensitive():
    base = dict(candidate_id='c1', seq=1, action='INFO_UPDATED',
                detail={'changes': [{'field': 'email', 'old': 'a', 'new': 'b'}]},
                created_by_id=None, prev_hash='')
    h1 = compute_row_hash(**base)
    h2 = compute_row_hash(**base)
    assert h1 == h2, '同输入应得同哈希'
    tampered = dict(base, detail={'changes': [{'field': 'email', 'old': 'a', 'new': 'X'}]})
    assert compute_row_hash(**tampered) != h1, 'detail 变更应改变哈希'
    # detail 键序不影响（规范化）
    reordered = dict(base, detail={'changes': [{'new': 'b', 'old': 'a', 'field': 'email'}]})
    assert compute_row_hash(**reordered) == h1, 'detail 键序不应影响哈希（canonical）'


def test_audit_hash_columns_fit_prefix_margin():
    """哈希链列必须留得下「版本前缀 + 64 hex」的口径余量（决策A·J6）。

    sha256 hexdigest **恰好 64 字符** —— 列宽等于 64 就是零余量，哈希口径一改
    （加 'v2_' 版本前缀 / 换摘要算法）就撑爆列；而审计链撑爆 = **整链失效**
    （``histories/verify`` 直接报 broken_at），比单个 PII 列截断严重得多。

    这条断言把 models.py 的 max_length 与 audit.AUDIT_HASH_REQUIRED_MAX_LENGTH 绑在一起 ——
    任何一方单独回退到 64 都会被拦下。
    """
    digest_len = len(compute_row_hash(
        candidate_id='c1', seq=1, action='INFO_UPDATED',
        detail={}, created_by_id=None, prev_hash='',
    ))
    for name in ('prev_hash', 'row_hash'):
        field = CandidateHistory._meta.get_field(name)
        assert field.max_length >= AUDIT_HASH_REQUIRED_MAX_LENGTH, (
            f'{name} max_length={field.max_length} < {AUDIT_HASH_REQUIRED_MAX_LENGTH} '
            f'(哈希链列零余量, 改口径即整链失效)'
        )
        assert digest_len <= field.max_length, (
            f'{name} max_length={field.max_length} 装不下当前摘要长度 {digest_len}'
        )
