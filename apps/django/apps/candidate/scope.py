"""候选人数据范围（行级 Scope）过滤 — 唯一真相源入口。

背景 (2026-10-08 审查):
    CandidateViewSet.get_queryset() 正确接了 scope_filter_q, 但一批辅助接口
    (合并 / 高级搜索 / 批量归档 / 批量分配 / 批量初筛 / CSV 导出 / 扩展简历字段)
    直接 `Candidate.objects...` 全表查, 只做角色或招聘类型校验, 完全绕过了
    L1-L4 部门/管理单元/SELF 范围。结果是「列表页看不到, 换个接口就能改」。

约束:
    本模块是候选人**读写的唯一入口**。任何新增接口都必须走 scoped_candidates(),
    不得再直接 `Candidate.objects.filter(...)`。
    例外只有: 系统内部任务 (Celery / 管理命令) 无 request, 此时显式传
    `bypass_scope=True` 并写明理由。
"""
from apps.candidate.models import Candidate
from apps.core.entity_scope import ENTITY_SCOPE, entity_scope_q
from apps.data_permission.enforcement import write_scope_q

# 与 CandidateViewSet 保持一致: Candidate 无 department 字段, 用推荐人部门间接 scope
SCOPE_FIELD = ENTITY_SCOPE['candidate']['scope_field']      # 'referrer__department'
CREATOR_FIELD = ENTITY_SCOPE['candidate']['creator_field']  # 'created_by'
ENTITY = 'candidate'


def candidate_scope_q(request, entity=ENTITY):
    """构造当前用户对候选人的行级可见范围 Q。"""
    return entity_scope_q(request, entity)


def scoped_candidates(request, qs=None, entity=ENTITY):
    """返回当前用户可见的候选人 queryset (已排除软删)。"""
    base = qs if qs is not None else Candidate.objects.all()
    return base.filter(deleted_at__isnull=True).filter(
        candidate_scope_q(request, entity=entity)
    )


def assert_candidates_visible(request, candidate_ids):
    """校验一批候选人 id 是否全部在当前用户可见范围内。

    返回**存在但越权**的 id 列表 (空列表 = 没有越权)。用于写操作前的越权拦截 ——
    合并/批量操作必须调用, 否则等于把改数据的权限开给全公司。

    注意: **完全不存在**的 id 不计入返回值。原因: 合并/批量接口历史上对不存在的
    id 是「跳过并继续」(service 里 `Candidate.DoesNotExist → continue`), 前端
    仍可能传入已失效的 id。若把"不存在"也判成越权 403, 会无谓打断正常流程;
    而"存在但越权"才是真正要拦的那一种, 必须拦。
    """
    ids = [i for i in candidate_ids if i is not None]
    if not ids:
        return []
    existing = set(
        Candidate.objects.filter(id__in=ids).values_list('id', flat=True)
    )
    if not existing:
        return []
    visible = set(
        scoped_candidates(request)
        .filter(id__in=existing)
        .values_list('id', flat=True)
    )
    return [str(i) for i in existing if i not in visible]


def assert_candidates_writable(request, candidate_ids, action: str = 'edit'):
    """校验一批候选人 id 是否都在当前用户的**写范围**内 (M07 长尾)。

    与 :func:`assert_candidates_visible` 的区别:
    - visible = 读范围 (可见即可见), 由 ``scoped_candidates`` / entity_scope_q 决定;
    - writable = 写范围 (可见 ≠ 可写), 由 ``data_permission.enforcement.write_scope_q``
      的 WRITE 规则决定 (ALL / NONE / OWNER / CUSTOM)。

    只读权限不足以改数据 —— 合并 / 批量筛选 / 批量推荐这类批量写入口必须同时过
    读范围与写范围两道关。此前批量接口只校验了读范围 (甚至直接
    ``Candidate.objects.get(pk=...)`` 全表取), 等于「列表看不到也能改」。

    语义与读侧保持一致:
    - 返回**存在但不可写**的 id 列表 (空列表 = 都可写);
    - 完全不存在的 id 不计入 (交由 service 的 ``DoesNotExist → continue`` 处理,
      避免把「已失效 id」误判成 403 而打断正常批量流程);
    - **未配置任何 WRITE 规则时返回空列表** (opt-in fail-open): 不配置写范围
      = 沿用既有功能权限, 不会因为上线本守卫就锁死所有批量写入口。
    """
    ids = [i for i in candidate_ids if i is not None]
    if not ids:
        return []
    existing = set(
        Candidate.objects.filter(id__in=ids).values_list('id', flat=True)
    )
    if not existing:
        return []

    # 写范围 Q; None = 无额外写限制 (fail-open)
    wq = write_scope_q(request.user, ENTITY, action=action)
    if wq is None:
        return []

    writable = set(
        Candidate.objects.filter(wq, id__in=existing).values_list('id', flat=True)
    )
    return [str(i) for i in existing if i not in writable]


def filter_writable_candidates(request, queryset, action: str = 'edit'):
    """把候选人 queryset 收窄到当前用户**可写**的子集 (批量入口取数用)。

    与 ``ensure_writable`` (单实例抛 403) 的区别: 本函数不抛异常, 返回收窄后的
    queryset —— 适合「批量里逐条判断, 不可写的跳过并回报」的既有响应壳语义。
    """
    wq = write_scope_q(request.user, ENTITY, action=action)
    if wq is None:
        return queryset
    return queryset.filter(wq)
