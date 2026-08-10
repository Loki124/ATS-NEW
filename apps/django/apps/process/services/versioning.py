"""流程版本管理服务（PRD v4 §9.2 BR-101~BR-105）

业务规则：
- BR-101: 流程被至少一个职位需求引用后，配置修改将生成新版本
- BR-102: 已在跑的候选人走创建时的版本
- BR-103: 历史版本只读
- BR-104: 支持历史候选人"升版本"到最新版本
- BR-105: 流程无草稿态，配置即时生效
- BR-106: 流程无停用态，只能归档
"""
from __future__ import annotations

import logging
from copy import deepcopy
from typing import List, Tuple

from django.db import transaction
from django.db.models import Count, Max, Q
from django.utils import timezone

logger = logging.getLogger(__name__)


def is_process_referenced(process) -> bool:
    """判断流程是否被职位需求引用"""
    return process.demands.filter(deleted_at__isnull=True).exists()


@transaction.atomic
def archive_process(process, actor=None) -> dict:
    """归档整条流程线（替代停用，BR-106 + 产品 Q5 裁定）。

    **作用对象是整条 ``code`` 线，不是单个版本行**（Q5）。只归档 ``is_latest=True``
    那一行会造出一个无法向用户解释的状态：列表页（``filter(is_latest=True)``）显示
    「已归档」，而 ``list_process_versions`` 里的历史版本仍是 ``ENABLED``；新建 Demand
    时该选哪一行无解。BR-106 的立法目的是「让这条流程不再被新需求选用」，作用域天然
    是整条线。

    归档只关闭入口，**不影响在跑的业务**：已引用的 Demand/Position 继续正常运行
    （FK 是 ``PROTECT``，行不会消失），在跑的 Application 继续跑完（BR-102 红线）。

    **两个分支必须返回同一套 key 与同一套类型**（V7 回归钉子）：改这里之前先看
    ``test_archive_returns_identical_shape_on_both_branches``。历史缺陷是早退分支
    返回 ``reference_count`` 为 **bool**（``is_process_referenced()`` 的返回值）且
    缺 ``archived_at`` 键，调用方按 int 用会静默拿到 ``True``/``False``。

    Args:
        process: 该流程线上的任意一行 RecruitmentProcess（用它的 ``code`` 定位整条线）。
        actor: 操作人，仅用于日志。

    Returns:
        - ``archived``: bool，恒为 True（幂等语义：重复归档也算已归档）
        - ``reference_count``: **int**，live Demand 引用数
        - ``archived_at``: str | None，ISO 串；重复归档时是**首次**归档时间
        - ``archived_version_count``: int，**本次**真正被改写的版本行数（重复归档为 0）
    """
    from ..models import RecruitmentProcess

    now = timezone.now()
    # 软删行不参与归档：它已经不在任何入口里，改它的 status 只会污染审计。
    # .update() 是原子批量写，绕过 auto_now，故 updated_at 必须显式给值。
    archived_count = (
        RecruitmentProcess.objects
        .filter(code=process.code, deleted_at__isnull=True)
        .exclude(status='ARCHIVED')
        .update(status='ARCHIVED', archived_at=now, updated_at=now)
    )

    # .update() 不回写内存实例。调用方（views.archive）拿 ``instance`` 直接过序列化器，
    # 不刷新会把「已归档」渲染成 ENABLED——响应体自相矛盾。
    process.refresh_from_db()

    logger.info(
        'Process line %s archived by %s (%d version row(s) affected)',
        process.code, actor, archived_count,
    )

    return {
        'archived': True,
        'reference_count': process.reference_count,
        'archived_at': process.archived_at.isoformat() if process.archived_at else None,
        'archived_version_count': archived_count,
    }


