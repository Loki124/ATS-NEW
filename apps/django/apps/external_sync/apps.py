"""External-sync 外部系统同步 — 2026-06-29 花无缺 stub.

FE api:
  POST /api/v1/external-sync/sync/{companyId}/{system}
  GET  /api/v1/external-sync/syncs
  POST /api/v1/external-sync/syncs/{syncId}/retry
"""
from django.apps import AppConfig


class ExternalSyncConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.external_sync'
    verbose_name = '外部系统同步'
