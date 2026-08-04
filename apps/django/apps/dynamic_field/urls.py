from django.urls import path

from .views import DynamicFieldViewSet

urlpatterns = [
    path(
        '<str:resource>/fields/',
        DynamicFieldViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='dynamicfield-list',
    ),
    path(
        '<str:resource>/fields/<str:pk>/',
        DynamicFieldViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}),
        name='dynamicfield-detail',
    ),
    path(
        '<str:resource>/fields/reorder/',
        DynamicFieldViewSet.as_view({'post': 'reorder'}),
        name='dynamicfield-reorder',
    ),
]
