"""WebSocket Consumers"""
import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """通知推送 - 用户级"""
    async def connect(self):
        if self.scope['user'].is_anonymous:
            await self.close()
        else:
            self.group_name = f'user_{self.scope["user"].id}'
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()

    async def disconnect(self, code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def notify(self, event):
        """接收通知事件"""
        await self.send_json({
            'type': 'notification',
            'data': event['data'],
        })


class ApplicationUpdateConsumer(AsyncJsonWebsocketConsumer):
    """申请状态更新 - 候选人级"""
    async def connect(self):
        if self.scope['user'].is_anonymous:
            await self.close()
        else:
            self.application_id = self.scope['url_route']['kwargs']['application_id']
            self.group_name = f'application_{self.application_id}'
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()

    async def disconnect(self, code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def application_update(self, event):
        await self.send_json({
            'type': 'application_update',
            'data': event['data'],
        })
