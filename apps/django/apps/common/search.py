"""统一关键词搜索工具（#38）。

历史：原先各 app 手写 ``Q(name__icontains=kw) | ...``，既重复又难统一升级。
现集中到 ``keyword_q()``，并落地「方案 A」的 MySQL FULLTEXT 索引级优化：

- ``SEARCH_BACKEND = 'auto'``（默认）：MySQL 上自动走 FULLTEXT（``MATCH...AGAINST``），
  其余数据库（SQLite/Postgres）回退到 ``__icontains``。
- ``SEARCH_BACKEND = 'fulltext'``：强制 FULLTEXT（仅 MySQL 有效，否则该路径会报「无 FULLTEXT 索引」）。
- ``SEARCH_BACKEND = 'like'``：强制 ``__icontains``（灰度开关 / 回滚用）。

注意：
- 关联字段（含 ``__``，如 ``candidate__name``）无法用原生 ``MATCH`` 跨 JOIN 遍历，
  在 fulltext 模式下回退到 ``__icontains``，搜索仍正确，只是这些字段走 LIKE。
- fulltext 模式依赖对应列上的 FULLTEXT 索引（见 candidate / application 的迁移），
  且列须用基表名限定（``MATCH(`table`.`col`)``），否则 JOIN 场景下与其它表同名列冲突。
- ``model`` 参数用于限定基表名；建议调用方传入当前 QuerySet 的 model。
"""
from django.conf import settings
from django.db import connection
from django.db.models import Q, BooleanField
from django.db.models.expressions import RawSQL


class _FullTextExpr(RawSQL):
    """可进入 Q/filter 的 FULLTEXT 条件表达式。

    Django 的 ``RawSQL`` 默认 ``conditional = False``，不能直接用于 ``filter()``。
    ``MATCH(... ) AGAINST (...)`` 在 MySQL 中返回浮点相关性分数，``> 0`` 即命中；
    标记 ``conditional = True`` 并自带 ``> 0``，使 Django 将其作为布尔条件输出。
    """

    conditional = True

    def __init__(self, sql, params):
        super().__init__(sql, params, output_field=BooleanField())


def _resolve_backend(backend):
    eff = backend or getattr(settings, 'SEARCH_BACKEND', 'auto')
    if eff == 'auto':
        eff = 'fulltext' if connection.vendor == 'mysql' else 'like'
    return eff


def _like_q(keyword, *fields):
    q: Q = Q()
    for field in fields:
        q |= Q(**{f'{field}__icontains': keyword})
    return q


def _fulltext_q(keyword, *fields, model=None):
    q: Q = Q()
    for field in fields:
        # 关联字段无法用 MATCH 跨 JOIN，且不接受非安全标识符 —— 回退 LIKE
        if '__' in field or not field.isidentifier():
            q |= Q(**{f'{field}__icontains': keyword})
            continue
        if model is not None:
            col = f'`{model._meta.db_table}`.`{field}`'
        else:
            col = f'`{field}`'
        q |= Q(_FullTextExpr(f'MATCH({col}) AGAINST (%s) > 0', [keyword]))
    return q


def keyword_q(keyword: str, *fields: str, backend: str | None = None, model=None) -> Q:
    """返回对多个字段做 OR 匹配的 ``Q`` 对象。

    Args:
        keyword: 搜索词；为空/None 时返回空 ``Q()``（即不过滤）。
        *fields: 字段路径，如 ``'name'``、``'candidate__name'``。
        backend: 强制后端（'fulltext' / 'like'）；缺省读 ``settings.SEARCH_BACKEND``。
        model: 当前 QuerySet 的 model（用于限定 FULLTEXT 基表名，避免 JOIN 同名列冲突）。

    Returns:
        ``Q``: 多字段 OR 组合（fulltext 或 like，由后端决定）。
    """
    if not keyword:
        return Q()
    if _resolve_backend(backend) == 'fulltext':
        return _fulltext_q(keyword, *fields, model=model)
    return _like_q(keyword, *fields)
