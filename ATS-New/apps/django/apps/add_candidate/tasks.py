"""Add Candidate V2 - Celery tasks"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def parse_resume_task(self, job_id):
    """解析单个简历任务

    完整实现见 Task 5（本 task 只做 stub 让 UploadAndParseView 跑通）
    """
    from .models import ParseJob
    try:
        job = ParseJob.objects.get(job_id=job_id)
        job.phase = 'parsing'
        job.progress = 10
        job.save(update_fields=['phase', 'progress'])
        logger.info('parse_resume_task: stub for job %s', job_id)
    except ParseJob.DoesNotExist:
        logger.error('ParseJob %s not found', job_id)
    except Exception as e:
        logger.exception('parse_resume_task failed: %s', e)
        raise self.retry(exc=e)