def _compute_next_version_seq(process) -> int:
    """纯计算：给出 ``process`` 所在流程线（同 ``code``）的下一个 ``version_seq``。

    ⚠️ **刻意不过滤软删**：C1 ``uniq_process_code_version_seq`` 是无条件唯一约束，
    软删行同样占位。若这里只统计 live 行，克隆一条曾被软删过版本的流程线会算出已被
    占用的 seq，直接撞 C1 抛 ``IntegrityError``。

    ⚠️ **取全线 MAX 而非 ``process.version_seq + 1``**：允许从任意历史版本发起克隆
    （例如线上已有 seq=1/2，从 seq=1 那行克隆）。用 ``+1`` 会算出 2 → 撞 C1；
    取 MAX+1 得 3，才是「追加一个新版本」的正确语义。
    ``max(..., process.version_seq)`` 兜底传入的是尚未落库的内存实例的情形。

    并发下两个 clone 可能算出同一个 seq：这不会静默腐化——C1 会让后到者
    ``IntegrityError``（响亮失败），与 C3' 的兜底策略一致。

    Args:
        process: 当前（待被克隆的）RecruitmentProcess 实例。

    Returns:
        下一个可用的版本序号（整数，>= 2）。
    """
    from ..models import RecruitmentProcess

    max_seq = RecruitmentProcess.objects.filter(code=process.code).aggregate(
        max_seq=Max('version_seq'),
    )['max_seq'] or 0
    return max(max_seq, process.version_seq or 0) + 1


def _compute_next_version(process, seq: int = None) -> str:
    """纯计算：给出 ``process`` 所在流程线的下一个版本号字符串，**不写库**。

    T2 之前这里叫 ``bump_version``，既算版本号又 ``process.save()`` 原地改写**老行**的
    ``current_version``——那是 V2/V3/V4 三个缺陷的共同根因：

    - V2：克隆时改写老行版本号，违反 BR-103「历史版本只读」；实测把 ``'1.0'``
      反复写成 ``'1.0+1+1+1'``（数据损坏）。
    - V3：老 default 是 ``'1.0'``（无 ``V`` 前缀），进不了 ``startswith('V')`` 分支，
      直接掉进 ``f'{cur}+1'`` 兜底，垃圾版本号经 ``__str__`` 直达 UI。
    - V4：从字符串反解 major/minor 本身不可靠，污染串一旦产生便不可恢复。

    改法：版本号的唯一权威来源是整数 ``version_seq``（DB 侧由
    ``uniq_process_code_version_seq`` 兜底），不再解析字符串、不再触碰老行。
    落库由调用方在**新建行**时完成，本函数零副作用。

    Args:
        process: 当前（待被克隆的）RecruitmentProcess 实例。
        seq: 已算好的目标版本序号；省略时内部调用 :func:`_compute_next_version_seq`。
            调用方若同时需要 seq 与版本串，应先算 seq 再传入，避免两次聚合查询
            之间取到不一致的结果。

    Returns:
        新版本字符串，形如 ``'V2.0'``。
    """
    if seq is None:
        seq = _compute_next_version_seq(process)
    return f'V{seq}.0'


# ============================================================
# 深拷贝基础设施（T4 / V6）
# ============================================================
# 任何被拷贝的模型都不许带过来的字段：主键与时间戳由新行自己生成，
# ``deleted_at`` 更不能继承（否则新版本一出生就是软删态）。
_COPY_EXCLUDE_BASE = frozenset({'id', 'pk', 'created_at', 'updated_at', 'deleted_at'})
# 审计字段统一由 actor 覆盖，不沿用旧行的创建人。
_COPY_EXCLUDE_AUDIT = frozenset({'created_by', 'updated_by'})


def _copy_field_values(instance, *, exclude: frozenset) -> dict:
    """按 ``_meta.concrete_fields`` **自省**抽取字段值，产出可喂给 ``create(**data)`` 的字典。

    为什么必须自省而不是手写字段清单
    ------------------------------------
    ``StageRule`` 在 2026-07-03 扩了 9 个字段（``auto_advance_type`` /
    ``default_handler_*`` / ``time_limit*`` / ``interview_round_ids`` 等，见
    ``models.py`` 该段注释），而 clone 里那份手抄的 17 字段清单**从未同步**——
    克隆出的新版本静默丢掉这 9 项配置。手写清单是这个函数的系统性弱点：
    它把「模型加字段」和「拷贝加字段」变成两个必须靠人记住的动作。改成自省后，
    将来加字段自动被覆盖，漏拷这类缺陷从「靠自觉」变成「结构上不可能」。

    实现要点：
    - 用 ``f.attname`` 而非 ``f.name`` 取值。FK 的 attname 是 ``xxx_id``，读原始外键值
      **不会**触发一次 SELECT；用 ``f.name`` 会把每个 FK 都变成一次查询（N+1），
      且拿到的对象还得再解引用。
    - ``exclude`` 同时按 ``f.name`` 和 ``f.attname`` 比对：调用方写 ``'link'`` 就能排掉
      ``link_id``，不必两个都写。
    - list / dict 值（JSONField 载荷）走 ``deepcopy``：不深拷会让新旧两行共享同一个
      Python 对象，改新行的 ``processor_order`` 会连带改旧行内存态（BR-103 的隐性破口）。

    Args:
        instance: 源模型实例。
        exclude: 要跳过的字段名集合（``name`` 或 ``attname`` 命中即跳过）。

    Returns:
        ``{attname: value}`` 字典。
    """
    data: dict = {}
    for field in instance._meta.concrete_fields:
        if field.primary_key:
            continue
        if field.name in exclude or field.attname in exclude:
            continue
        value = getattr(instance, field.attname)
        if isinstance(value, (list, dict)):
            value = deepcopy(value)
        data[field.attname] = value
    return data


