"""业务触发点执行器 —— 把持久化规则挂到入池 / 筛选 / 评分（T3）。

用法：
    from apps.metrics.services.rule_trigger import evaluate_scene
    result = evaluate_scene('TALENT_POOL', candidate_id)
    if result['blocked']:
        return Response({'error': result['message']}, status=400)

设计要点：
    1. 只执行该 scene 下「启用且状态正常」的规则，停用规则零开销跳过
    2. 动作语义由规则自带 action_type 字段控制（T4 取代旧 blocking 布尔）：
         VETO   → 不通过即拒绝业务动作（如拒绝入池）
         DEDUCT → 不满足仅记录/降权，不阻断（安全默认）
         BONUS  → 满足给正向加权，不满足不惩罚
       这样规则误配不会直接伤业务，运营可先观察再开启强约束
    3. 任何异常都不向上抛（业务动作不能因为规则引擎故障而失败），
       统一降级为「不阻断 + error 记录」，绝不 500
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .candidate_snapshot import (
    build_candidate_snapshot,
    build_demand_snapshot,
    build_position_snapshot,
)
from .metric_engine import MetricEngine

logger = logging.getLogger(__name__)


def _build_rule_context(rule) -> Dict[str, Any]:
    """收集规则绑定的需求/职位快照，并入求值 data（与 candidate 快照并列）。

    规则若引用 demand.* / position.* 对象路径指标，必须在此提供对应实体快照，
    否则引擎解析这些路径会失败（字段解析失败 → 该步 FAIL）。异常降级跳过，绝不阻断。
    """
    ctx: Dict[str, Any] = {}
    demand_id = getattr(rule, 'demand_id', None)
    position_id = getattr(rule, 'position_id', None)
    if demand_id:
        try:
            ctx.update(build_demand_snapshot(demand_id))
        except Exception as exc:
            logger.warning('[metrics] 需求快照构建失败 demand=%s: %s', demand_id, exc)
    if position_id:
        try:
            ctx.update(build_position_snapshot(position_id))
        except Exception as exc:
            logger.warning('[metrics] 职位快照构建失败 position=%s: %s', position_id, exc)
    return ctx


def default_candidate_ids(limit: int = 200) -> List[str]:
    """未提供 ID 列表时的默认候选集合（按创建时间倒序取前 limit 条）。

    放在服务层而非 views，供同步端点与 Celery 任务共用，避免循环导入。
    """
    from apps.candidate.models import Candidate

    qs = Candidate.objects.filter(deleted_at__isnull=True).order_by('-created_at')
    if limit is not None:
        qs = qs[:limit]
    return [str(pk) for pk in qs.values_list('id', flat=True)]


def count_candidates() -> int:
    """在库候选人总数（用于判断是否超出同步扫描上限）。"""
    from apps.candidate.models import Candidate

    return Candidate.objects.filter(deleted_at__isnull=True).count()


def evaluate_scene(scene: str, candidate_id: str) -> Dict[str, Any]:
    """执行某场景下全部启用规则，返回汇总结论。

    返回：
        {
          scene, candidateId, pass, blocked, message,
          rules: [{ruleId, ruleName, pass, actionType, summary, steps}],
          evaluated: 规则条数
        }
    """
    from apps.metrics.models import MetricRule, MetricStatus

    result: Dict[str, Any] = {
        'scene': scene,
        'candidateId': candidate_id,
        'pass': True,
        'blocked': False,
        'message': '',
        'rules': [],
        'evaluated': 0,
    }

    try:
        rules = list(MetricRule.objects.filter(
            scene=scene, enabled=True, status=MetricStatus.ENABLED,
        ).order_by('created_at'))
    except Exception as exc:  # 表不存在等极端情况 → 不阻断
        logger.warning('[metrics] 加载场景规则失败 scene=%s: %s', scene, exc)
        result['message'] = '规则加载失败（已放行）'
        return result

    if not rules:
        result['message'] = '该场景无启用规则'
        return result

    try:
        snapshot = build_candidate_snapshot(candidate_id)
    except Exception as exc:
        # 快照失败绝不阻断业务（规则引擎故障不应让入池/评分失败）
        logger.warning('[metrics] 快照构建失败 candidate=%s: %s', candidate_id, exc)
        result['message'] = '数据快照构建失败（已放行）'
        return result

    if not snapshot.get('candidate'):
        result['message'] = f'候选人 {candidate_id} 不存在'
        result['pass'] = False
        return result

    failed_veto: List[str] = []
    all_pass = True

    for rule in rules:
        # T4：阻断语义以 action_type=='VETO' 为权威（旧 blocking 仅作派生兼容）
        is_veto = (rule.action_type == 'VETO')
        # 并入规则绑定的需求/职位快照，使 demand.* / position.* 指标可真实求值
        data = {**snapshot, **_build_rule_context(rule)}
        try:
            outcome = MetricEngine.execute(
                rule.to_engine_conditions(), data, rule.logic or 'AND',
            )
        except Exception as exc:  # 单条规则异常不拖垮整体
            logger.exception('[metrics] 规则执行异常 rule=%s', rule.id)
            result['rules'].append({
                'ruleId': rule.id,
                'ruleName': rule.name,
                'pass': False,
                'actionType': rule.action_type,
                'summary': f'执行异常: {exc}',
                'steps': [],
            })
            continue

        passed = bool(outcome.get('pass'))
        if not passed:
            all_pass = False
            if is_veto:
                failed_veto.append(rule.name)

        result['rules'].append({
            'ruleId': rule.id,
            'ruleName': rule.name,
            'pass': passed,
            'actionType': rule.action_type,
            'summary': outcome.get('summary', ''),
            'steps': outcome.get('steps', []),
        })

    result['evaluated'] = len(rules)
    result['pass'] = all_pass
    if failed_veto:
        result['blocked'] = True
        result['message'] = '不满足规则：' + '、'.join(failed_veto)
    elif not all_pass:
        result['message'] = '存在未满足规则（未开启阻断，已放行）'
    else:
        result['message'] = '全部规则满足'

    return result


def filter_candidates_by_scene(scene: str, candidate_ids: List[str]) -> Dict[str, Any]:
    """批量筛选：返回通过全部阻断性规则的候选人 ID 列表（供"筛选"场景用）。"""
    passed: List[str] = []
    rejected: List[Dict[str, Any]] = []
    for cid in candidate_ids:
        outcome = evaluate_scene(scene, str(cid))
        if outcome.get('blocked'):
            rejected.append({'candidateId': str(cid), 'reason': outcome.get('message')})
        else:
            passed.append(str(cid))
    return {'scene': scene, 'passedIds': passed, 'rejected': rejected}
