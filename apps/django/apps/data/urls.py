"""data URLs — 2026-06-29.

FE api:
  GET  /api/v1/data/kpi/
  GET  /api/v1/data/subscriptions/
  POST /api/v1/data/subscriptions/
  DELETE /api/v1/data/subscriptions/{id}
  GET  /api/v1/data/export/{resource}
"""
from django.urls import path
from .views import DataViewSet

list_view = DataViewSet.as_view({'get': 'list'})
kpi_view = DataViewSet.as_view({'get': 'kpi'})
subs_view = DataViewSet.as_view({'get': 'subscriptions'})
create_view = DataViewSet.as_view({'post': 'create_subscription'})
del_view = DataViewSet.as_view({'delete': 'destroy_subscription'})

urlpatterns = [
    path('', list_view, name='data-list'),
    path('kpi', kpi_view, name='data-kpi'),
    path('kpi/', kpi_view),
    path('subscriptions', subs_view, name='data-subs'),
    path('subscriptions/', subs_view),
    path('subscriptions/create', create_view, name='data-subs-create'),
    path('subscriptions/create/', create_view),
    path('subscriptions/<str:pk>', del_view, name='data-subs-del'),
    path('subscriptions/<str:pk>/', del_view),
    # FE 期望的 DELETE 是 /subscriptions/{id}, 也支持 GET 用于列表
    # (KPI/export 真实 stub 不返 blob)
]
