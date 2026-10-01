"""指标规则筛选 —— 异步任务（大规模候选人场景）。

为什么需要异步：
    规则含派生指标（空窗期 / 跳槽频率等）需逐条构建快照并计算，无法 SQL 化。
    同步端点只能扫描前 N 条（FILTER_MAX_CANDIDATES），候选人规模大时结果会被截断。
    本任务对**全量**候选人执行，结果写入缓存，前端凭 taskId 轮询进度与结果。

结果存储：django cache（Redis），TTL 30 分钟。无 Redis 时降级为不写进度，
但任务本身仍会执行并返回结果（Celery result backend 兜底）。

启动 worker（项目约定）：
    celery -A celery_app worker -l info
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from celery import shared_task
from django.core.cache import cache

logger = logging.getLogger(__name__)

TASK_TTL = 30 * 60  # 结果缓存 30 分钟


def _cache_key(task_id: str) -> str:
    return f'metrics:filter-task:{task_id}'


def write_progress(task_id: str, payload: Dict[str, Any]) -> None:
    try:
        cache.set(_cache_key(task_id), payload, TASK_TTL)
    except Exception as exc:  # noqa: BLE001 — 无 Redis 时不影响任务执行 (缓存故障不应阻塞主流程)
        logger.warning('[metrics] 写入筛选进度失败 task=%s: %s', task_id, exc)


def read_progress(task_id: str) -> Optional[Dict[str, Any]]:
    try:
        return cache.get(_cache_key(task_id))
    except Exception:  # noqa: BLE001 — 无 Redis 时返 None (读缓存失败回退到无缓存路径, 不应阻断轮询)
        return None


@shared_task(bind=True, queue='scoring')
def filter_by_scene_task(self, task_id: str, scene: str,
                         candidate_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """按场景规则对（全量）候选人执行筛选，进度与结果写入缓存。"""
    from .services.rule_trigger import default_candidate_ids, evaluate_scene

    write_progress(task_id, {'status': 'running', 'progress': 0, 'total': 0})

    ids = [str(i) for i in candidate_ids] if candidate_ids else default_candidate_ids(limit=None)
    total = len(ids)

    passed: List[str] = []
    rejected: List[Dict[str, Any]] = []

    for index, cid in enumerate(ids, start=1):
        try:
            outcome = evaluate_scene(scene, cid)
            if outcome.get('blocked'):
                rejected.append({'candidateId': cid, 'reason': outcome.get('message')})
            else:
                passed.append(cid)
        except Exception as exc:  # noqa: BLE001 — 单条失败不中断整体 (批量筛选场景, 单条规则异常不应拖垮全量)
            logger.exception('[metrics] 筛选任务单条失败 candidate=%s', cid)
            passed.append(cid)

        # 每 20 条或最后一条刷新一次进度（避免频繁写缓存）
        if index % 20 == 0 or index == total:
            write_progress(task_id, {
                'status': 'running', 'progress': index, 'total': total,
            })

    result = {
        'status': 'done',
        'scene': scene,
        'progress': total,
        'total': total,
        'passedIds': passed,
        'rejected': rejected,
    }
    write_progress(task_id, result)
    return result
