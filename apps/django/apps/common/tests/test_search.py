"""keyword_q 搜索后端测试。

- SQLite（本地默认）：走 like 路径，验证空词 / 构造正确性。
- MySQL（CI 测试库）：走 fulltext 路径，验证 MATCH...AGAINST 可在 MySQL 上
  编译并执行（索引由 candidate/application 的迁移在 migrate 阶段建立）。
"""
import pytest
from django.db import connection
from django.db.models import Q

from apps.candidate.models import Candidate
from apps.common.search import keyword_q


def test_keyword_q_empty_returns_blank_q():
    assert keyword_q('') == Q()
    assert keyword_q(None) == Q()


def test_keyword_q_like_path_compiles():
    # SQLite 下走 like；构造不应抛错
    q = keyword_q('john', 'name', 'phone')
    assert q.connector == Q.OR


def test_keyword_q_forces_like_on_sqlite():
    # 强制 like，验证仍是 __icontains 组合
    q = keyword_q('john', 'name', backend='like')
    sql = str(Candidate.objects.filter(q).query)
    assert 'LIKE' in sql.upper()


@pytest.mark.django_db(transaction=True)
def test_keyword_q_fulltext_on_mysql():
    if connection.vendor != 'mysql':
        pytest.skip('FULLTEXT 仅在 MySQL 验证')
    # 1) MATCH 路径应生成 MATCH...AGAINST SQL
    q = keyword_q('铁柱', 'name', backend='fulltext', model=Candidate)
    sql = str(Candidate.objects.filter(q).query)
    assert 'MATCH' in sql.upper() and 'AGAINST' in sql.upper()
    # 2) 真实中文召回（ngram）：插入含「赵铁柱」的记录，应能按「铁柱」命中
    Candidate.objects.create(id='ft-cand-001', name='赵铁柱', phone='13900000001', email='a@b.com')
    hit = list(Candidate.objects.filter(keyword_q('铁柱', 'name', backend='fulltext', model=Candidate)))
    assert any(c.id == 'ft-cand-001' for c in hit)
    # 3) 非匹配词不应命中
    miss = list(Candidate.objects.filter(keyword_q('不存在的词xyz', 'name', backend='fulltext', model=Candidate)))
    assert all(c.id != 'ft-cand-001' for c in miss)


@pytest.mark.django_db
def test_keyword_q_relation_field_falls_back_on_mysql():
    if connection.vendor != 'mysql':
        pytest.skip('关联字段回退路径仅在 MySQL 验证')
    from apps.application.models import Application

    q = keyword_q('x', 'code', 'candidate__name', 'position__title', model=Application)
    # code 用 MATCH 限定为 applications.code，candidate__name / position__title 回退 icontains，
    # 整体应可正常执行（验证 JOIN 场景下列名歧义已消除）
    assert list(Application.objects.filter(q)[:1]) == []
