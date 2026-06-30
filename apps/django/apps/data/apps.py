"""Data 数据中心 — 2026-06-29 花无缺 stub.

FE api (web/app/src/api/data.ts):
  GET  /api/v1/data/kpi/
  GET  /api/v1/data/subscriptions/
  POST /api/v1/data/subscriptions/
  GET  /api/v1/data/export/{resource}
  DELETE /api/v1/data/subscriptions/{id}

注: analytics app 已实现部分 KPI/export, 这里只补 /data/* 命名空间.
实际应把 analytics 暴露在 /data/ 下, 但完整迁移属于 G35 任务, 此处只挂 stub 防止 404.
"""
from django.apps import AppConfig


class DataConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.data'
    verbose_name = '数据中心'
