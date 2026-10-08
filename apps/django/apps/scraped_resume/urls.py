"""scraped_resume URLs — 2026-06-29. 直接 path 避免 router basename '-' 问题."""
from django.urls import path

from .views import ScrapedResumeViewSet

# config/urls.py: path('scraped-resumes/', include(...))
# 这里列具体 path. DRF ViewSet 提供 list/retrieve/create/update/destroy 标准 actions
# + 自定义 scrape (POST) 和 import_to (POST {id})

list_view = ScrapedResumeViewSet.as_view({'get': 'list'})
detail_view = ScrapedResumeViewSet.as_view({'get': 'retrieve'})
scrape_view = ScrapedResumeViewSet.as_view({'post': 'scrape'})
import_to_view = ScrapedResumeViewSet.as_view({'post': 'import_to'})

urlpatterns = [
    path('', list_view, name='scraped-resume-list'),
    path('scrape', scrape_view, name='scraped-resume-scrape'),
    path('scrape/', scrape_view),
    path('<str:pk>', detail_view, name='scraped-resume-detail'),
    path('<str:pk>/', detail_view),
    path('<str:pk>/import', import_to_view, name='scraped-resume-import'),
    path('<str:pk>/import/', import_to_view),
]
