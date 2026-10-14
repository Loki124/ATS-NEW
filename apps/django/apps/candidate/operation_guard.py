"""简历**操作权**守卫（动态数据操作权限 · 四维求交）。

    allow = 主体(Who) ∧ 状态门(State) ∧ 数据范围(Which) ∧ 动作(What)

与既有守卫的分工（不重复造轮子）
--------------------------------
- ``data_permission.enforcement.ensure_writable``：管 **数据范围 + 动作白名单**，
  基于「角色 → 行级 WRITE 规则」。它是角色级的，表达不了下一项。
- **本模块**：管 **按记录主体（锁定人）+ 状态门**。锁定人是**记录属性而非角色** ——
  锁一转移，旧锁定人实时失效，零回收逻辑；这类判定角色级规则表达不了。

判定实现**一律复用** ``lock.py`` 的既有原语（``is_lock_owner`` / ``lock_owner_q`` /
``position_authority_q``），本模块只做策略组合 —— 否则「列表过滤」与「对象守卫」
两套实现必然漂移，而漂移的方向是权限漏洞。

过渡期兜底（重要：防上线即全线瘫痪）
------------------------------------
存量简历 ``formal_locked_by`` 绝大多数为 NULL —— 锁定引擎 2026-10-14 才上线，
存量追溯回填属 P6。若严格「非锁定人一律拒绝」，上线瞬间全体 HR 集体失去操作能力，
属于自伤式上线。故：

- **该简历无锁定人时，回退按职位权限人判定**（保证业务连续）；
- 一旦有锁定人（正式或未过期临时），严格按锁定人判定，职位权限人仅有查看权；
- 待 P6 存量回填完成，把 ``ALLOW_POSITION_AUTHORITY_FALLBACK`` 置 False 即收紧。

状态门
------
- **审批独占**（已实现）：候选人存在在途审批（``ApprovalFlow.status in
  (PENDING, IN_PROGRESS)``）时，**只有该审批的发起人**能操作 —— 连锁定人也不放行。
  理由：审批是对该简历处置权的临时移交，他人此时改动会与审批结论打架
  （批的是旧版本，改的是新版本）。终态（APPROVED/REJECTED/CANCELLED）自动解除。
- **评分中置灰**：**已作废**。评分自 2026-10 起平均耗时 < 10s（兵哥 2026-10-14
  确认），不存在需要置灰的窗口，故不实现「评分中全局置灰」。
- ``STATE_ACTION_GATE``：可按 ``Candidate.current_state`` 登记额外状态门
  （当前为空 = 不限制）。口径确认前不臆造映射 —— 宁可先不限，也不配错。
"""

from __future__ import annotations

import logging

from django.core.exceptions import PermissionDenied
from django.db.models import Q

logger = logging.getLogger(__name__)

#: 无锁定人的简历，是否回退按职位权限人判定（过渡期开关，见模块 docstring）
ALLOW_POSITION_AUTHORITY_FALLBACK = True

#: 状态门：简历状态 -> 该状态下**允许**的动作 key 集合。
#: 登记了某状态 = 该状态下只允许表内动作；未登记的状态不受状态门约束。
STATE_ACTION_GATE: dict[str, set[str]] = {}


def register_state_gate(state: str, allowed_actions) -> None:
    """登记状态门（供后续 PRD 特殊流程接线：评分中 / 审批中）。

    同名状态重复登记以**最后一次为准**，但会打 warning —— 门被悄悄覆盖意味着
    权限语义变化，必须留痕。
    """
    if state in STATE_ACTION_GATE:
        logger.warning('状态门被覆盖: state=%s（旧=%s 新=%s）', state, STATE_ACTION_GATE[state], allowed_actions)
    STATE_ACTION_GATE[state] = set(allowed_actions)


def _anon(user) -> bool:
    return user is None or not getattr(user, 'is_authenticated', False)


def _is_super_admin(user) -> bool:
    from apps.core.role_v2_query import is_super_admin

    return bool(is_super_admin(user))


