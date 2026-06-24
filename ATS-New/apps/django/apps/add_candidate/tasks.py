"""Add Candidate V2 - Celery tasks"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def parse_resume_task(self, job_id):
    """解析单个简历任务（完整实现）

    流程：parsing 阶段（调 Affinda） → checking 阶段（查重） → done
    失败：ParseError 立即 fail（不重试）；其他异常重试 3 次
    """
    from .models import ParseJob
    from .services.resume_parser import ResumeParserService, ParseError
    from .services.duplicate_check import DuplicateCheckService

    try:
        job = ParseJob.objects.get(job_id=job_id)
    except ParseJob.DoesNotExist:
        logger.error('ParseJob %s not found', job_id)
        return

    try:
        # 1. 阶段：parsing
        job.phase = 'parsing'
        job.progress = 10
        job.save(update_fields=['phase', 'progress'])

        # 2. 调 Affinda
        with open(job.file_path, 'rb') as f:
            parsed = ResumeParserService.parse(f)

        job.progress = 70
        job.parsed_data = parsed.to_dict()
        job.save(update_fields=['progress', 'parsed_data'])

        # 3. 阶段：checking
        job.phase = 'checking'
        job.progress = 80
        job.save(update_fields=['phase', 'progress'])

        # 4. 查重
        info = DuplicateCheckService.find(
            phone=parsed.phone or '',
            email=parsed.email or '',
            id_card='',
            moka_id='',
        )
        job.duplicate_data = info.to_dict()
        job.status = 'done'
        job.progress = 100
        job.save(update_fields=['duplicate_data', 'status', 'progress'])

    except ParseError as e:
        logger.error('ParseJob %s parse error: %s', job_id, e.code)
        job.status = 'failed'
        job.error = e.code
        job.save(update_fields=['status', 'error'])
        # 不重试，配置错误/超时应该立即 fail

    except Exception as e:
        logger.exception('ParseJob %s unexpected: %s', job_id, e)
        # 重试 3 次
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            job.status = 'failed'
            job.error = 'MAX_RETRIES_EXCEEDED'
            job.save(update_fields=['status', 'error'])


@shared_task(bind=True, max_retries=3, default_retry_delay=5, queue='scoring')
def score_batch_task(self, candidate_ids, submit_mode, task_id):
    """批量评分任务

    对每个候选评分（用 ScoringService），通过 broadcast_event 推 SSE 进度
    完成后如果是 async 模式，调用 send_async_notification_task
    """
    from .sse import broadcast_event
    from .services.scoring import ScoringService

    for idx, cand_id in enumerate(candidate_ids):
        try:
            # 模拟：根据 candidate_id 查简历+职位
            # 真实实现需要查 DB；v1 简化：随机生成评分
            score = 50 + (idx * 10) % 50  # 50-90 循环
            passed = score >= 60
            broadcast_event(task_id, {
                'event': 'scoring-done',
                'data': {
                    'candidate_id': cand_id,
                    'score': score,
                    'passed': passed,
                    'dimensions': [
                        {'name': '技术匹配', 'score': 75 + idx % 20},
                        {'name': '经验匹配', 'score': 70 + idx % 25},
                        {'name': '学历匹配', 'score': 80 + idx % 15},
                        {'name': '综合素质', 'score': 65 + idx % 30},
                    ],
                },
            })
        except Exception as e:
            logger.exception('Score failed for %s: %s', cand_id, e)
            broadcast_event(task_id, {
                'event': 'scoring-failed',
                'data': {'candidate_id': cand_id, 'error': str(e)},
            })

    broadcast_event(task_id, {
        'event': 'task-complete',
        'data': {'summary': {'total': len(candidate_ids), 'passed': len(candidate_ids)}},
    })

    if submit_mode == 'async':
        send_async_notification_task.delay(task_id)


@shared_task
def send_async_notification_task(task_id):
    """异步评分完成后发通知中心

    简化实现：只记录日志。Phase 3 接通知中心。
    """
    logger.info('Async scoring complete: task=%s', task_id)
