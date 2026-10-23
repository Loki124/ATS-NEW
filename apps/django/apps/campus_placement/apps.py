"""campus_placement app config（校招定岗与结算域）。

挂载前缀 `/api/v1/campus-placement/`（由 `config/urls.py` 挂载，父会话负责）。
本 app 只做三件事：
- 岗位需求（PositionDemand）与志愿（PositionApplication）的双选撮合状态机；
- 定岗跟踪（PlacementRecord 及其目标 / 数据 / 考核子表）；
- 交易与结算（定价方案 / 出价 / 输出台账 / 结算账单）。

跨域只读引用 `campus_control.Person`（字符串外键 'campus_control.Person'），
**不 import 别的 app 的 models**，避免 app 间成环。
"""
from django.apps import AppConfig


class CampusPlacementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.campus_placement'
    label = 'campus_placement'
    verbose_name = '校招定岗与结算'
