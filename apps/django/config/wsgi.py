"""WSGI 配置

2026-08-03 R3 (寇豆码): 原默认值 'config.settings' 不在 settings 白名单里,
会被 config/settings/__init__.py 静默回落到 dev(DEBUG=True + CORS 全放开)。
WSGI 只在服务端跑,默认值改为显式 prod。
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod')
application = get_wsgi_application()
