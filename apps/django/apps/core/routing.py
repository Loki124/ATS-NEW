"""Channels WebSocket 路由 + 工具函数"""
from __future__ import annotations

from channels.layers import get_channel_layer
from django.urls import re_path
from asgiref.sync import async_to_sync

from . import consumers


websocket_urlpatterns = [
    re_path(r'ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
    re_path(r'ws/applications/(?P<application_id>\w+)/$', consumers.ApplicationUpdateConsumer.as_asgi()),
]


# ============================================================
# 同步工具函数（供普通视图/Celery 任务调用）
# ============================================================
def push_to_user(user_id: str, payload: dict) -> int:
    """向指定用户推送 WebSocket 消息

    返回：成功投递的连接数
    """
    try:
        channel_layer = get_channel_layer()
        if not channel_layer:
            return 0
        group_name = f'user_{user_id}'
        async_to_sync(channel_layer.group_send)(group_name, {
            'type': 'notify',
            'data': payload,
        })
        return 1
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning('push_to_user failed: %s', e)
        return 0


def push_to_application(application_id: str, payload: dict) -> int:
    """向申请相关订阅者推送"""
    try:
        channel_layer = get_channel_layer()
        if not channel_layer:
            return 0
        group_name = f'application_{application_id}'
        async_to_sync(channel_layer.group_send)(group_name, {
            'type': 'application_update',
            'data': payload,
        })
        return 1
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning('push_to_application failed: %s', e)
        return 0
