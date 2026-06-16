"""Celery 应用入口

⚠️ Beat 定时任务统一在 config/settings/base.py 的 CELERY_BEAT_SCHEDULE 中定义（单一来源）。
本文件只做应用初始化、任务路由、队列优先级配置。
"""
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('ats')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# === 任务路由（按业务域分流到不同队列）===
app.conf.task_routes = {
    'apps.time_limit.tasks.*': {'queue': 'time_limit'},
    'apps.automation.tasks.*': {'queue': 'automation'},
    'apps.notification.tasks.*': {'queue': 'notification'},
    'apps.analytics.tasks.*': {'queue': 'analytics'},
    'apps.application.tasks.*': {'queue': 'application'},
    'apps.gdpr.tasks.*': {'queue': 'gdpr'},
    'apps.invitation.tasks.*': {'queue': 'invitation'},
    'apps.talent_pool.tasks.*': {'queue': 'talent_pool'},
}

# === 任务优先级 ===
app.conf.task_queue_max_priority = 10
app.conf.task_default_priority = 5

# 任务默认行为
app.conf.task_acks_late = True
app.conf.worker_prefetch_multiplier = 1
