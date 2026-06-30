"""Scrape-resume 简历抓取 — 2026-06-29 花无缺 stub.

FE api (web/app/src/api/scraped-resume.ts):
  POST  /api/v1/scraped-resumes/scrape
  GET   /api/v1/scraped-resumes
  POST  /api/v1/scraped-resumes/{id}/import
"""
from django.apps import AppConfig


class ScrapedResumeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.scraped_resume'
    verbose_name = 'RPA 简历抓取'
