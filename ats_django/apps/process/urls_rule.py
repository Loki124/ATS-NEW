"""StageRule URL 单独配置 - 兼容 root urls.py 引用"""
from .urls import urlpatterns as process_urls  # noqa

urlpatterns = process_urls