def _action_enabled(action: str) -> bool:
    """动作白名单（fail-closed 于字典）：停用/未注册动作一律拒绝。

    字典表不可读时 ``action_registry`` 回退种子全集，不会误拒。
    """
    from apps.data_permission.action_registry import is_action_enabled

    return is_action_enabled(action)


# ============================ 审批独占（状态门） ============================

def in_flight_approval(candidate):
    """该候选人当前的在途审批流（无则 None）。

    「在途」= ``ApprovalFlow.status in (PENDING, IN_PROGRESS)``；终态不占用。
    以 ``created_at desc`` 取最新一条 —— 唯一性由创建侧校验保证（同一简历不可
    有两条在途），此处的 ``first()`` 只是防御性兜底。
    """
    from apps.resume_flow.models import ApprovalFlow

    if candidate is None or getattr(candidate, 'pk', None) is None:
        return None
    return (
        ApprovalFlow.objects
        .filter(candidate_id=candidate.pk, status__in=ApprovalFlow.IN_FLIGHT_STATUSES)
        .order_by('-created_at')
        .first()
    )


def is_approval_owner(user, candidate) -> bool:
    """``user`` 是否是该在途审批的**发起人**（``ApprovalFlow.created_by``）。

    发起人是审批的归属人 —— PRD 口径「审批中时仅发起人可以处理」。
    """
    flow = in_flight_approval(candidate)
    if flow is None or user is None or getattr(user, 'pk', None) is None:
        return False
    return str(getattr(flow, 'created_by_id', None) or '') == str(user.pk)


# ============================ 主体判定（复用 lock.py 原语） ============================

def is_lock_principal(user, candidate) -> bool:
    """对象级：``user`` 是否为该简历的锁定人（正式锁定人 ∪ 未过期的临时锁定人）。"""
    from .lock import is_lock_owner

    return is_lock_owner(candidate, user)


def is_position_principal(user, candidate) -> bool:
    """对象级：``user`` 是否为该简历所投职位的权限人（负责人/共享人/抢单人）。

    刻意复用 ``lock.position_authority_q``（Candidate 视角的既有实现），
    不另写一份 Position 视角查询 —— 避免两套判定漂移。
    """
    from .lock import position_authority_q
    from .models import Candidate

    return Candidate.objects.filter(position_authority_q(user), pk=candidate.pk).exists()


def is_legacy_principal(user, candidate) -> bool:
    """**过渡期**兜底主体：职位权限人 ∨ 创建人 ∨ 招聘负责人。

    为什么必须带上 created_by / recruiter：存量简历绝大多数既无锁定人也**没投过职位**
    （待分配池里躺着），只回退职位权限人等于「谁都不能操作」= 上线即瘫痪。
    且既有可见范围本就按 created_by/recruiter 过滤（普通 HR 只看自己的），
    「能看见却不能操作」是自相矛盾的半截权限。故过渡期与可见口径对齐。

    待 P6 存量锁定人回填完成后，本函数应从兜底链中移除。
    """
    if is_position_principal(user, candidate):
        return True
    uid = str(getattr(user, 'pk', None))
    if uid and str(getattr(candidate, 'created_by_id', None) or '') == uid:
        return True
    if uid and str(getattr(candidate, 'recruiter_id', None) or '') == uid:
        return True
    # 无主简历（无创建人、无招聘负责人、无投递）：维持既有行为 —— 这类数据本就
    # 不在任何人的可见范围内（scope 按 created_by/recruiter/职位过滤，NULL 不匹配），
    # 若在此一律拒绝只会把它变成谁都动不了的死数据，且**改变了接线前的既有行为**。
    return not has_any_relation(candidate)


def has_any_relation(candidate) -> bool:
    """该简历是否与**任何人**存在归属关系（创建人 / 招聘负责人 / 投递）。"""
    if getattr(candidate, 'created_by_id', None):
        return True
    if getattr(candidate, 'recruiter_id', None):
        return True
    from apps.application.models import Application

    return Application.objects.filter(candidate_id=candidate.pk).exists()


def lock_principal_q(user) -> Q:
    """列表级：锁定人过滤 Q（含临时锁时间窗），供 SQL 层过滤/批量置灰。"""
    from .lock import lock_owner_q

    return lock_owner_q(user)


