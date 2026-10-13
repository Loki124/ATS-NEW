"""简历**正式锁定人**规则引擎。

依据《简历模块及特殊简历审批流程调整需求说明》(2026-10-14) 与兵哥 2026-10-14 口径：

- 职位权限人 = 职位负责人 ``Position.owner`` ∪ 职位共享人 ``Position.assistants``
  ∪ 简历抢单人 ``Application.grabbed_by``（投递级）。
- 正式锁定人由**规则自动确定与流转，任何角色不可手动变更**，故本模块
  （经 :func:`apply_formal_lock`）是写入 ``formal_locked_by`` 的**唯一入口**；
  业务 view / serializer 不得直接改该字段。

核心不变量（必须守住，否则权限链断裂）
--------------------------------------
**正式锁定人必须是目标职位的权限人之一。**

理由：锁定人拿到的是「操作权」，可见范围给的是「看得到」。若锁定人不在职位
权限人集合内，会出现两种残废态 —— ① 看得到却不能操作（共享人干瞪眼）；
② 能操作却看不到（权限越界）。因此所有兜底分支（HRBP / 内推兜底）算出的
人选**必须先过权限人校验**，不通过就继续降级，最终一律回退 ``Position.owner``
（owner 恒为权限人，是唯一不会失效的兜底）。

与 :mod:`apps.candidate.lock` 的分工
------------------------------------
``lock.py`` 只提供**判定与服务原语**（谁算锁定人、临时锁授予/回收、乐观锁）；
本模块提供**规则**（锁定人应该是谁）。判定可独立复用，规则只在业务事件
（分配 / 入库 / 激活 / 转推）时由本模块驱动。

HRBP 的真实落点（2026-10-14 核实，勿凭印象）
-------------------------------------------
HRBP **不是模型字段**，而是 ``Demand`` 上的动态字段 ``resource='Demand',
field_key='hrbp'``（PERSON 型，值落 ``DynamicFieldValue.value`` JSON）。
且 dev 库存量 ``DynamicFieldValue`` 中 hrbp **全为空** —— 即 HRBP 兜底在真实
数据上大概率落空。故实现为「动态字段 → 回退 owner」两级，且**解析失败一律
返回 None 而非臆造**（fail-closed 于该分支，再由 owner 兜底整体不变量）。

内推兜底第 1 级「绑定的内推招聘专家」
------------------------------------
当前 ``Referral`` 模型**没有**该字段（已核实 ``apps/referral/models.py``
仅有 referrer / candidate / status 等）。故第 1 级以**可插拔 provider** 形式
预留：``REFERRAL_EXPERT_PROVIDER`` 由 referral 模块在字段落地后注入；未注入时
该级**明确跳过**（而非伪造一个"专家"顶上）—— 不假装实现是硬要求。
"""

from __future__ import annotations

from dataclasses import dataclass

from . import lock as lock_service

# ---------------------------------------------------------------- 常量

#: HRBP 动态字段定位（已核实：resource='Demand', field_key='hrbp'）
HRBP_RESOURCE = 'Demand'
HRBP_FIELD_KEY = 'hrbp'

#: 内推兜底第 1 级 provider 注入点。
#: 签名 ``(candidate, position) -> User | None``；referral 模块字段落地后赋值。
#: 为 None 时该级跳过 —— 宁可少一级兜底，也不伪造"专家"。
REFERRAL_EXPERT_PROVIDER = None


class LockReason:
    """正式锁定人决策原因码（写入审计 detail.reason，用于事后追溯"凭什么是他"）。"""

    # 分配场景（PRD 4.2 优先级，自上而下）
    ASSIGNER_IS_AUTHORITY = 'ASSIGNER_IS_AUTHORITY'              # 分配人是新职位权限人
    PREVIOUS_IS_AUTHORITY = 'PREVIOUS_IS_AUTHORITY'              # 原锁定人是新职位权限人 → 继承
    REFERRAL_EXPERT = 'REFERRAL_EXPERT'                          # 内推兜底 L1 绑定招聘专家
    REFERRAL_PREV_TEAM_HRBP = 'REFERRAL_PREV_TEAM_HRBP'          # 内推兜底 L2 原团队 HRBP
    POSITION_HRBP = 'POSITION_HRBP'                              # 内推兜底 L3 / 常规：职位 HRBP
    POSITION_OWNER = 'POSITION_OWNER'                            # 最终兜底：职位负责人（恒权限人）

    # 人才库场景（按 pool_kind）
    POOL_EXCLUSIVE_OWNER = 'POOL_EXCLUSIVE_OWNER'
    POOL_PERSONAL_OWNER = 'POOL_PERSONAL_OWNER'
    POOL_ONBOARD_OWNER = 'POOL_ONBOARD_OWNER'
    POOL_NO_LOCK = 'POOL_NO_LOCK'                                # 共享/内推/通用库：无锁定人

    # 无法判定
    NO_POSITION_NO_LOCK = 'NO_POSITION_NO_LOCK'
    NO_AUTHORITY_NO_LOCK = 'NO_AUTHORITY_NO_LOCK'


