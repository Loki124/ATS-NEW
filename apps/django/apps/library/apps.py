"""院校/公司信息库 — 2026-06-29 花无缺.

FE api (web/app/src/api/library.ts) 调用:
  GET  /api/v1/library/schools
  GET  /api/v1/library/schools/{id}
  GET  /api/v1/library/schools/provinces
  GET  /api/v1/library/companies
  GET  /api/v1/library/companies/{id}
  GET  /api/v1/library/companies/industries

实现: 最小可跑 stub - 真实 School/Company model 留给后续 Plan 任务.
现在返 mock 空数据 + permission 占位, 让兵哥至少不再看到 404.
"""
from django.apps import AppConfig


class LibraryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.library'
    verbose_name = '院校/公司信息库'
