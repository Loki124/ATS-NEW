"""keyword_q 搜索后端测试。

2026-10-15 起开发/测试统一 MySQL（不再默认 SQLite），本地与 CI 均走 fulltext 路径；
SQLite 仅作 DB_ENGINE=sqlite 的显式逃生口。此前本文件靠"本地默认 SQLite 走 like、
CI MySQL 走 fulltext"双轨，现已统一。

2026-10-11 去掉方法级 django_db(transaction=True)：
本文件不依赖 transaction.on_commit，也不走 save() 内 select_for_update 自动补号，
普通 django_db 已把整个测试包在一个原子事务里，语义足够；而 transaction=True
会让写入真实提交且不回滚，本文件在业务表留下的数据残留到后续用例，
曾导致 dynamic_field / process 等模块出现上百个看不懂的断言失败。

例外：`test_keyword_q_fulltext_on_mysql` 必须 transaction=True + 显式 commit ——
InnoDB FULLTEXT 对未提交事务不可见，只有提交后的行才能被 MATCH 命中
（与生产 create 提交后索引可见的行为一致），用例末尾再 delete+commit 清理，不留残留。
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
    # 2) 真实中文召回（ngram）：InnoDB FULLTEXT 对未提交事务不可见, 必须提交后命中
    #    （与生产 create 提交后索引可见的行为一致）。
    Candidate.objects.create(id='ft-cand-001', name='赵铁柱', phone='13900000001', email='a@b.com')
    connection.commit()
    try:
        hit = list(Candidate.objects.filter(keyword_q('铁柱', 'name', backend='fulltext', model=Candidate)))
        assert any(c.id == 'ft-cand-001' for c in hit)
        # 3) 非匹配词不应命中
        miss = list(Candidate.objects.filter(keyword_q('不存在的词xyz', 'name', backend='fulltext', model=Candidate)))
        assert all(c.id != 'ft-cand-001' for c in miss)
    finally:
        # 显式清理并提交, 避免残留到后续用例（与文件约定一致：本文件不留业务数据）
        Candidate.objects.filter(id='ft-cand-001').delete()
        connection.commit()


@pytest.mark.django_db
def test_keyword_q_relation_field_falls_back_on_mysql():
    if connection.vendor != 'mysql':
        pytest.skip('关联字段回退路径仅在 MySQL 验证')
    from apps.application.models import Application

    q = keyword_q('x', 'code', 'candidate__name', 'position__title', model=Application)
    # code 用 MATCH 限定为 applications.code，candidate__name / position__title 回退 icontains，
    # 整体应可正常执行（验证 JOIN 场景下列名歧义已消除）
    assert list(Application.objects.filter(q)[:1]) == []