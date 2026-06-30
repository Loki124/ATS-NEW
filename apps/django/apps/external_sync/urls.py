"""external_sync URLs — 2026-06-29.

FE api:
  POST /external-sync/sync/{companyId}/{system}
  GET  /external-sync/syncs
  POST /external-sync/syncs/{syncId}/retry
"""
from django.urls import path
from .views import CompanySyncViewSet

# config/urls.py: path('integrations/', include('apps.integration.urls'))
# 但 FE 调 /external-sync/* (不是 /integrations/*) — 命名空间不一致.
# 这里直接 path 显式挂:
# config/urls.py 需要: path('external-sync/', include('apps.external_sync.urls'))
# 但目前 config/urls.py 有 path('integrations/', include('apps.integration.urls'))
# 修: config/urls.py 添加 external-sync (用 url include 模式)

# 暂用 router 模式 (但 basename '-')
# 改用 path() 直接:
list_view = CompanySyncViewSet.as_view({'get': 'list'})
syncs_view = CompanySyncViewSet.as_view({'get': 'syncs'})
sync_one = CompanySyncViewSet.as_view({'post': 'trigger_sync'})
retry_one = CompanySyncViewSet.as_view({'post': 'retry'})

urlpatterns = [
    path('', list_view, name='external-sync-list'),
    path('syncs', syncs_view, name='external-sync-syncs'),
    path('syncs/', syncs_view),
    path('sync/<str:company_id>/<str:system>', sync_one, name='external-sync-trigger'),
    path('sync/<str:company_id>/<str:system>/', sync_one),
    path('syncs/<str:pk>/retry', retry_one, name='external-sync-retry'),
    path('syncs/<str:pk>/retry/', retry_one),
]