def position_principal_q(user) -> Q:
    """列表级：职位权限人过滤 Q。"""
    from .lock import position_authority_q

    return position_authority_q(user)


def has_lock(candidate) -> bool:
    """该简历当前是否**有**锁定人（正式或临时，临时不论是否过期）。"""
    return bool(getattr(candidate, 'formal_locked_by_id', None) or getattr(candidate, 'temp_locked_by_id', None))


# ============================ 统一判定 ============================

def is_operable(user, candidate, action: str) -> bool:
    """能否对该简历执行该操作（主体 ∧ 状态门 ∧ 动作白名单）。

    不含数据范围（那部分由 ``ensure_writable`` 负责，两者**同时**调用才完整）。
    """
    if _anon(user):
        return False
    if candidate is None or getattr(candidate, 'pk', None) is None:
        return False
    if _is_super_admin(user):
        return True

    # 动作白名单：停用/未注册的动作为 0 容忍
    if not _action_enabled(action):
        logger.info('操作权拒绝(动作未启用): candidate=%s action=%s', candidate.pk, action)
        return False

    # 状态门：登记了该状态则只允许门内动作
    gate = STATE_ACTION_GATE.get(getattr(candidate, 'current_state', None))
    if gate is not None and action not in gate:
        logger.info('操作权拒绝(状态门): candidate=%s state=%s action=%s',
                    candidate.pk, getattr(candidate, 'current_state', None), action)
        return False

    # ---- 审批独占（优先级高于锁定人）----
    # 兵哥 2026-10-14 口径「审批中时仅发起人可以处理」：候选人存在在途审批时，
    # **只有该审批的发起人**（ApprovalFlow.created_by）能操作 —— 连锁定人也不放行。
    # 理由：审批是对该简历处置权的临时移交，发起人之外的任何人（包括锁定人）
    # 此时改动会与审批结论打架（批的是旧版本，改的是新版本）。
    flow = in_flight_approval(candidate)
    if flow is not None:
        if is_approval_owner(user, candidate):
            return True
        logger.info('操作权拒绝(审批独占): user=%s candidate=%s flow=%s action=%s',
                    user.pk, candidate.pk, flow.id, action)
        return False

    # ---- 分支 2：无在途审批 -> 常规主体判定 ----
    # 主体：有锁定人 -> 严格按锁定人（需求核心：只有锁定人能操作这条简历）
    if has_lock(candidate):
        if is_lock_principal(user, candidate):
            return True
        logger.info('操作权拒绝(非锁定人): user=%s candidate=%s action=%s', user.pk, candidate.pk, action)
        return False

    # 无锁定人（存量简历的常态）-> 过渡期兜底：
    #   ① legacy 主体（职位权限人 ∪ 创建人 ∪ 招聘负责人）命中即可；
    #   ② 连这些都没有（无主简历：created_by/recruiter 全 NULL，历史上确有其数据）
    #      -> 主体层**不表态**，交回角色级写范围决定（与 ensure_writable 的
    #         fail-open 哲学一致：无 WRITE 规则配置则不限制）。
    #      这样既不会因为新权限上线而把存量简历变成谁都动不了的死数据，
    #      也不会在角色级已经拒绝时越权放行。
    if ALLOW_POSITION_AUTHORITY_FALLBACK:
        from apps.data_permission.enforcement import is_writable, write_scope_q

        wq = write_scope_q(user, 'candidate', action=action)
        if wq is not None:
            # 角色级**明确**配置了写范围 -> 严格按它，legacy 主体不得绕过。
            # 反例（已实测踩坑）：规则配 scope=NONE（明确不可写），却被
            # 「我是创建人」兜底放行 —— 那是把收紧的配置反向放宽，属越权。
            if is_writable(user, 'candidate', candidate, action=action):
                return True
        elif is_legacy_principal(user, candidate):
            # 角色级未配置（None = 不限制）-> 由 legacy 主体决定，与既有可见口径对齐
            return True

    logger.info('操作权拒绝(非锁定人): user=%s candidate=%s action=%s', user.pk, candidate.pk, action)
    return False


