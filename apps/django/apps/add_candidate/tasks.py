"""Add Candidate V2 - Celery tasks"""
from django.db import DatabaseError
import logging

from celery import shared_task
from django.db import transaction

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def parse_resume_task(self, job_id):
    """解析单个简历任务（完整实现）

    流程：parsing 阶段（调本地解析引擎 career_core / smartresume，可切换） → checking 阶段（查重） → done
    失败：ParseError 立即 fail（不重试）；其他异常重试 3 次

    2026-07-02: 全流程用 select_for_update 锁 job 行, 防并发重试导致
    progress/phase 倒序覆盖。
    """
    from .models import ParseJob
    from .services.resume_parser import ResumeParserService, ParseError
    from .services.duplicate_check import DuplicateCheckService

    try:
        with transaction.atomic():
            job = ParseJob.objects.select_for_update().get(job_id=job_id)
    except ParseJob.DoesNotExist:
        logger.error('ParseJob %s not found', job_id)
        return

    try:
        # 1. 阶段：parsing
        ParseJob.objects.filter(pk=job.pk).update(phase='parsing', progress=10)

        # 2. 调本地解析引擎 (subprocess IO 在锁外, 这里只用短锁)
        with open(job.file_path, 'rb') as f:
            parsed = ResumeParserService.parse(f)

        # 3. 阶段：checking
        with transaction.atomic():
            info = DuplicateCheckService.find(
                phone=parsed.phone or '',
                email=parsed.email or '',
                id_card='',
                moka_id='',
            )
            ParseJob.objects.filter(pk=job.pk).update(
                progress=100, status='done', phase='done',
                parsed_data=parsed.to_dict(), duplicate_data=info.to_dict(),
            )

    except ParseError as e:
        logger.error('ParseJob %s parse error: %s', job_id, e.code)
        ParseJob.objects.filter(pk=job.pk).update(status='failed', error=e.code)
        # 不重试，配置错误/超时应该立即 fail

    except (DatabaseError, ValueError, TypeError, AttributeError, OSError) as e:  # Celery ParseJob 兜底: 未预期异常全部 retry (与已知异常区分), 不让单次解析永久失败
        logger.exception('ParseJob %s unexpected: %s', job_id, e)
        # 重试 3 次
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            ParseJob.objects.filter(pk=job.pk).update(
                status='failed', error='MAX_RETRIES_EXCEEDED',
            )


@shared_task(bind=True, max_retries=3, default_retry_delay=5, queue='scoring')
def score_batch_task(self, candidate_ids, submit_mode, task_id):
    """批量评分任务

    对每个候选调用 ScoringService.score() 真引擎评分，通过 broadcast_event 推 SSE 进度。
    完成后如果是 async 模式，调用 send_async_notification_task。

    数据源：P1 最小策略 — candidate.extra['resume'] + position.extra['jd'] JSONField。
    无数据时退化为空 dict → 低分兜底。
    """
    from .sse import broadcast_event
    from .services.scoring import ScoringService
    from apps.candidate.models import Candidate
    from apps.application.models import Application
    # 2026-09-25: 评分触发点（函数内导入，避免模块级循环依赖）
    from apps.metrics.services.rule_trigger import evaluate_scene

    passed_count = 0
    for cand_id in candidate_ids:
        try:
            cand = Candidate.objects.select_related().get(pk=cand_id)

            # 通过最近的 Application 拿到关联 Position
            app = (Application.objects
                   .filter(candidate_id=cand_id, deleted_at__isnull=True)
                   .select_related('position')
                   .order_by('-created_at').first())
            position = app.position if app else None

            # P1 最小策略：全从 extra JSONField 读，无则空 dict 退化为低分兜底
            resume = cand.extra.get('resume') or {}
            pos_extra = getattr(position, 'extra', None) if position else None
            jd = (pos_extra.get('jd') if pos_extra else {}) or {}

            result = ScoringService.score(resume=resume, position_jd=jd)

            # 2026-09-25 触发点：执行「评分」场景的指标规则。
            # 阻断型规则不满足 → 不计入通过数，并把规则结论一并返回给前端。
            rule_outcome = evaluate_scene('SCORING', str(cand_id))
            rule_blocked = bool(rule_outcome.get('blocked'))

            if result.passed and not rule_blocked:
                passed_count += 1

            broadcast_event(task_id, {
                'event': 'scoring-done',
                'data': {
                    'candidate_id': cand_id,
                    **result.to_dict(),
                    'metricRule': {
                        'pass': rule_outcome.get('pass'),
                        'blocked': rule_blocked,
                        'message': rule_outcome.get('message'),
                    },
                },
            })
        except Candidate.DoesNotExist:
            logger.warning('Candidate %s not found, skipping', cand_id)
            broadcast_event(task_id, {
                'event': 'scoring-failed',
                'data': {'candidate_id': cand_id, 'error': 'CANDIDATE_NOT_FOUND'},
            })
        except (DatabaseError, ValueError, TypeError, AttributeError, OSError) as e:  # Celery 评分任务单条候选人失败不影响其他 (与 ParseJob 一致的批处理兜底)
            logger.exception('Score failed for %s: %s', cand_id, e)
            broadcast_event(task_id, {
                'event': 'scoring-failed',
                'data': {'candidate_id': cand_id, 'error': str(e)},
            })

    broadcast_event(task_id, {
        'event': 'task-complete',
        'data': {'summary': {'total': len(candidate_ids), 'passed': passed_count}},
    })

    if submit_mode == 'async':
        send_async_notification_task.delay(task_id)


@shared_task
def send_async_notification_task(task_id):
    """异步评分完成后发通知中心

    简化实现：只记录日志。Phase 3 接通知中心。
    """
    logger.info('Async scoring complete: task=%s', task_id)