@dataclass(frozen=True)
class LockDecision:
    """一次正式锁定人决策结果。

    ``user`` 为 None 表示"按规则此人/此场景不该有正式锁定人"；
    ``applied`` 仅 :func:`apply_formal_lock` / :func:`apply_pool_lock` 返回时为 True。
    """

    user: object
    reason: str
    applied: bool = False


# ---------------------------------------------------------------- 职位权限人

def position_authority_ids(position) -> set:
    """目标职位的权限人 id 集合（str 形式，规避 int/nanoid 主键类型差异）。

    职位负责人 ∪ 职位共享人 ∪ 该职位下所有投递的抢单人。
    """
    if position is None or getattr(position, 'pk', None) is None:
        return set()
    from apps.application.models import Application

    ids = set()
    owner_id = getattr(position, 'owner_id', None)
    if owner_id:
        ids.add(str(owner_id))
    # 共享人（M2M）
    ids.update(str(pk) for pk in position.assistants.values_list('pk', flat=True))
    # 抢单人（投递级：该职位下所有已认领投递）
    ids.update(
        str(pk) for pk in Application.objects
        .filter(position_id=position.pk)
        .exclude(grabbed_by__isnull=True)
        .values_list('grabbed_by_id', flat=True)
    )
    ids.discard('None')
    return ids


def is_position_authority(position, user) -> bool:
    """对象级：``user`` 是否为该职位的权限人（负责人 / 共享人 / 抢单人）。"""
    if user is None or getattr(user, 'pk', None) is None:
        return False
    return str(user.pk) in position_authority_ids(position)


# ---------------------------------------------------------------- HRBP / 人员解析

def _coerce_user_id(value):
    """从动态字段 PERSON 值里抽取用户 id。

    PERSON 值结构尚**无生产样例**（dev 库 hrbp 全空），故按常见形态容错解析：
    标量 / ``[x]`` / ``{'id'|'user_id'|'value': x}``。解析不出返回 None ——
    绝不猜结构、绝不回退成"随便一个人"。
    """
    if value is None:
        return None
    if isinstance(value, dict):
        for key in ('id', 'user_id', 'value', 'user'):
            inner = value.get(key)
            if isinstance(inner, (str, int)) and str(inner).strip():
                return str(inner)
            if isinstance(inner, dict):
                nested = _coerce_user_id(inner)
                if nested:
                    return nested
        return None
    if isinstance(value, (list, tuple)):
        return _coerce_user_id(value[0]) if value else None
    if isinstance(value, (str, int)):
        text = str(value).strip()
        return text or None
    return None


def _get_user_by_id(user_id):
    """按 id 取用户；不存在 / 已离职软删一律返回 None（fail-closed）。"""
    if not user_id:
        return None
    from apps.core.models import User

    return User.objects.filter(pk=user_id).first()


def resolve_dynamic_person(resource: str, entity_id, field_key: str):
    """读取实体上的 PERSON 型动态字段并解析为 User。读不到返回 None。"""
    if not entity_id:
        return None
    from apps.dynamic_field.models import DynamicFieldValue

    row = DynamicFieldValue.objects.filter(
        resource=resource, entity_id=str(entity_id), field_key=field_key,
    ).only('value').first()
    if row is None:
        return None
    return _get_user_by_id(_coerce_user_id(row.value))


def resolve_hrbp(position):
    """职位的 HRBP：``Demand`` 动态字段 hrbp → 取不到返回 None。

    **不做 owner 兜底** —— 兜底是决策链（:func:`decide_formal_lock`）的职责，
    本函数保持"只回答 HRBP 是谁"的单一语义，便于审计区分是 HRBP 还是 owner 兜底。
    """
    demand_id = getattr(position, 'demand_id', None)
    if not demand_id:
        return None
    return resolve_dynamic_person(HRBP_RESOURCE, demand_id, HRBP_FIELD_KEY)