def ensure_operable(user, candidate, action: str) -> None:
    """操作权守卫：不可操作抛 PermissionDenied（DRF 自动转 403）。

    与 ``ensure_writable`` **并列**调用：前者管「你与这条记录的关系」，
    后者管「这条记录在你角色的写范围内」。缺任一都是半截权限。
    """
    if is_operable(user, candidate, action):
        return
    raise PermissionDenied(
        f'无操作权限：仅该简历的锁定人可执行 {action}'
        f'（当前锁定人：{getattr(candidate, "formal_locked_by_id", None) or "无"}）'
    )


def operable_q(user, action: str) -> Q:
    """列表级：可对该动作操作的简历集合（供前端批量置灰 / 批量操作预过滤）。

    与 :func:`is_operable` **逐分支同构**（这是两者不漂移的唯一保证方式）：

    ==========  ===============================================  ==========
    分支         条件                          放行集合
    ==========  ===============================================  ==========
    审批独占     存在在途审批                   仅该审批 created_by
    有锁定人     formal/temp 锁存在             锁定人（严格）
    过渡兜底     无锁定人 + 角色级配了写范围      严格按写范围
    过渡兜底     无锁定人 + 角色级未配            legacy 主体 ∪ 无主简历
    ==========  ===============================================  ==========

    ⚠️ 三处已踩坑，勿改回：
    1. 审批独占写成 ``if 有在途审批: return Q(pk__in=发起人)`` → 无关候选人全被误杀；
    2. 兜底写成 ``legacy | (scope_q or Q())`` → 空 Q() 是 OR 单位元会被 Django 化简，
       兜底形同虚设；
    3. 审批独占与主体判定写成纯并集 ``(不在途) | ...`` → 会让无审批且非锁定人的简历
       全部放行，把主体判定架空（比误杀更危险：等于无权限）。
    """
    from apps.resume_flow.models import ApprovalFlow

    from .lock import lock_owner_q, position_authority_q

    if _anon(user):
        return Q(pk__in=[])

    in_flight = ApprovalFlow.objects.filter(
        status__in=ApprovalFlow.IN_FLIGHT_STATUSES,
    ).values('candidate_id')

    # ---- 分支 1：审批独占（优先级最高，**替代**主体判定）----
    # 存在在途审批 → 仅该审批发起人可操作。发起人**不受锁定人限制**：
    # 审批是对该简历处置权的临时移交，发起人拿到的是「这次审批期间的全权」。
    approval_exclusive = Q(pk__in=ApprovalFlow.objects.filter(
        status__in=ApprovalFlow.IN_FLIGHT_STATUSES, created_by=user,
    ).values('candidate_id'))

    # ---- 分支 2：无在途审批 → 常规主体判定 ----
    not_in_flight = ~Q(pk__in=in_flight)

    #   2a 有锁定人 —— 严格按锁定人
    has_lock_q = Q(formal_locked_by__isnull=False) | Q(temp_locked_by__isnull=False)
    locked_pass = has_lock_q & lock_owner_q(user)

    #   2b 无锁定人的过渡兜底
    no_lock = ~has_lock_q
    if ALLOW_POSITION_AUTHORITY_FALLBACK:
        from apps.data_permission.enforcement import write_scope_q

        legacy = position_authority_q(user) | Q(created_by=user) | Q(recruiter=user)
        scope_q = write_scope_q(user, 'candidate', action=action)
        if scope_q is None:
            ownerless = Q(created_by__isnull=True, recruiter__isnull=True, applications__isnull=True)
            unlocked_pass = legacy | ownerless
        else:
            unlocked_pass = scope_q
    else:
        unlocked_pass = Q(pk__in=[])

    # 顶层 OR：两个分支互斥（有在途审批 / 无在途审批），故并集即为全语义。
    # ⚠️ 不能写成 ``(不在途) | (在途且发起人是我) & 主体`` 之类的形式 ——
    #    「不在途」单独一项会让无审批且非锁定人的简历全部放行（主体判定被架空）。
    return approval_exclusive | (not_in_flight & (locked_pass | (no_lock & unlocked_pass)))
