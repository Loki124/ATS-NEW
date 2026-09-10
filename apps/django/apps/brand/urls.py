"""品牌信息管理 (G43) 路由。"""
from django.urls import path

from .views import BrandInfoView, BrandLogoUploadView

urlpatterns = [
    # 单例配置端点: GET 读取 / PUT 全量更新 / PATCH 部分更新, 均无 pk
    path('', BrandInfoView.as_view(), name='brand-info'),
    # Logo 上传: POST multipart/form-data, 返回 { data: { url } }
    path('logo/', BrandLogoUploadView.as_view(), name='brand-logo-upload'),
]
