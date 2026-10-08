"""验证 EntrySource 枚举包含 DIRECT_IMPORT"""
import pytest

from apps.talent_pool.models import TalentPoolEntry


def test_entry_source_has_direct_import():
    """DIRECT_IMPORT 枚举值必须存在"""
    sources = dict(TalentPoolEntry.EntrySource.choices)
    assert 'DIRECT_IMPORT' in sources
    assert sources['DIRECT_IMPORT'] == '直接导入（HR 上传简历）'


def test_create_talent_pool_entry_with_direct_import(db, clean_candidate):
    """可以创建 source=DIRECT_IMPORT 的 TalentPoolEntry"""
    entry = TalentPoolEntry.objects.create(
        candidate=clean_candidate,
        source=TalentPoolEntry.EntrySource.DIRECT_IMPORT,
        source_detail='通过 HR 上传简历',
    )
    assert entry.source == 'DIRECT_IMPORT'
    assert entry.is_active is True