# ---------------------------------------------------------------- 人才库锁定

#: pool_kind → 锁定规则。'OWNER' = 库归属人为锁定人；'NONE' = 公共资源池，无锁定人。
_POOL_KIND_RULE = {
    'CAMPUS_EXCLUSIVE': ('OWNER', LockReason.POOL_EXCLUSIVE_OWNER),
    'PERSONAL': ('OWNER', LockReason.POOL_PERSONAL_OWNER),
    'ONBOARD': ('OWNER', LockReason.POOL_ONBOARD_OWNER),
    'CAMPUS_SHARED': ('NONE', LockReason.POOL_NO_LOCK),
    'REFERRAL': ('NONE', LockReason.POOL_NO_LOCK),
    'GENERAL': ('NONE', LockReason.POOL_NO_LOCK),
}


def decide_pool_lock(entry):
    """人才库条目的正式锁定人决策（PRD 人才库 7 类 / pool_kind 归属维度）。

    - 独享库 / 个人库 / 入职库 → 库归属人（``pool_owner``）；
    - 共享库 / 内推库 / 通用库 → **无锁定人**（公共资源池，靠可见范围 + 临时锁/抢单）。
    - 归属人为空（数据缺失）→ 视为无锁定人，绝不退回"随便一个人"。
    """
    rule = _POOL_KIND_RULE.get(getattr(entry, 'pool_kind', None))
    if rule is None:
        return LockDecision(None, LockReason.POOL_NO_LOCK)
    mode, reason = rule
    if mode == 'NONE':
        return LockDecision(None, reason)
    owner = getattr(entry, 'pool_owner', None)
    if owner is None or getattr(owner, 'pk', None) is None:
        return LockDecision(None, LockReason.POOL_NO_LOCK)
    return LockDecision(owner, reason)


# ---------------------------------------------------------------- 内推兜底

def referral_fallback(candidate, position):
    """内推来源 3 级兜底（PRD 内推规则）：

    L1 绑定的内推招聘专家（provider 未注入 → 跳过）
    L2 原团队 HRBP（简历原所属职位的 HRBP）
    L3 职位 HRBP（目标职位）
    每级算出的候选**必须**是目标职位权限人，否则继续降级。
    """
    authority = position_authority_ids(position)

    if REFERRAL_EXPERT_PROVIDER is not None:
        expert = REFERRAL_EXPERT_PROVIDER(candidate, position)
        if expert is not None and str(expert.pk) in authority:
            return expert, LockReason.REFERRAL_EXPERT

    prev_hrbp = _previous_team_hrbp(candidate)
    if prev_hrbp is not None and str(prev_hrbp.pk) in authority:
        return prev_hrbp, LockReason.REFERRAL_PREV_TEAM_HRBP

    hrbp = resolve_hrbp(position)
    if hrbp is not None and str(hrbp.pk) in authority:
        return hrbp, LockReason.POSITION_HRBP

    return None, None


def _previous_team_hrbp(candidate):
    """原团队 HRBP：取该候选人**最近一次**投递所属职位的 HRBP。

    无历史投递 / 该职位无 demand / hrbp 未录 → None（不臆造）。
    """
    if candidate is None or getattr(candidate, 'pk', None) is None:
        return None
    from apps.application.models import Application

    app = (
        Application.objects
        .filter(candidate_id=candidate.pk)
        .exclude(position__isnull=True)
        .order_by('-created_at')
        .select_related('position')
        .first()
    )
    if app is None:
        return None
    return resolve_hrbp(app.position)


# ---------------------------------------------------------------- 主决策

