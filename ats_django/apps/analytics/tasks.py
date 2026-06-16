"""Analytics Celery tasks (PRD v4 §14.9)"""
import logging
from typing import Dict

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name='apps.analytics.tasks.run_export_task')
def run_export_task(export_task_id: str) -> Dict:
    """执行导出任务（异步）"""
    from .models import ExportTask
    from django.http import HttpResponse

    try:
        task = ExportTask.objects.get(id=export_task_id)
    except ExportTask.DoesNotExist:
        return {'error': f'ExportTask {export_task_id} 不存在'}

    task.status = 'RUNNING'
    task.started_at = timezone.now()
    task.save()

    try:
        # 根据 entity 字段确定要导出的数据
        if task.entity == 'candidates':
            from apps.candidate.models import Candidate
            qs = Candidate.objects.filter(deleted_at__isnull=True)
        elif task.entity == 'applications':
            from apps.application.models import Application
            qs = Application.objects.filter(deleted_at__isnull=True)
        elif task.entity == 'demands':
            from apps.demand.models import Demand
            qs = Demand.objects.filter(deleted_at__isnull=True)
        else:
            raise ValueError(f'未知 entity: {task.entity}')

        # 应用过滤
        for key, value in (task.filters or {}).items():
            qs = qs.filter(**{key: value})

        # 字段选择
        if task.fields:
            data = list(qs.values(*task.fields))
        else:
            data = list(qs.values())

        # 写入文件
        import os
        from django.conf import settings
        export_dir = os.path.join(settings.MEDIA_ROOT, 'exports')
        os.makedirs(export_dir, exist_ok=True)

        filename = f'{task.entity}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.{task.format.lower()}'
        filepath = os.path.join(export_dir, filename)

        if task.format == 'XLSX':
            import openpyxl
            wb = openpyxl.Workbook()
            ws = wb.active
            if data:
                ws.append(list(data[0].keys()))
                for row in data:
                    ws.append([str(v) for v in row.values()])
            wb.save(filepath)
        elif task.format == 'CSV':
            import csv
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                if data:
                    writer = csv.DictWriter(f, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
        else:  # PDF
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            c = canvas.Canvas(filepath, pagesize=A4)
            c.drawString(100, 800, f'Export: {task.name}')
            y = 770
            for row in data[:50]:
                c.drawString(50, y, str(row)[:100])
                y -= 15
            c.save()

        task.file_url = f'{settings.MEDIA_URL}exports/{filename}'
        task.file_size = os.path.getsize(filepath)
        task.row_count = len(data)
        task.status = 'COMPLETED'
        task.completed_at = timezone.now()
        task.save()
    except Exception as e:
        logger.exception(f'Export task {export_task_id} failed: {e}')
        task.status = 'FAILED'
        task.error_message = str(e)
        task.completed_at = timezone.now()
        task.save()

    return {
        'task_id': export_task_id,
        'status': task.status,
        'row_count': task.row_count,
    }


@shared_task(name='apps.analytics.tasks.generate_daily_report_snapshot')
def generate_daily_report_snapshot() -> Dict:
    """每日生成 HR 看板快照"""
    from .models import ReportSnapshot
    from .services import AnalyticsService

    summary = AnalyticsService.get_dashboard_summary()
    funnel = AnalyticsService.get_funnel_data(days=7)

    snapshot = ReportSnapshot.objects.create(
        name=f'每日看板-{timezone.now().strftime("%Y-%m-%d")}',
        report_type='DASHBOARD',
        scope={'days': 7},
        data={'summary': summary, 'funnel': funnel},
    )
    return {
        'snapshot_id': snapshot.id,
        'generated_at': snapshot.generated_at.isoformat(),
    }
