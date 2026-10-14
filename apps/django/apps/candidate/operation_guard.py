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
``STATE_ACTION_GATE`` 为空表示**不限制**（与整体 fail-open 哲学一致）。
PRD 的「评分中全局置灰 / 审批中发起人独占」需要先把这两个状态补全到
``CandidateState``（当前枚举里没有），再调用 :func:`register_state_gate` 登记。
**在口径确认前不臆造映射** —— 宁可先不限，也不配错。
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

    与 :func:`is_operable` 同一套主体语义，但走 SQL 层：
    - 有锁定人 → 锁定人命中；
    - 无锁定人且开启兜底 → 职位权限人命中。

    二者是 OR 关系（一条记录要么有锁要么无锁，互斥），故直接并集即可。
    """
    from .lock import lock_owner_q, position_authority_q

    if _anon(user):
        return Q(pk__in=[])

    q = lock_owner_q(user)
    if ALLOW_POSITION_AUTHORITY_FALLBACK:
        no_lock = Q(formal_locked_by__isnull=True, temp_locked_by__isnull=True)
        legacy = position_authority_q(user) | Q(created_by=user) | Q(recruiter=user)
        # 无主简历交回角色级写范围（与 is_operable 的 ② 分支**必须**同语义）：
        #   write_scope_q 返回 None = 未配置写范围 = 不限制 -> 所有无锁定人的简历放行。
        # ⚠️ 不能写成 ``legacy | (scope_q or Q())``：空 Q() 是 OR 的单位元，Django 会
        #    把它化简掉，兜底形同虚设（已实测踩坑：无主简历被整批拒掉）。
        from apps.data_permission.enforcement import write_scope_q

        scope_q = write_scope_q(user, 'candidate', action=action)
        if scope_q is None:
            # 角色级未配置 -> legacy 主体（含无主简历，与 is_legacy_principal 同语义）
            ownerless = Q(created_by__isnull=True, recruiter__isnull=True, applications__isnull=True)
            q = q | (no_lock & (legacy | ownerless))
        else:
            # 角色级明确配置了写范围 -> 严格按它，不得被 legacy 放宽
            q = q | (no_lock & scope_q)
    return q
