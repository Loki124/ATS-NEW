"""统一关键词搜索工具（#38：收口散落的 ``__icontains`` 模糊搜索）。

各 app 普遍手写 ``Q(name__icontains=kw) | Q(code__icontains=kw) | ...``，既重复
又难以统一升级到 FULLTEXT/ngram/ES。集中到本模块，后续做 MySQL FULLTEXT + ngram
或 ES 时只需改这一处。

注意：当前实现仍用 ``__icontains``（B-Tree 索引失效、大表线性扫），仅做**代码收口**；
真正的索引级优化属于基建迁移（MySQL ngram FULLTEXT / ES），见 TODO #38 说明，
需 DBA / infra 决策，不在本次改动范围。
"""
from django.db.models import Q


def keyword_q(keyword: str, *fields: str) -> Q:
    """返回对多个字段做 OR 模糊匹配的 ``Q`` 对象。

    Args:
        keyword: 搜索词；为空/None 时返回空 ``Q()``（即不过滤）。
        *fields: 字段路径，如 ``'name'``、``'candidate__name'``。

    Returns:
        ``Q``: 各字段 ``field__icontains=keyword`` 的 OR 组合。
    """
    if not keyword:
        return Q()
    q: Q = Q()
    for field in fields:
        q |= Q(**{f'{field}__icontains': keyword})
    return q
