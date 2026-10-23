"""campus_learning app config（校招学习与社区域）。

本 app **不注册任何字典种子 / 角色种子**：
- 课程形式、考试形式、活动状态、课程类型都是模型内嵌 `TextChoices`
  （契约 §1.1「枚举用 models.TextChoices 内嵌在模型里，禁止裸字符串」），不需要字典表；
- 人员 / 角色 / 字典全部复用既有 `campus_control` / `core`，不建第二套主数据。
"""
from django.apps import AppConfig


class CampusLearningConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.campus_learning'
    label = 'campus_learning'
    verbose_name = '校招学习与社区'
