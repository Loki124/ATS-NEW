"""ASGI 配置 - 支持 WebSocket (Channels)

2026-08-03 R3 (寇豆码): 原默认值 'config.settings' 会被静默回落到 dev,
生产 daphne 进程实际跑 DEBUG=True。默认值改为显式 prod。
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod')
django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

from apps.core.routing import websocket_urlpatterns
from apps.core.middleware_ws import JWTAuthMiddleware

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AllowedHostsOriginValidator(
        JWTAuthMiddleware(
            URLRouter(websocket_urlpatterns)
        )
    ),
})
