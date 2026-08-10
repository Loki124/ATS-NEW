"""阶段映射共享服务（§2.2）— 「申请当前阶段 → 目标流程阶段」解析。

谁在用
======
- **T3 升版本**（``ApplicationService.upgrade_workflow_version``）：同一条 ``code``
  流程线内，把申请从旧版本行改指到 ``is_latest=True`` 的新版本行。
- **T8 换流程**（``change-process``）：跨 ``code`` 把申请改指到另一条流程线。

两者的差异只在**校验**（是否允许跨 code、是否禁降版本），落点计算完全一致，
故抽到本模块共用，避免两处各写一份而慢慢长歪。

为什么必须是纯函数
==================
本模块**只读**：唯一的数据库访问是 ``new_process.stage_links`` 的一次查询，
不写任何行、不发信号、不写审计。调用方（T3/T8）负责在自己的
``transaction.atomic`` 里完成「解析 → 改指 → 写审计」。

这样做的收益：
1. 落点计算可被单测穷举（见 ``apps/application/tests/test_stage_mapping.py``），
   不必构造 Application/Candidate/Position 整条外键链；
2. 调用方可以「先算后写」——落点算不出来（目标流程零阶段）时直接抛错，
   不会留下「process 已改指、current_link 却悬空」的半截状态。

映射算法（§2.2）
================
设申请升级前所在的关联为 ``current_link``（其 ``stage`` 为当前阶段、``order`` 为
其在**旧**流程中的序号），在目标流程的 **live** 关联（``deleted_at IS NULL``）中
按下列优先级取落点：

1. **精确匹配**：目标流程存在同一 ``stage`` 的 live 关联 → 落它（阶段没变，
   ``remapped=False``，候选人体感无跳转）。
2. **前序回落**：当前阶段在新版本被删/未配置 → 取新版本中 ``order`` 严格小于
   ``current_link.order`` 的**最大** order 的 live 关联。语义是「退回到候选人
   确定已经走过的最后一个阶段」，绝不前进——前进会让候选人白嫖掉尚未通过的环节。
3. **回落到起点**：连前序都没有（当前阶段在新版本里排最前，或前面的全被删了）
   → 落新版本第一个 live 关联。
4. **无 current_link**：同样落起点。见下方「关于 current_link 为空」。
5. **目标流程零 live 阶段** → 抛 :class:`StageMappingError`（``ValueError`` 子类）。

关于 current_link 为空
======================
``Application.current_link`` 是 ``on_delete=SET_NULL``，硬删关联行会把它置空；
``current_stage`` 则可能仍留着值。此时**刻意不**拿 ``current_stage`` 去做精确匹配，
一律落起点，理由有二：

- 没有 ``order`` 锚点就无法做前序回落，精确匹配失败后仍要落起点，两条路径徒增分叉；
- ``current_stage`` 在 link 已消失的情况下是**孤证**，据此把候选人直接放到流程中段，
  等于凭一个不可校验的残留字段跳过前面所有阶段。落起点是唯一可解释的保守选择。

关于「live」的口径
==================
只按**关联行**（``ProcessStageLink.deleted_at``）过滤，不看 ``RecruitmentStage``
自身的 ``status``/``deleted_at``。原因：阶段库是全局字典，某个阶段被全局停用
不代表已配好的流程要立刻塌掉；流程里「这一步还算不算数」的唯一权威是关联行。
（这也与 T4 clone 深拷贝的口径一致——clone 同样只拷 live 关联。）
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from apps.process.models import ProcessStageLink, RecruitmentProcess, RecruitmentStage

if TYPE_CHECKING:  # pragma: no cover - 仅供类型检查，避免运行期引入无谓依赖
    from ..models import Application

logger = logging.getLogger(__name__)


# ============================================================
# 落点策略常量
# ============================================================
#: 目标流程存在同一阶段的 live 关联 —— 阶段未变。
STRATEGY_EXACT: str = 'EXACT'
#: 当前阶段在目标流程不存在，回落到前序阶段。
STRATEGY_PREDECESSOR: str = 'PREDECESSOR'
#: 无前序可回落（或无 current_link），落目标流程第一个 live 关联。
STRATEGY_START: str = 'START'

#: 全部合法策略，供调用方/测试做穷举校验。
ALL_STRATEGIES: tuple = (STRATEGY_EXACT, STRATEGY_PREDECESSOR, STRATEGY_START)

#: 目标流程零 live 阶段时的错误文案（调用方转 409 时会原样透出，勿随意改）。
NO_STAGE_MESSAGE: str = '目标流程无任何可用阶段'


class StageMappingError(ValueError):
    """目标流程没有任何可落脚的 live 阶段，无法完成映射。

    刻意继承 ``ValueError``（而非 ``StateTransitionError``）：本模块是与 HTTP 无关的
    纯计算单元，不应该把 DRF 的状态码语义带进来。调用方（T3/T8 的 service 层）
    负责捕获后转成 ``StateTransitionError`` → 409。
    """


@dataclass(frozen=True)
class StageMapping:
    """一次映射的完整结论（含审计所需的全部原始信息）。

    Attributes:
        link: 目标流程中的落点关联，**保证非空且 live**。
        strategy: :data:`ALL_STRATEGIES` 之一，说明落点是怎么来的。
        remapped: 阶段是否发生了改变（``strategy != EXACT``）。写审计的
            ``stage_remapped`` 字段直接取它。
        source_link_id: 映射前的关联 id；无 current_link 时为 ``None``。
        source_stage_id: 映射前的阶段 id；无 current_link 时为 ``None``。
        source_order: 映射前的阶段序号；无 current_link 时为 ``None``。
    """

    link: ProcessStageLink
    strategy: str
    remapped: bool
    source_link_id: Optional[str] = None
    source_stage_id: Optional[str] = None
    source_order: Optional[int] = None

    @property
    def stage(self) -> RecruitmentStage:
        """落点关联对应的阶段（``select_related`` 过，不会再打一次库）。"""
        return self.link.stage

    def as_audit_detail(self) -> Dict[str, Any]:
        """摊平成审计 ``detail`` 用的字典（T3/T8 共用同一份 key 集合）。"""
        return {
            'stage_remapped': self.remapped,
            'stage_map_strategy': self.strategy,
            'from_link_id': self.source_link_id,
            'from_stage_id': self.source_stage_id,
            'from_stage_order': self.source_order,
            'to_link_id': self.link.id,
            'to_stage_id': self.link.stage_id,
            'to_stage_order': self.link.order,
        }


# ============================================================
# 内部工具
# ============================================================
def _extract_current_link(
    source: Union['Application', ProcessStageLink, None],
) -> Optional[ProcessStageLink]:
    """把入参归一成 ``ProcessStageLink | None``。

    支持三种入参（§2.2 要求「application 或 current_link」）：

    - ``ProcessStageLink`` → 原样返回；
    - 带 ``current_link`` 属性的对象（``Application``）→ 取其 ``current_link``；
    - ``None`` → ``None``（调用方明确表示「没有落脚点」）。

    刻意用鸭子类型而非 ``isinstance(source, Application)``：本模块不 import
    ``..models``，避免 ``services`` ↔ ``models`` 之间多一条无谓的运行期依赖。

    Raises:
        TypeError: 传了既不是 link、也没有 ``current_link`` 属性的东西 ——
            这是调用方的编程错误，必须响亮失败而不是静默当成 None 落起点。
    """
    if source is None:
        return None
    if isinstance(source, ProcessStageLink):
        return source
    if hasattr(source, 'current_link'):
        return source.current_link
    raise TypeError(
        f'resolve_target_link 只接受 Application / ProcessStageLink / None，'
        f'收到 {type(source).__name__}',
    )


def _live_links(new_process: RecruitmentProcess) -> List[ProcessStageLink]:
    """目标流程的 live 关联，按 ``order`` 升序。

    排序键刻意带上 ``created_at``/``id`` 兜底：``order`` 在真实库里**会重复**
    （dev 实测流程 ``Yw9GBzXA4rJT8348AthR2`` 的 8 条关联 orders 为
    ``[2,3,4,4,5,8,9,10]``）。只按 ``order`` 排序时，同序号行的先后由数据库
    实现决定，会让「起点」和「前序」在不同库/不同执行计划下漂移。
    """
    return list(
        new_process.stage_links
        .filter(deleted_at__isnull=True)
        .select_related('stage')
        .order_by('order', 'created_at', 'id')
    )


# ============================================================
# 对外 API
# ============================================================
def resolve_stage_mapping(
    source: Union['Application', ProcessStageLink, None],
    new_process: RecruitmentProcess,
) -> StageMapping:
    """解析落点并返回完整结论（含策略与审计快照）。

    Args:
        source: 升级前的 ``Application``、其 ``current_link``，或 ``None``。
        new_process: 目标流程（升版本时是同 code 的 ``is_latest=True`` 行）。

    Returns:
        :class:`StageMapping`，``link`` 保证非空且属于 ``new_process``。

    Raises:
        StageMappingError: ``new_process`` 没有任何 live 关联。
        TypeError: ``source`` 类型不合法。
    """
    live = _live_links(new_process)
    if not live:
        raise StageMappingError(NO_STAGE_MESSAGE)

    current_link = _extract_current_link(source)

    # ④ 无 current_link → 起点（不拿 current_stage 做孤证匹配，理由见模块 docstring）
    if current_link is None:
        return StageMapping(
            link=live[0],
            strategy=STRATEGY_START,
            remapped=True,
        )

    source_link_id = current_link.id
    source_stage_id = current_link.stage_id
    source_order = current_link.order

    # ① 精确匹配：目标流程里有同一阶段的 live 关联
    for link in live:
        if link.stage_id == source_stage_id:
            return StageMapping(
                link=link,
                strategy=STRATEGY_EXACT,
                remapped=False,
                source_link_id=source_link_id,
                source_stage_id=source_stage_id,
                source_order=source_order,
            )

    # ② 前序回落：order 严格小于当前序号的最大 order（live 已升序，取最后一个即最大）
    predecessors = [link for link in live if link.order < source_order]
    if predecessors:
        target = predecessors[-1]
        logger.info(
            'Stage remapped to predecessor: process=%s stage=%s(order=%s) -> stage=%s(order=%s)',
            new_process.id, source_stage_id, source_order, target.stage_id, target.order,
        )
        return StageMapping(
            link=target,
            strategy=STRATEGY_PREDECESSOR,
            remapped=True,
            source_link_id=source_link_id,
            source_stage_id=source_stage_id,
            source_order=source_order,
        )

    # ③ 无前序可回落 → 起点
    logger.info(
        'Stage remapped to start: process=%s stage=%s(order=%s) -> stage=%s(order=%s)',
        new_process.id, source_stage_id, source_order, live[0].stage_id, live[0].order,
    )
    return StageMapping(
        link=live[0],
        strategy=STRATEGY_START,
        remapped=True,
        source_link_id=source_link_id,
        source_stage_id=source_stage_id,
        source_order=source_order,
    )


def resolve_target_link(
    source: Union['Application', ProcessStageLink, None],
    new_process: RecruitmentProcess,
) -> ProcessStageLink:
    """§2.2 主入口：只要落点关联本身。

    等价于 ``resolve_stage_mapping(source, new_process).link``。需要知道「是否发生
    回落」（写审计的 ``stage_remapped``）时请直接用 :func:`resolve_stage_mapping`。
    """
    return resolve_stage_mapping(source, new_process).link