def _clone_related(model, source, *, exclude: frozenset, overrides: dict):
    """自省拷贝 ``source`` 为 ``model`` 的一条新行，``overrides`` 覆盖指定字段后落库。

    **overrides 的 key 怎么选（这里踩过坑，别改回去）：**

    ``_copy_field_values`` 产出的 key 一律是 attname（FK 就是 ``xxx_id``）。
    ``data.update(overrides)`` 是**字典层面**的覆盖——只有 key 字面量相同才会顶掉。
    所以规则是：

    - 该字段已被 ``exclude`` 排掉（data 里没有它）→ key 用字段名或 attname 都行，
      例如 ``exclude={'process'}`` 配 ``overrides={'process': new_process}``。
    - 该字段**仍在 data 里**、要就地改值 → key **必须**用 attname，否则 data 里那个
      attname 键原封不动留着，两个键一起进 ``Model.__init__``。而 ``__init__`` 处理
      FK 时，是先按 concrete_fields 顺序消费 attname（``next_stage_id=<旧值>``），
      再把剩下的字段名 kwargs 当作关系赋值；传 ``next_stage=None`` 这种「空关系」
      并不会把已写入的 ``next_stage_id`` 清回 None，结果就是**静默保留旧外键**。
      这正是 ``test_clone_disables_automation_rule_whose_next_stage_was_removed``
      守的那条线：必须写 ``overrides['next_stage_id'] = None``。

    正反例对照（以「把 AutomationRule 的 next_stage 置空」为例）::

        # ❌ 无效：data 里已有 'next_stage_id'，这行只是多塞了一个无人读的 key
        data.update({'next_stage': None})
        # ✅ 有效：自省产出的 key 是 attname，覆写必须用 attname
        data.update({'next_stage_id': None})

    这个坑**不限于 clone**：项目里任何「自省字段 → dict → 重建实例」的写法都会踩
    （批量复制、导入导出、快照回滚、测试夹具工厂……）。它的恶劣之处在于**没有任何
    信号**——不抛异常、不打日志、DB 层也没有 FK 约束会拦（本仓 FK 多为逻辑外键），
    表现只是新行悄悄指着旧版本的对象。肉眼 review 极难发现，唯一可靠的兜底是
    **断言**：凡自省拷贝出来的行，都要显式断言其外键不指回源对象。
    """
    data = _copy_field_values(source, exclude=exclude)
    data.update(overrides)
    return model.objects.create(**data)


def _live_children(manager, *order_fields):
    """取某个反向关系的「存活」子行，并按给定字段稳定排序。

    本仓的反向 Manager 是**原生** Manager，不会自动过滤软删——``stage_links.all()``
    会把软删的 link 一并克隆进新版本（X2；开发库流程 ``Yw9GBzXA4rJT8348AthR2``
    8 条 link 里有 4 条是软删的）。

    是否过滤按模型**实际有没有** ``deleted_at`` 字段动态决定，而不是写死：
    ``EntryConditionRule`` / ``TimeLimitRule`` / ``AutomationRule`` 都只继承
    ``TimestampedModel``（无软删），硬写 ``filter(deleted_at__isnull=True)`` 会直接
    ``FieldError``；反过来若将来给它们加上软删，这里会自动跟上。

    排序必须显式且稳定：``EntryConditionRule`` 的序号是 ``ProcessStageLink
    .entry_rule_expression``（形如 ``(1 AND 2) OR 3``）的引用基准，顺序错位 =
    表达式指向另一条规则，静默改变准入逻辑。
    """
    qs = manager.all()
    if any(f.name == 'deleted_at' for f in manager.model._meta.concrete_fields):
        qs = qs.filter(deleted_at__isnull=True)
    if order_fields:
        qs = qs.order_by(*order_fields)
    return qs


