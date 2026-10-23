"""campus_assessment app config（校招考核域）。

本 app 不注册字典种子，也不写任何 post_migrate 回调 ——
考核域的表结构全部由本 app 自带的迁移 0001 承担，资源码登记由父会话在
core 迁移里统一做（契约 §1.2 末尾 / §7）。
"""
from django.apps import AppConfig


class CampusAssessmentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.campus_assessment'
    label = 'campus_assessment'
    verbose_name = '校招考核'
