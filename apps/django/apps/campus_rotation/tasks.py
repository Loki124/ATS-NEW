"""校招轮岗 Celery 任务（需求 5-9 / S5-22：考核提醒兜底）。

当前任务：
- `rotation_assessment_reminder`：每日扫描「满 15 天需考核但临近结束仍未考核」
  的轮岗阶段，输出提醒清单（本期只落日志 + 返回清单，不接通知通道）。

🔴 通知口径：Q-05 明确「本期仅状态变更 + 日志，不通知」，故本任务**不发邮件/
飞书/企微**，只写日志并返回结构化清单，通知通道接入时只需在此追加。
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)

# 临近结束提前提醒的天数（阶段结束日 <= 今天 + N 天即进提醒清单）
REMIND_DAYS_BEFORE_END = 3


@shared_task(
    bind=True,
    name='apps.campus_rotation.tasks.rotation_assessment_reminder',
    acks_late=True,
)
def rotation_assessment_reminder(self, days_before_end: int = REMIND_DAYS_BEFORE_END) -> dict:
    """扫描需考核但未考核的轮岗阶段。

    Args:
        days_before_end: 结束日距今 <= N 天即进提醒清单（默认 3 天）。

    Returns:
        {'scanned': int, 'need_remind': int, 'items': [{id, arrangement, postType, end}]}
    """
    from apps.campus_rotation.services.assessment import scan_pending_assessments

    try:
        stages = scan_pending_assessments(days_before_end=days_before_end)
    except Exception as exc:  # noqa: BLE001 —— 定时任务不因单次异常中断 beat
        logger.exception('轮岗考核提醒扫描失败')
        return {
            'scanned': 0, 'need_remind': 0, 'items': [],
            'error': f'{type(exc).__name__}: {exc}',
        }

    items = []
    for stage in stages:
        end = stage.actual_end or stage.planned_end
        items.append({
            'id': str(stage.id),
            'arrangement': str(stage.arrangement_id) if stage.arrangement_id else None,
            'stageNo': stage.stage_no,
            'end': end.isoformat() if end else None,
        })

    if items:
        logger.warning(
            '轮岗考核提醒：%d 个阶段满 15 天需考核但尚未填写结论，明细=%s',
            len(items), items[:20],
        )

    return {'scanned': len(stages), 'need_remind': len(items), 'items': items}