@transaction.atomic
def clone_process_with_new_version(
    process,
    new_name: str = None,
    actor=None,
) -> 'RecruitmentProcess':
    """克隆流程并生成新版本（深拷贝所有 stage_links 和 stage_rules）

    用于：
    - 引用中流程的配置修改（PRD BR-101）
    - 历史候选人"升版本"（BR-104）

    **老行只读**：本函数不再改写老行的 ``current_version`` / ``version_seq``
    （BR-103），唯一会被写的老行字段是 ``is_latest``——降级让位给新行。

    **按 Q4 裁定，克隆不改指任何 Demand/Position/Application（有意为之）**：
    在跑的候选人继续走创建时的版本（BR-102），改指必须由显式的升版本动作发起。

    深拷贝清单（T4 / V6）
    ----------------------
    ======================== ==================================================
    关系                      处置
    ======================== ==================================================
    ``stage_links``          拷贝，**只取 live 行**（软删 link 不进新版本）
    ``stage_rule`` (1:1)     **自省**拷贝全部 concrete field（原手抄清单漏 9 个）
    ``entry_condition_rules``拷贝 + **递归**拷贝二级 ``items``（ConditionItem）
    ``time_limit_rules``     拷贝
    ``automation_rules``     拷贝，按新版本阶段集合过滤（产品 Q3）
    ``application_records``  **不拷贝**（运行时数据，非配置）
    ======================== ==================================================

    ⚠️ ``EntryConditionRule`` / ``TimeLimitRule`` 上的 ``process_id`` 是**普通
    CharField，不是 FK**（``entry_condition/models.py`` / ``time_limit/models.py``），
    ``workflow_version`` 同理。自省拷贝会把旧流程 ID 与旧版本号原样带过来，形成
    跨版本脏引用，且因为不是 FK，DB 层没有任何约束会拦住它——必须显式覆盖。

    Returns:
        新建的 RecruitmentProcess。额外挂一个 ``_degraded_automation_rules`` 属性
        （list[dict]）：因阶段变更而被跳过/禁用的自动化规则清单，供端点回给前端提示
        「N 条自动化规则因阶段变更需要重新配置」。函数签名保持返回单值，避免
        ``views.clone_version`` 等既有调用方被迫改写（元组返回会静默把整个
        Response 变成序列化元组）。
    """
    from apps.automation.models import AutomationRule
    from apps.entry_condition.models import ConditionItem, EntryConditionRule
    from apps.time_limit.models import TimeLimitRule

    from ..models import (
        ProcessStageLink,
        RecruitmentProcess,
        StageRule,
    )

    # 先算 seq 再由它派生版本串，保证 version_seq 与 current_version 永远同源，
    # 不会出现 C1 通过而 C2 撞车（或反之）这种半截状态。
    new_seq = _compute_next_version_seq(process)
    new_version = _compute_next_version(process, seq=new_seq)

    # 创建新流程
    new_process = RecruitmentProcess.objects.create(
        code=process.code,  # 编号不变，新版本是同一流程
        name=new_name or f'{process.name} ({new_version})',
        current_version=new_version,
        version_seq=new_seq,
        # 新行先落为非 latest：翻转必须「先降后升」，此处若直接 True 会与老行瞬时
        # 并存两个 latest → C3' 立即 IntegrityError。
        is_latest=False,
        applicable_scope=deepcopy(process.applicable_scope),
        is_template=process.is_template,
        template_code=process.template_code,
        is_enabled=process.is_enabled,
        validate_resume_score=process.validate_resume_score,
        description=process.description,
        status='ENABLED',
        created_by=actor,
        updated_by=actor,
    )

    audit_overrides = {'created_by': actor, 'updated_by': actor}
    child_exclude = _COPY_EXCLUDE_BASE | _COPY_EXCLUDE_AUDIT

    # ------------------------------------------------------------
    # 克隆 stage_links（只取 live 行；顺序即 entry_rule_expression 的序号基准）
    # ------------------------------------------------------------
    new_stage_ids: set = set()
    for link in _live_children(process.stage_links, 'order', 'id'):
        new_link = ProcessStageLink.objects.create(
            process=new_process,
            stage_id=link.stage_id,
            order=link.order,
            is_required=link.is_required,
            entry_rule_expression=link.entry_rule_expression,
            created_by=actor,
            updated_by=actor,
        )
        new_stage_ids.add(link.stage_id)

        # --- stage_rule（1:1）：自省全字段拷贝 ---
        # 用 getattr(..., None) 而非 hasattr：hasattr 会把 RelatedObjectDoesNotExist
        # 之外的真实异常也一并吞成 False，让「拷贝失败」伪装成「本来就没有」。
        old_rule = getattr(link, 'stage_rule', None)
        if old_rule is not None:
            _clone_related(
                StageRule, old_rule,
                exclude=child_exclude | {'link'},
                overrides={'link': new_link, **audit_overrides},
            )

        # --- entry_condition_rules（1:N）+ 递归 items（二级 1:N） ---
        for old_ec in _live_children(link.entry_condition_rules, 'rule_seq', 'id'):
            new_ec = _clone_related(
                EntryConditionRule, old_ec,
                exclude=child_exclude | {'link'},
                overrides={
                    'link': new_link,
                    # ⚠️ 普通 CharField，不是 FK —— 排除 'process' 拦不住它。
                    # 漏了这两行，新版本的规则会指回**旧**流程 ID / 旧版本号，
                    # 而 DB 层没有 FK 约束会报错，属于静默脏数据。
                    'process_id': new_process.id,
                    'workflow_version': new_process.current_version,
                    **audit_overrides,
                },
            )
            for old_item in _live_children(old_ec.items, 'item_seq', 'id'):
                _clone_related(
                    ConditionItem, old_item,
                    exclude=child_exclude | {'rule'},
                    overrides={'rule': new_ec},
                )

        # --- time_limit_rules（1:N） ---
        for old_tl in _live_children(link.time_limit_rules, 'priority', 'id'):
            _clone_related(
                TimeLimitRule, old_tl,
                exclude=child_exclude | {'link'},
                overrides={
                    'link': new_link,
                    'process_id': new_process.id,       # 同上：CharField，非 FK
                    'workflow_version': new_process.current_version,
                    **audit_overrides,
                },
            )

    # ------------------------------------------------------------
    # 克隆 automation_rules（产品 Q3：复制，但按新版本阶段集合过滤）
    # ------------------------------------------------------------
    # 不复制 = 静默的能力归零：AutomationRule.process 是 CASCADE FK 指向**具体行**，
    # 新版本行天生没有任何规则，用户改个小配置就会「第二天发现自动提醒全停了」。
    # stage / next_stage 都 FK 到全局阶段字典 RecruitmentStage（**不是** ProcessStageLink），
    # 所以复制过去不会悬空；真实边界只有「新版本删掉了该阶段」这一种。
    degraded_rules: List[dict] = []
    for old_auto in _live_children(process.automation_rules, 'created_at', 'id'):
        if old_auto.stage_id not in new_stage_ids:
            # 触发阶段已从新版本移除 → 复制过去也是永不触发的哑规则，跳过。
            degraded_rules.append({
                'rule_id': old_auto.id,
                'rule_name': old_auto.name,
                'action': 'SKIPPED',
                'reason': 'STAGE_REMOVED',
                'stage_id': old_auto.stage_id,
            })
            continue

        overrides = {'process': new_process, **audit_overrides}
        if old_auto.next_stage_id is not None and old_auto.next_stage_id not in new_stage_ids:
            # 目标阶段没了：规则本身仍有意义（用户可重配），但不能带着悬空目标运行。
            # 注意 key 必须是 attname ``next_stage_id``：``next_stage`` 字段名没有被
            # exclude 排掉，data 里已有 ``next_stage_id=<旧值>``，用字段名传 None
            # 顶不掉它（详见 _clone_related 的 docstring），旧外键会被静默保留。
            overrides['next_stage_id'] = None
            overrides['enabled'] = False
            degraded_rules.append({
                'rule_id': old_auto.id,
                'rule_name': old_auto.name,
                'action': 'DISABLED',
                'reason': 'NEXT_STAGE_REMOVED',
                'stage_id': old_auto.stage_id,
                'next_stage_id': old_auto.next_stage_id,
            })

        _clone_related(
            AutomationRule, old_auto,
            exclude=child_exclude | {'process'},
            overrides=overrides,
        )

    new_process._degraded_automation_rules = degraded_rules
    if degraded_rules:
        logger.warning(
            'Clone %s → %s: %d automation rule(s) degraded by stage changes',
            process.id, new_process.id, len(degraded_rules),
        )

    # ============================================================
    # is_latest 原子翻转 —— **顺序是硬约束：必须先降后升**
    # 双库实测：先升后降在 ① 执行瞬间同 code 存在 2 行 is_latest=True
    # → C3'（uniq_one_latest_per_code）立即抛 IntegrityError，克隆整体回滚。
    # ============================================================
    # ① 先降级：filter(code=...) 刻意不过滤软删，一并降级软删行（自愈，见 C3' soft_delete 条）
    RecruitmentProcess.objects.filter(code=new_process.code).exclude(id=new_process.id).update(is_latest=False)
    # ② 后升级
    new_process.is_latest = True
    new_process.save(update_fields=['is_latest'])

    logger.info('Process %s cloned to new version %s by %s', process.id, new_version, actor)
    return new_process


