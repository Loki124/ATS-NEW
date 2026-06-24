"""Add Candidate V2 - SSE 流 (Redis pub/sub 改造)

为什么用 Redis pub/sub：
- 内存 defaultdict 在多进程部署（gunicorn workers × Celery workers）下不工作 —
  Celery worker 写到自己进程的 dict，gunicorn worker 读不到。
- Redis pub/sub 跨进程、跨机器共享，Celery → Web 事件可靠送达。
"""
import json
import time

import redis
from django.conf import settings
from django.http import StreamingHttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.permissions import IsHROrAbove

_redis = None


def _get_redis():
    """懒加载 Redis client（连 CELERY_BROKER_URL）"""
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.CELERY_BROKER_URL)
    return _redis


def broadcast_event(task_id: str, payload: dict):
    """Celery task 调这个推 SSE 事件（写入 Redis pub/sub）"""
    r = _get_redis()
    channel = f'add_candidate:scoring:{task_id}'
    r.publish(channel, json.dumps(payload, ensure_ascii=False))


def _consume_events(task_id: str):
    """SSE consumer generator（订阅 Redis pub/sub）"""
    r = _get_redis()
    pubsub = r.pubsub()
    channel = f'add_candidate:scoring:{task_id}'
    pubsub.subscribe(channel)

    last_heartbeat = time.time()
    try:
        for message in pubsub.listen():
            if message['type'] != 'message':
                continue
            try:
                evt = json.loads(message['data'])
            except (TypeError, ValueError):
                continue
            event = evt.get('event', 'message')
            data = json.dumps(evt.get('data', {}), ensure_ascii=False)
            yield f'event: {event}\ndata: {data}\n\n'
            if event == 'task-complete':
                break

            # Heartbeat
            now = time.time()
            if now - last_heartbeat > 15:
                yield ': heartbeat\n\n'
                last_heartbeat = now
    finally:
        try:
            pubsub.unsubscribe(channel)
        except Exception:
            pass
        try:
            pubsub.close()
        except Exception:
            pass


class ScoringStreamView(APIView):
    """GET /scoring/stream/{task_id}/

    SSE 评分进度流。前端 EventSource 连这个端点。
    """
    permission_classes = [IsAuthenticated, IsHROrAbove]

    def get(self, request, task_id):
        response = StreamingHttpResponse(
            _consume_events(task_id),
            content_type='text/event-stream',
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'  # nginx 不缓冲
        return response
