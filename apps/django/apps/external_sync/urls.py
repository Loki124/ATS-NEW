"""External Sync URL Routes — /api/v1/external-sync/..."""
from django.urls import path

from .views import CompanySyncListView, CompanySyncRetryView, CompanySyncTriggerView

urlpatterns = [
    path('syncs', CompanySyncListView.as_view()),
    path('syncs/<str:sync_id>/retry', CompanySyncRetryView.as_view()),
    path('sync/<str:company_id>/<str:system>', CompanySyncTriggerView.as_view()),
]