def list_process_versions(process_code: str) -> List[dict]:
    """列出某流程编号的所有历史版本，按 ``version_seq`` 升序。

    三个已修缺陷，改动前请先读这段：

    - **V8**：原实现不过滤软删，已软删的版本行照样出现在版本列表里。
    - **V9（排序）**：原实现 ``order_by('current_version')`` 是**字典序**——实测
      ``['V1.0', 'V1.10', 'V1.2', 'V10.0', 'V2.0']``，第 10 版排在第 2 版前面。
      版本号的唯一权威来源是整数 ``version_seq``（同 :func:`_compute_next_version`），
      排序也必须走它。
    - **V9（N+1）**：原实现在推导式里逐行读 ``p.reference_count`` 属性，N 行发 1+N 条
      COUNT。改为一次 ``annotate(Count(..., filter=...))``，全函数恒定 **1 条**查询。

    ``reference_count`` 的口径与 ``is_process_referenced`` / ``RecruitmentProcess
    .reference_count`` 对齐：只数 live Demand。

    Args:
        process_code: 流程编号（``code``）。库中不存在 / 全部软删时返回 ``[]``，不抛异常。

    Returns:
        list[dict]，每项含 ``id`` / ``version`` / ``version_seq`` / ``is_latest`` /
        ``name`` / ``status`` / ``created_at`` / ``reference_count``。
    """
    from ..models import RecruitmentProcess

    versions = (
        RecruitmentProcess.objects
        .filter(code=process_code, deleted_at__isnull=True)
        .annotate(
            live_reference_count=Count(
                'demands', filter=Q(demands__deleted_at__isnull=True),
            ),
        )
        .order_by('version_seq')
    )
    rows = [
        {
            'id': p.id,
            'version': p.current_version,
            'version_seq': p.version_seq,
            'is_latest': p.is_latest,
            'name': p.name,
            'status': p.status,
            'created_at': p.created_at.isoformat() if p.created_at else None,
            'reference_count': p.live_reference_count,
        }
        for p in versions
    ]

    # C3'（uniq_one_latest_per_code）保证每条 code 至多 1 行 latest，但「至多」不等于
    # 「恰好」：整条线全软删或历史数据未回填时可能一个都没有。这里**只告警不抛**——
    # 列表是只读查询，不该因为数据面异常而对用户 500。硬断言留在回归测试里。
    latest_count = sum(1 for row in rows if row['is_latest'])
    if rows and latest_count != 1:
        logger.error(
            'Process line %s has %d rows with is_latest=True (expected exactly 1)',
            process_code, latest_count,
        )

    return rows


# 已删除（T3 死代码清理）：``upgrade_application_to_latest_version``
# 零调用、零测试，且自带 V5 缺陷——它先把 ``application.workflow_version`` 写成目标
# 版本，之后才把该字段读作返回值里的 ``from_version``，导致 ``from_version`` 恒等于
# ``to_version``，审计一直在撒谎。「候选人升版本」的唯一活实现是
# ``apps.application.services.ApplicationService.upgrade_workflow_version``；
# 本函数**一行逻辑都不得回迁**（读后写的坑会跟着一起搬过去）。
# 守卫：``tests/test_dead_upgrade_function_is_gone.py``。
