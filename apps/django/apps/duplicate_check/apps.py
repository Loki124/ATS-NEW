"""Duplicate-check 简历查重 — 2026-06-29 花无缺 stub.

FE api:
  POST /api/v1/duplicate-check/check
  POST /api/v1/duplicate-check/ocr-parse
"""
from django.apps import AppConfig


class DuplicateCheckConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.duplicate_check'
    verbose_name = '简历查重'
