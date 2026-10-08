"""#13 / P-34: ExportTask 软超时后被标 FAILED, 不永久卡 RUNNING。

CI 已设 CELERY_TASK_SOFT_TIME_LIMIT=25*60, 软超时抛 SoftTimeLimitExceeded,
任务应捕获并标记 FAILED (而非被硬超时杀进程导致状态长期 RUNNING)。
"""
import pytest
from celery.exceptions import SoftTimeLimitExceeded
from django.contrib.auth import get_user_model

from apps.analytics.models import ExportTask
from apps.analytics.tasks import run_export_task

User = get_user_model()


@pytest.mark.django_db
def test_soft_time_limit_marks_failed(monkeypatch):
    u = User.objects.create_user(username='exportu', password='Str0ng!Pass#1', is_active=True)
    task = ExportTask.objects.create(name='t', entity='candidates', format='CSV', requested_by=u)

    def _raise(*_a, **_k):
        raise SoftTimeLimitExceeded()

    # 导出查询阶段抛软超时异常 (模拟数据量过大触发)
    monkeypatch.setattr('apps.candidate.models.Candidate.objects.filter', _raise)

    run_export_task(task.id)

    task.refresh_from_db()
    assert task.status == 'FAILED'
    assert 'SoftTimeLimitExceeded' in (task.error_message or '')