def decide_formal_lock(candidate, *, position=None, assigned_by=None):
    """按 PRD 4.2 优先级决定正式锁定人（纯读，不写库）。

    L1 分配人是新职位权限人            → 分配人
    L2 原正式锁定人是新职位权限人      → 继承（保持原锁定人）
    L3 内推来源 → 3 级兜底链
    L4 职位 HRBP
    L5 职位负责人 owner（恒权限人，唯一不会失效的兜底）

    ``position`` 为 None（未分配至职位）→ 返回 None 且**不改动**现有锁定人
    （避免"未分配"误清空已生效的锁定）。
    """
    if position is None or getattr(position, 'pk', None) is None:
        return LockDecision(None, LockReason.NO_POSITION_NO_LOCK)

    authority = position_authority_ids(position)

    # L1 分配人（显式传入优先，否则取简历上的 assigned_by）
    assigner = assigned_by if assigned_by is not None else getattr(candidate, 'assigned_by', None)
    if assigner is not None and getattr(assigner, 'pk', None) is not None:
        if str(assigner.pk) in authority:
            return LockDecision(assigner, LockReason.ASSIGNER_IS_AUTHORITY)

    # L2 继承
    previous = getattr(candidate, 'formal_locked_by', None)
    if previous is not None and getattr(previous, 'pk', None) is not None:
        if str(previous.pk) in authority:
            return LockDecision(previous, LockReason.PREVIOUS_IS_AUTHORITY)

    # L3 内推 3 级兜底
    if getattr(candidate, 'referrer_id', None):
        user, code = referral_fallback(candidate, position)
        if user is not None:
            return LockDecision(user, code)

    # L4 职位 HRBP
    hrbp = resolve_hrbp(position)
    if hrbp is not None and str(hrbp.pk) in authority:
        return LockDecision(hrbp, LockReason.POSITION_HRBP)

    # L5 最终兜底 owner
    owner = getattr(position, 'owner', None)
    if owner is not None and getattr(owner, 'pk', None) is not None:
        return LockDecision(owner, LockReason.POSITION_OWNER)

    return LockDecision(None, LockReason.NO_AUTHORITY_NO_LOCK)


# ---------------------------------------------------------------- 写入口

def _same_user(a, b) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return str(getattr(a, 'pk', None)) == str(getattr(b, 'pk', None))


def _apply(candidate, decision, *, actor=None, allow_clear: bool):
    """落库公共逻辑：写 formal_locked_by → bump 乐观锁 → 写审计。"""
    previous = candidate.formal_locked_by
    if _same_user(previous, decision.user):
        return LockDecision(decision.user, decision.reason, applied=False)
    if decision.user is None and not allow_clear:
        # 无法保证不变量的"清空"一律拒绝，宁可维持现状也不制造无主简历
        return LockDecision(previous, decision.reason, applied=False)

    from .audit import record_lock_change

    lock_service.set_formal_lock(candidate, decision.user)
    lock_service.bump_lock_version(candidate)
    record_lock_change(
        candidate,
        from_user=previous,
        to_user=decision.user,
        reason=decision.reason,
        actor=actor,
        kind='FORMAL',
    )
    return LockDecision(decision.user, decision.reason, applied=True)


def apply_formal_lock(candidate, *, position=None, assigned_by=None, actor=None):
    """分配/转推等场景下**重算并写入**正式锁定人。

    这是 ``formal_locked_by`` 的唯一写入口（PRD：不可手动变更）。
    决策为 None（无职位 / 无权限人）时**保持原值不清空**。
    """
    decision = decide_formal_lock(candidate, position=position, assigned_by=assigned_by)
    return _apply(candidate, decision, actor=actor, allow_clear=False)


def apply_pool_lock(candidate, entry, *, actor=None):
    """人才库入库 / 激活场景下的锁定联动。

    与分配场景不同：共享库 / 内推库 / 通用库按 PRD **确属无锁定人**，
    故此处允许清空（``allow_clear=True``）。
    """
    decision = decide_pool_lock(entry)
    return _apply(candidate, decision, actor=actor, allow_clear=True)


# ---------------------------------------------------------------- 临时锁场景

def maybe_grant_temp_lock(candidate, actor, *, provider_id=None):
    """PRD 临时锁场景：操作人 ≠ 提供人时，授予操作人 72h 临时锁定。

    适用于：① 上传时上传人 ≠ 提供人；② 人才库重新激活时激活人 ≠ 提供人。
    ``provider_id`` 缺省取 ``candidate.referrer_id``。

    返回是否授予（同一个人 / 匿名 → False，不产生噪声审计）。
    """
    if actor is None or not getattr(actor, 'is_authenticated', False):
        return False
    referrer_id = provider_id if provider_id is not None else getattr(candidate, 'referrer_id', None)
    if referrer_id and str(referrer_id) == str(actor.pk):
        return False
    if not referrer_id:
        # 无提供人时无"抢别人简历"风险，无需临时锁（查看由可见范围控制）
        return False
    lock_service.grant_temp_lock(candidate, actor)
    return True
